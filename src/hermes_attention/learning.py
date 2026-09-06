"""Owner-mediated learning backed by native Hermes memory and skill files.

The trusted UI supplies authorize_owner; model/source arguments never constitute
owner approval. No real home is touched by construction or tests.
"""
from pathlib import Path
import difflib
import hashlib
import json
import re
import secrets
import time
from uuid import uuid4
from .domain import utc_now,stable_hash
from .security import SECRET_PATTERNS,detect_prompt_injection

AUTHORITY=re.compile(r'\b(?:permission|credential|token|password|oauth|scope|budget|sudo|security|send|payment|purchase|checkout|shell|execute|bypass|disable|company|client|repository|tool)\b',re.I)
NAME=re.compile(r'^[a-z0-9][a-z0-9_-]{0,79}$')

def ensure_schema(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS learning_preferences(preference_id TEXT PRIMARY KEY,text TEXT NOT NULL,status TEXT NOT NULL,provenance_json TEXT NOT NULL,replaces_id TEXT,native_result_json TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS learning_selections(selection_id TEXT PRIMARY KEY,pending_id TEXT NOT NULL,record_hash TEXT NOT NULL,expires REAL NOT NULL,consumed INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS learning_skill_versions(version_id TEXT PRIMARY KEY,name TEXT NOT NULL,before_text TEXT NOT NULL,after_text TEXT NOT NULL,before_hash TEXT NOT NULL,after_hash TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS learning_community(stage_id TEXT PRIMARY KEY,source TEXT NOT NULL,name TEXT NOT NULL,content TEXT NOT NULL,content_hash TEXT NOT NULL,requested_tools_json TEXT NOT NULL,scan_json TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
    ''')

class NativeHermesAdapter:
    """Lazy imports resolve inside the owned Hermes interpreter, not system Python."""
    def pending(self):
        from tools import write_approval as wa
        return wa.list_pending(wa.MEMORY)
    def confirmed(self):
        from tools.memory_tool import load_on_disk_store
        store=load_on_disk_store()
        return {'memory':list(store.memory_entries),'user':list(store.user_entries)}
    def resolve(self,pending_id,action):
        from tools import write_approval as wa
        from tools.memory_tool import load_on_disk_store
        from hermes_cli.write_approval_commands import handle_pending_subcommand
        text=handle_pending_subcommand(wa.MEMORY,[action,pending_id],memory_store=load_on_disk_store())
        return {'ok':bool(text and text.startswith(('Approved 1','Rejected pending'))),'result':text}
    def stage(self,text):
        from tools import write_approval as wa
        record=wa.stage_write(wa.MEMORY,{'action':'add','target':'user','content':text,'old_text':None},summary=text[:120],origin='foreground')
        if wa.get_pending(wa.MEMORY,record['id']) is None:raise RuntimeError('native staging did not persist')
        return {'pending_id':record['id'],'staged':True}
    def preference(self,text,old=None,remove=False):
        from tools.memory_tool import load_on_disk_store
        store=load_on_disk_store()
        # The caller supplies authenticated owner intent; all native content,
        # cap, lock, drift and persistence checks remain in MemoryStore.
        return store.remove('user',old) if remove else (store.replace('user',old,text) if old is not None else store.add('user',text))
    def scan_skill(self,path):
        from tools.skills_guard import scan_skill
        result=scan_skill(path,source='local')
        return {'verdict':result.verdict,'summary':result.summary}

class Learning:
    def __init__(self,store,skills_root,*,native=None,authorize_owner=None,clock=time.time):
        self.store=store;self.skills_root=Path(skills_root).absolute();self.native=native or NativeHermesAdapter()
        self.authorize_owner=authorize_owner or (lambda operation,resource:False);self.clock=clock
        ensure_schema(store.connection)
    def _owner(self,operation,resource):
        if self.authorize_owner(operation,resource) is not True:raise PermissionError('explicit owner selection is required')
    def snapshot(self):
        pending=self.native.pending()
        return {'native_pending':[{'id':r['id'],'summary':r.get('summary',''),'origin':r.get('origin'),'payload':r.get('payload')} for r in pending],
            'native_confirmed':self.native.confirmed(),
            'project_memory':[{**dict(r),'review_hash':stable_hash(dict(r))} for r in self.store.connection.execute('SELECT * FROM memory_proposals ORDER BY created_at DESC')],
            'preferences':[dict(r) for r in self.store.connection.execute('SELECT * FROM learning_preferences ORDER BY created_at DESC')],
            'skills':self.list_skills(),'automatic_pending_approval':False}
    def select_native(self,pending_id):
        self._owner('select-memory',pending_id)
        record=next((r for r in self.native.pending() if r['id']==pending_id),None)
        if not record:raise ValueError('pending item no longer exists')
        selection=secrets.token_urlsafe(24)
        with self.store.connection:self.store.connection.execute('INSERT INTO learning_selections VALUES(?,?,?,?,0)',(selection,pending_id,stable_hash(record),self.clock()+600))
        return {'selection':selection,'summary':record.get('summary'),'expires_in_seconds':600}
    def resolve_native(self,selection,action):
        if action not in {'approve','reject'}:raise ValueError('invalid review action')
        row=self.store.connection.execute('SELECT * FROM learning_selections WHERE selection_id=?',(selection,)).fetchone()
        if not row or row['consumed'] or row['expires']<self.clock():raise PermissionError('selection expired or already used')
        self._owner(action+'-memory',selection)
        current=next((r for r in self.native.pending() if r['id']==row['pending_id']),None)
        if current is None or stable_hash(current)!=row['record_hash']:raise PermissionError('pending content changed; select again')
        result=self.native.resolve(row['pending_id'],action)
        if result.get('ok'):
            with self.store.connection:self.store.connection.execute('UPDATE learning_selections SET consumed=1 WHERE selection_id=?',(selection,))
        return result
    def resolve_project(self,memory_id,action,*,expected_hash):
        if action not in {'approve','reject'}:raise ValueError('invalid review action')
        self._owner(action+'-project-memory',{'memory_id':memory_id,'hash':expected_hash})
        row=self.store.connection.execute("SELECT * FROM memory_proposals WHERE memory_id=? AND status='proposed'",(memory_id,)).fetchone()
        if not row or stable_hash(dict(row))!=expected_hash:raise PermissionError('project memory changed; review again')
        with self.store.connection:self.store.connection.execute('UPDATE memory_proposals SET status=?,reviewed_at=? WHERE memory_id=?',('confirmed' if action=='approve' else 'rejected',utc_now(),memory_id))
        return {'memory_id':memory_id,'status':'confirmed' if action=='approve' else 'rejected'}

    def dispatch(self,operation,arguments=None):
        """Trusted IPC facade. Never expose the owner-authority callback to models."""
        operations={'snapshot':self.snapshot,'select-native':self.select_native,'resolve-native':self.resolve_native,
          'resolve-project':self.resolve_project,'save-preference':self.save_preference,'undo-preference':self.undo_preference,
          'list-skills':self.list_skills,'skill-preview':self.skill_preview,'skill-edit':self.skill_edit,
          'skill-rollback':self.skill_rollback,'community-stage':self.community_stage}
        if operation not in operations:raise ValueError('unsupported learning operation')
        return operations[operation](**(arguments or {}))

    def save_preference(self,text,*,provenance,replaces_id=None,uncertain=False):
        text=str(text).strip()
        if not text or len(text)>1000:raise ValueError('preference must contain 1 to 1000 characters')
        self._owner('save-preference',{'text':text,'replaces_id':replaces_id})
        if any(p.search(text) for p in SECRET_PATTERNS):raise ValueError('secret-shaped content cannot be stored as a preference')
        old=None
        if replaces_id:
            old=self.store.connection.execute('SELECT * FROM learning_preferences WHERE preference_id=? AND status=?',(replaces_id,'confirmed')).fetchone()
            if not old:raise ValueError('current confirmed preference required')
        preference_language=bool(re.search(r'(?i)\b(?:prefer|favorite|favourite|like|dislike|replies|responses|paragraphs?|bullets?|tone|format|concise|brief|verbose|style)\b',text))
        staged=uncertain or not preference_language or bool(re.search(r'(?i)\b(?:maybe|possibly|uncertain|probably)\b',text)) or bool(AUTHORITY.search(text)) or bool(detect_prompt_injection(text))
        already_present=not staged and old is None and text in self.native.confirmed().get('user',[])
        result=({'success':True,'already_present':True} if already_present else
                (self.native.stage(text) if staged else self.native.preference(text,old['text'] if old else None)))
        if not staged and result.get('success') is not True:raise RuntimeError('native memory refused preference: '+str(result.get('error',result)))
        pid=str(uuid4());status='staged' if staged else 'confirmed'
        with self.store.connection:
            self.store.connection.execute('INSERT INTO learning_preferences VALUES(?,?,?,?,?,?,?)',(pid,text,status,json.dumps(provenance),replaces_id,json.dumps(result),utc_now()))
            if old and not staged:self.store.connection.execute("UPDATE learning_preferences SET status='superseded' WHERE preference_id=?",(replaces_id,))
        return {'preference_id':pid,'status':status,'native':result,'undo_available':not staged and not already_present}
    def undo_preference(self,preference_id):
        self._owner('undo-preference',preference_id)
        row=self.store.connection.execute("SELECT * FROM learning_preferences WHERE preference_id=? AND status='confirmed'",(preference_id,)).fetchone()
        if not row:raise ValueError('current confirmed preference required')
        if json.loads(row['native_result_json']).get('already_present'):raise ValueError('pre-existing native preference was preserved; there is no new write to undo')
        old=self.store.connection.execute('SELECT * FROM learning_preferences WHERE preference_id=?',(row['replaces_id'],)).fetchone() if row['replaces_id'] else None
        result=self.native.preference(old['text'] if old else '',old=row['text'],remove=old is None)
        if result.get('success') is not True:raise RuntimeError('native undo refused; version retained')
        with self.store.connection:
            self.store.connection.execute("UPDATE learning_preferences SET status='undone' WHERE preference_id=?",(preference_id,))
            if old:self.store.connection.execute("UPDATE learning_preferences SET status='confirmed' WHERE preference_id=?",(old['preference_id'],))
        return {'status':'undone','native':result}
    def _path(self,name):
        if not NAME.fullmatch(name):raise ValueError('invalid personal skill name')
        path=self.skills_root/name/'SKILL.md'
        for part in (self.skills_root,*self.skills_root.parents,path.parent,path):
            if part.is_symlink():raise PermissionError('symlink skill path refused')
        if not path.resolve().is_relative_to(self.skills_root.resolve()):raise PermissionError('skill escapes selected root')
        return path
    def list_skills(self):
        if not self.skills_root.exists():return []
        result=[]
        for directory in sorted(self.skills_root.iterdir()):
            if not NAME.fullmatch(directory.name):continue
            try:path=self._path(directory.name)
            except PermissionError:continue
            if not path.is_file():continue
            content=path.read_text();usage=self.skills_root/'.usage.json'
            meta=json.loads(usage.read_text()).get(directory.name,{}) if usage.is_file() and not usage.is_symlink() else {}
            result.append({'name':directory.name,'content':content,'hash':stable_hash(content),'pinned':bool(meta.get('pinned')),'created_by':meta.get('created_by'),'owner_editable':True})
        return result
    def skill_preview(self,name,content):
        path=self._path(name);before=path.read_text() if path.exists() else ''
        issues=[]
        if len(content)>30000:issues.append('instructions exceed 30000 characters')
        if not content.startswith('---\n') or '\n---\n' not in content[4:]:issues.append('YAML name and description frontmatter required')
        try:
            front={}
            for line in content.split('---',2)[1].strip().splitlines():
                if not line.strip() or line.lstrip().startswith('#'):continue
                key,value=line.split(':',1)
                if key in front or not re.fullmatch(r'[a-z][a-z_-]*',key):raise ValueError('invalid frontmatter field')
                front[key]=value.strip().strip('\"\'')
            if not isinstance(front,dict) or front.get('name')!=name or not front.get('description'):issues.append('frontmatter name must match selection and description is required')
            elif set(front)-{'name','description','tags','version'}:issues.append('capability or setup metadata cannot be changed by instructions editor')
        except (IndexError,ValueError):issues.append('invalid YAML frontmatter')
        if re.search(r'(?i)\b(?:bypass|disable|override|ignore)\b.{0,60}\b(?:approval|policy|security|permission|instructions|guard)\b|\b(?:grant|expand|change)\b.{0,40}\b(?:scope|permission|credential|budget)\b',content) or detect_prompt_injection(content):issues.append('protected authority changes require separate review')
        if any(p.search(content) for p in SECRET_PATTERNS):issues.append('secret-shaped content')
        if re.search(r'```(?:bash|sh|python|javascript)|\b(?:curl|wget|pip install|npm install|subprocess|os\.system)\b',content,re.I):issues.append('instructions-only skills cannot contain executable setup')
        return {'name':name,'before_hash':stable_hash(before),'after_hash':stable_hash(content),'diff':''.join(difflib.unified_diff(before.splitlines(True),content.splitlines(True),fromfile=name+'/before',tofile=name+'/after')),'allowed':not issues,'issues':issues}
    def skill_edit(self,name,content,*,expected_hash):
        self._owner('edit-skill',{'name':name,'hash':stable_hash(content)})
        preview=self.skill_preview(name,content)
        if preview['before_hash']!=expected_hash:raise ValueError('skill changed; review the latest diff')
        if not preview['allowed']:raise PermissionError('; '.join(preview['issues']))
        path=self._path(name);before=path.read_text() if path.exists() else ''
        path.parent.mkdir(parents=True,exist_ok=True)
        # Content scanning occurs in a staging directory before native activation.
        staging=path.parent/('.review-'+secrets.token_hex(8));staging.mkdir()
        staged=staging/'SKILL.md';staged.write_text(content)
        scan=self.native.scan_skill(staging)
        if scan.get('verdict') not in {'safe','allow','clean'}:raise PermissionError('native skill scan requires review: '+str(scan))
        # Recheck after scanning, since another editor can change the native file.
        path=self._path(name)
        if stable_hash(path.read_text() if path.exists() else '')!=expected_hash:raise ValueError('skill changed during validation; activation cancelled')
        # Atomic replace only this selected SKILL.md; preserve curator usage/pin metadata.
        staged.replace(path)
        version=str(uuid4())
        with self.store.connection:self.store.connection.execute('INSERT INTO learning_skill_versions VALUES(?,?,?,?,?,?,?)',(version,name,before,content,preview['before_hash'],preview['after_hash'],utc_now()))
        return {'version_id':version,'name':name,'hash':preview['after_hash'],'native_synced':True,'scan':scan,'curator_metadata_preserved':True}
    def skill_rollback(self,version_id):
        row=self.store.connection.execute('SELECT * FROM learning_skill_versions WHERE version_id=?',(version_id,)).fetchone()
        if not row:raise ValueError('unknown skill version')
        if not row['before_text']:raise ValueError('new skill has no previous version; preserve it and disable through native skill controls')
        return self.skill_edit(row['name'],row['before_text'],expected_hash=row['after_hash'])
    def community_stage(self,*,name,content,source,requested_tools):
        self._owner('stage-community-skill',name)
        if not source.startswith('https://'):raise ValueError('reviewable HTTPS source required')
        preview=self.skill_preview(name,content);sid=str(uuid4())
        stage_root=self.skills_root/('.community-review-'+sid)
        self._path(name)  # validate root and ancestor symlinks before any writes
        stage_root.mkdir(parents=True,exist_ok=False)
        (stage_root/'SKILL.md').write_text(content)
        preview['native_scan']=self.native.scan_skill(stage_root)
        preview['behavior_test_status']='not-tested; human activation review required'
        with self.store.connection:self.store.connection.execute('INSERT INTO learning_community VALUES(?,?,?,?,?,?,?,?,?)',(sid,source,name,content,stable_hash(content),json.dumps(requested_tools),json.dumps(preview),'human-activation-required',utc_now()))
        return {'stage_id':sid,'source':source,'hash':stable_hash(content),'requested_tools':requested_tools,'scan':preview,'status':'human-activation-required','installed':False}
