"""Owner workspace operations over the existing evidence, task and project ledger.

No provider access. Source clocks/identities remain immutable; owner review is recorded
separately from evidence. Conservative transcript proposals never imply completion.
"""
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import re
from uuid import uuid4
from .domain import stable_hash
from .extraction import extract_task_candidates
from .projects import Portfolio


def instant(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Use a timezone-aware date')
    return result.astimezone(UTC)


class AwarenessWorkspace:
    def __init__(self,store,*,clock=None):
        self.store=store;self.clock=clock or (lambda:datetime.now(UTC))
        store.connection.executescript('''
        CREATE TABLE IF NOT EXISTS awareness_project_creations(request_id TEXT PRIMARY KEY,payload_hash TEXT NOT NULL,result_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS awareness_task_reviews(task_id TEXT PRIMARY KEY,review_json TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS awareness_meeting_items(candidate_id TEXT PRIMARY KEY,evidence_id TEXT NOT NULL,source_hash TEXT NOT NULL,result_json TEXT NOT NULL,created_at TEXT NOT NULL);
        ''')

    def source(self,evidence_id,*,content=False):
        row=self.store.connection.execute('SELECT * FROM evidence WHERE evidence_id=? AND tombstoned_at IS NULL',(evidence_id,)).fetchone()
        if not row:raise ValueError('Source evidence unavailable or removed')
        p=json.loads(row['provenance_json'])
        value={'evidence_id':evidence_id,'title':row['title'],'source_system':p.get('source_system'),'account_id':p.get('account_id'),'connection_id':p.get('connection_id'),'source_timestamp':p.get('source_timestamp'),'retrieved_at':p.get('retrieved_at'),'indexed_at':row['indexed_at'],'uri':p.get('uri'),'content_hash':row['content_hash'],'contexts':json.loads(row['contexts_json'])}
        if content:value['content']=row['content']
        return value

    def _task(self,task_id):
        row=self.store.connection.execute('SELECT * FROM tasks WHERE task_id=?',(task_id,)).fetchone()
        if not row:raise ValueError('Task not found')
        item=dict(row);item['evidence_ids']=json.loads(item.pop('evidence_ids_json'))
        review=self.store.connection.execute('SELECT review_json FROM awareness_task_reviews WHERE task_id=?',(task_id,)).fetchone()
        item['review']=json.loads(review[0]) if review else {}
        item['version']=stable_hash(item)
        item['sources']=[]
        for identity in item['evidence_ids']:
            try:item['sources'].append(self.source(identity))
            except ValueError:item['sources'].append({'evidence_id':identity,'unavailable':True})
        return item

    def snapshot(self,context=None,*,query='',during_chat=False):
        now=self.clock(); tasks=[]
        for row in self.store.connection.execute('SELECT task_id FROM tasks ORDER BY priority DESC,updated_at DESC LIMIT 500'):
            task=self._task(row[0]);review=task['review']
            if task['context_id']=='mitchell' or context not in (None,'mixed','unknown') and task['context_id']!=context:continue
            if task['status'] in {'done','completed','verified','dismissed','cancelled','archived'}:continue
            if review.get('snoozed_until') and instant(review['snoozed_until'])>now:continue
            if query and not any(word in task['title'].casefold() for word in query.casefold().split() if len(word)>2):continue
            try:due=instant(task['due_at']) if task['due_at'] else None
            except (ValueError,TypeError):due=None;task['due_warning']='Saved deadline lacks a valid timezone; review its date'
            task['due']=bool(due and due<=now)
            task['reason']='Due now' if task['due'] else 'Waiting on '+task['waiting_on'] if task['waiting_on'] else 'Blocked' if task['status']=='blocked' else 'Needs confirmation' if task['status']=='triage' else 'Confirmed next action'
            if during_chat and (not query or not task['due']):continue
            tasks.append(task)
        tasks.sort(key=lambda t:(not t['due'],-t['priority']))
        collections=[dict(row) for row in self.store.connection.execute('SELECT * FROM collection_runs ORDER BY started_at DESC LIMIT 25')]
        sources=[]
        for row in self.store.connection.execute('SELECT evidence_id FROM evidence WHERE tombstoned_at IS NULL ORDER BY indexed_at DESC LIMIT 100'):
            source=self.source(row[0]); contexts={c.get('context_id') for c in source['contexts']}
            if contexts=={'mitchell'} or context not in (None,'mixed','unknown') and context not in contexts:continue
            sources.append(source)
        return {'tasks':tasks[:100],'sources':sources,'collections':collections,'generated_at':now.isoformat(),'coverage':'Saved evidence; collection receipts show actual provider checks','provider_refresh_performed':False,'truncated':len(tasks)>100}

    def transition(self,value):
        with self.store.connection:
            self.store.connection.execute("BEGIN IMMEDIATE")
            return self._transition(value)

    def reminders(self,value,*,acknowledge=False):
        """Due occurrences use a durable identity; snooze creates a later occurrence.

        Delivery is local UI only. Unrelated conversations neither receive nor
        consume a reminder. Reopening the app rechecks unacknowledged due tasks.
        """
        with self.store.connection:
            self.store.connection.execute('BEGIN IMMEDIATE')
            candidates=[]
            for task in self.snapshot(value.get('context'),query=value.get('query',''),during_chat=value.get('duringChat',False))['tasks']:
                if not task['due']:continue
                occurrence=stable_hash([task['task_id'],task['due_at'],task['review'].get('snoozed_until')])
                if task['review'].get('reminded_occurrence')==occurrence:continue
                candidates.append({'taskId':task['task_id'],'title':task['title'],'context':task['context_id'],'occurrence':occurrence,'version':task['version']})
            if not acknowledge:return {'data':candidates[:3],'delivery':'local in-app only'}
            selected=next((task for task in candidates if task['taskId']==value.get('taskId') and task['occurrence']==value.get('occurrence') and task['version']==value.get('expectedVersion')),None)
            if not selected:return {'acknowledged':False,'reason':'Reminder changed, suppressed, or already delivered'}
            review=self._task(selected['taskId'])['review']
            review.update(reminded_occurrence=selected['occurrence'],reminded_at=self.clock().isoformat())
            self.store.connection.execute('INSERT OR REPLACE INTO awareness_task_reviews VALUES(?,?,?)',(selected['taskId'],json.dumps(review),self.clock().isoformat()))
            return {'acknowledged':True,'task':{**selected,'version':self._task(selected['taskId'])['version']}}

    def _transition(self,value):
        item=self._task(value['taskId'])
        if value.get('expectedVersion')!=item['version']:raise ValueError('Task changed; reload before applying this review')
        action=value['action'];review=dict(item['review']);now=self.clock().isoformat();status=item['status']
        if action in {'confirm','start','done','dismiss','reopen'}:
            status={'confirm':'open','start':'in-progress','done':'done','dismiss':'dismissed','reopen':'open'}[action]
            review.update(authority='owner-desktop',completion='owner-confirmed' if action=='done' else None)
            if action=='done' and item['task_type']=='commitment':status='completed'
            if action=='done':review['completion_note']=str(value.get('note','Owner confirmed completion'))[:2000]
        elif action=='snooze':
            until=instant(value['until'])
            if not self.clock()<until<=self.clock()+timedelta(days=366):raise ValueError('Choose a future snooze time within a year')
            review['snoozed_until']=until.isoformat()
        elif action=='correct':
            title=str(value.get('title','')).strip();owner=str(value.get('owner','')).strip()
            if not title or len(title)>500 or not owner or len(owner)>100:raise ValueError('Supply a short title and owner')
            item.update(title=title,owner=owner)
            review['correction_authority']='owner-desktop'
        else:raise ValueError('Unsupported task review')
        # Completion is an owner claim; a source mention never upgrades it to evidenced.
        with self.store.connection:
            self.store.connection.execute('UPDATE tasks SET title=?,owner=?,status=?,updated_at=? WHERE task_id=?',(item['title'],item['owner'],status,now,item['task_id']))
            self.store.connection.execute('INSERT OR REPLACE INTO awareness_task_reviews VALUES(?,?,?)',(item['task_id'],json.dumps(review),now))
        return self._task(item['task_id'])

    def meeting_preview(self,evidence_id):
        source=self.source(evidence_id,content=True);candidates=[]
        for offset,line in enumerate(source['content'].splitlines()):
            speaker_match=re.match(r'\s*(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?([^:]{1,70}):\s*(.*)',line)
            speaker=speaker_match.group(1).strip() if speaker_match else 'Unknown speaker'
            body=speaker_match.group(2) if speaker_match else line
            for task in extract_task_candidates(body,evidence_id,'unknown'):
                candidates.append({'kind':'task','title':task.title,'speaker':speaker,'owner':speaker if speaker.casefold() in {'syed','sid','syed ali','syed ali haider'} else 'Unconfirmed assignee','line':offset+1,'quote':line[:1000]})
            if re.match(r'\s*(?:decision|decided|agreed)\s*:',line,re.I):
                candidates.append({'kind':'decision','title':line.split(':',1)[1].strip()[:500],'speaker':'Unconfirmed decision maker','owner':'Unconfirmed','line':offset+1,'quote':line[:1000]})
        for item in candidates:item['candidate_id']=sha256((evidence_id+source['content_hash']+json.dumps(item,sort_keys=True)).encode()).hexdigest()
        source.pop('content')
        return {'source':source,'candidates':candidates[:100],'extraction':'Conservative proposals; review omissions and assignees before saving','truncated':len(candidates)>100}

    def meeting_process(self,value):
        preview=self.meeting_preview(value['evidenceId']);source=preview['source']
        if value['expectedHash']!=source['content_hash']:raise ValueError('Transcript changed; review the current source')
        context=value['context']
        if context not in {'personal','inside-success','mitchell','mixed','unknown'}:raise ValueError('Choose a configured context')
        available={c['context_id'] for c in source['contexts']}
        if context=='mitchell':raise ValueError('Mitchell is dormant; no automatic meeting processing')
        if context not in available and not available.intersection({'unknown','mixed'}):raise ValueError('Meeting context must match its source')
        project=value.get('projectId')
        if project:self._project(project,context)
        selected=value.get('selected',[])
        if not selected:raise ValueError('Select reviewed meeting items first')
        candidates={c['candidate_id']:c for c in preview['candidates']};results=[]
        # Validate the entire review before the first local mutation.
        for choice in selected:
            if choice['candidateId'] not in candidates:raise ValueError('Candidate no longer belongs to this transcript')
            if not str(choice.get('owner','')).strip():raise ValueError('Confirm the assignee or mark unknown')
        for choice in selected:
            item=candidates[choice['candidateId']];identity=item['candidate_id']
            existing=self.store.connection.execute('SELECT result_json FROM awareness_meeting_items WHERE candidate_id=?',(identity,)).fetchone()
            if existing:results.append(json.loads(existing[0]));continue
            result={**item,'owner':choice['owner'],'source':source,'project_id':project,'reviewed_by':'owner-desktop'}
            if item['kind']=='task':
                task_id='meeting:'+identity
                with self.store.connection:self.store.connection.execute('INSERT OR IGNORE INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(task_id,item['title'],context,'meeting-commitment','open',50,choice['owner'],None,None,json.dumps([source['evidence_id']]),0.8,self.clock().isoformat()))
                result['task_id']=task_id
            else:
                result['decision_id']='meeting:'+identity
                with self.store.connection:self.store.connection.execute('INSERT OR IGNORE INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)',(result['decision_id'],context,project,item['title'],'[]','Owner reviewed transcript line '+str(item['line']),None,None,json.dumps([source['evidence_id']]),self.clock().isoformat(),None))
            with self.store.connection:self.store.connection.execute('INSERT INTO awareness_meeting_items VALUES(?,?,?,?,?)',(identity,source['evidence_id'],source['content_hash'],json.dumps(result),self.clock().isoformat()))
            results.append(result)
        return {'items':results,'provider_write':False,'completion_claimed':False}

    def _project(self,identity,context=None):
        row=self.store.connection.execute('SELECT * FROM projects WHERE project_id=?',(identity,)).fetchone()
        if not row or row['lifecycle']!='active':raise ValueError('Choose an active project')
        if context and row['context_id']!=context:raise ValueError('Project context differs from source')
        return dict(row)

    def project_create(self,value):
        if not isinstance(value,dict) or set(value)-{'requestId','context','name','objective','completionContract','evidenceIds'}:raise ValueError('Unsupported project creation fields')
        request_id=value.get('requestId')
        if not isinstance(request_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',request_id):raise ValueError('A stable owner request ID is required')
        context=value.get('context')
        if context not in {'personal','inside-success','unknown'}:raise ValueError('Choose an active personal, Inside Success, or unknown context')
        fields={}
        for field,limit,default in [('name',120,None),('objective',2000,None),('completionContract',1000,'Owner confirms the objective is complete')]:
            text=value.get(field,default)
            if not isinstance(text,str) or not text.strip() or len(text.strip())>limit:raise ValueError('Supply a bounded project '+field)
            fields[field]=text.strip()
        identities=value.get('evidenceIds',[])
        if not isinstance(identities,list) or len(identities)>20 or not all(isinstance(x,str) and 1<=len(x)<=500 for x in identities):raise ValueError('Select at most20 source evidence IDs')
        identities=list(dict.fromkeys(identities));payload=stable_hash({'context':context,**fields,'evidenceIds':identities})
        project_id='project:'+stable_hash({'owner_request':request_id});now=self.clock().isoformat()
        with self.store.connection:
            self.store.connection.execute('BEGIN IMMEDIATE')
            existing=self.store.connection.execute('SELECT * FROM awareness_project_creations WHERE request_id=?',(request_id,)).fetchone()
            if existing:
                if existing['payload_hash']!=payload:raise ValueError('Project request ID already belongs to different input')
                return {**json.loads(existing['result_json']),'created':False}
            for identity in identities:
                source=self.source(identity)
                if context not in {x['context_id'] for x in source['contexts']}:raise ValueError('Project evidence context mismatch')
            self.store.connection.execute('INSERT INTO projects VALUES(?,?,?,?,?,?,?,?,?,?)',(project_id,context,fields['name'],fields['objective'],fields['completionContract'],'planning','active',now,now,now))
            snapshot_id=None
            if identities:
                snapshot_id='snapshot:'+stable_hash({'project_creation':request_id})
                state={'summary':'Owner created project: '+fields['objective'],'state':'owner-reported project creation','completed':False}
                self.store.connection.execute('INSERT INTO project_snapshots VALUES(?,?,?,?,?)',(snapshot_id,project_id,json.dumps(state),json.dumps(identities),now))
            result={'project':self._project(project_id),'projectId':project_id,'snapshotId':snapshot_id,'created':True,'providerWrite':False}
            self.store.connection.execute('INSERT INTO awareness_project_creations VALUES(?,?,?)',(request_id,payload,json.dumps(result)))
        return result

    def checkpoint(self,value):
        project=self._project(value['projectId']);summary=str(value.get('summary','')).strip();next_step=str(value.get('nextStep','')).strip()
        if not summary or not next_step or len(summary)>5000 or len(next_step)>2000:raise ValueError('Record where you stopped and the next step')
        selected=value.get('evidenceIds',[])
        if not isinstance(selected,list) or len(selected)>20 or not all(isinstance(x,str) and 1<=len(x)<=500 for x in selected):raise ValueError('Select at most20 valid evidence IDs')
        identities=list(dict.fromkeys(selected))
        for identity in identities:
            source=self.source(identity)
            if project['context_id'] not in {c['context_id'] for c in source['contexts']}:raise ValueError('Checkpoint source context mismatch')
        state={'summary':summary,'next_step':next_step,'state':'owner-reported checkpoint','verification':'unverified owner report','completed':False}
        if identities:identity=Portfolio(self.store).snapshot(project['project_id'],state,tuple(identities))
        else:
            identity=str(uuid4());now=self.clock().isoformat()
            with self.store.connection:
                self.store.connection.execute('INSERT INTO project_snapshots VALUES(?,?,?,?,?)',(identity,project['project_id'],json.dumps(state),'[]',now))
                self.store.connection.execute('UPDATE projects SET freshness_at=?,updated_at=? WHERE project_id=?',(now,now,project['project_id']))
        return {'snapshot_id':identity,'status':'saved','completion_claimed':False,'verification':'unverified owner report','evidence_count':len(identities)}

    def resume(self,project_id):
        project=self._project(project_id)
        row=self.store.connection.execute('SELECT * FROM project_snapshots WHERE project_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1',(project_id,)).fetchone()
        checkpoint={**dict(row),'state':json.loads(row['state_json'])} if row else None
        linked=[]
        for identity in (checkpoint or {}).get('state',{}).get('task_ids',[]):
            task=self._task(identity)
            if task['context_id']!=project['context_id']:raise ValueError('Project task context changed; review required')
            linked.append(task)
        return {'project':project,'checkpoint':checkpoint,'linked_tasks':linked,'attention':self.snapshot(project['context_id'])['tasks'][:10],'apps_opened':False,'completion_basis':'Only task review receipts indicate completion'}

    def dispatch(self,operation,value):
        if operation=='reminders.pending':return self.reminders(value)
        if operation=='reminders.ack':return self.reminders(value,acknowledge=True)
        if operation=='snapshot':return self.snapshot(value.get('context'),query=value.get('query',''),during_chat=value.get('duringChat',False))
        if operation=='task.transition':return self.transition(value)
        if operation=='meeting.preview':return self.meeting_preview(value['evidenceId'])
        if operation=='meeting.process':return self.meeting_process(value)
        if operation=='project.create':return self.project_create(value)
        if operation=='project.checkpoint':return self.checkpoint(value)
        if operation=='project.resume':return self.resume(value['projectId'])
        raise ValueError('Unsupported awareness operation')
