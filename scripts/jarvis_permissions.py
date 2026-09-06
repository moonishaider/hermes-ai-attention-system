#!/usr/bin/env python3
"""Native-only permission management and origin-bound browser runtime dispatch.

The command bridge is not an agent tool. Runtime dispatch cannot issue grants,
choose accounts/profiles/native windows, or rebind API sessions.
"""
from datetime import datetime,UTC
from pathlib import Path
import json,re,sys,secrets,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.append(str(Path.home()/'.hermes/hermes-agent'))
from hermes_attention.personal_permissions import Permissions
from hermes_attention.browser_tasks import BrowserTasks,NativeCUAAdapter
from hermes_attention.service import AttentionService


def _identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',value):raise ValueError('invalid native session identifier')
    return value

def _payload(value):
    if not isinstance(value,dict):raise ValueError('native browser returned no structured state')
    if value.get('ok') is False or value.get('success') is False or value.get('status') in {'refused','error'} or value.get('error'):raise PermissionError('native browser state unavailable: '+str(value.get('code') or value.get('error') or value.get('message'))[:180])
    for key in ('structuredContent','data'):
        if isinstance(value.get(key),dict):return _payload(value[key])
    return value

def _browser_consent_required(value):
    if not isinstance(value,dict):return False
    if isinstance(value.get('refusal'),dict) and value['refusal'].get('code')=='browser_consent_required':return True
    return any(_browser_consent_required(value.get(key)) for key in ('structuredContent','data'))

def discover_chrome_profiles(path,personal_account):
    """Configured metadata only; never reads cookies or attests a live window."""
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size>16*1024*1024:return []
        cache=json.loads(path.read_text()).get('profile',{}).get('info_cache',{})
    except (OSError,ValueError,AttributeError):return []
    if not isinstance(cache,dict):return []
    result=[]
    for directory in ('Default','Profile 1','Profile 2'):
        record=cache.get(directory)
        if not isinstance(record,dict):continue
        account=record.get('user_name')
        # Profile display names and directory numbers never assign a context.
        # Unmapped work/unknown identities remain unavailable, not personal.
        if not isinstance(account,str) or account.strip().casefold()!=personal_account.casefold():continue
        name=record.get('name')
        if not isinstance(name,str) or not name.strip():continue
        result.append({'id':'chrome-'+directory.lower().replace(' ','-'),'label':name+' ('+directory+'; configured)',
                       'context_id':'personal','account_id':personal_account,'profile':directory,'app':'Google Chrome',
                       'profile_marker':name,'account_marker':personal_account,'configured_only':True,
                       'discovery_source':'chrome-local-state-info-cache','native_confirmation_required':True})
    return result

class ObservedBrowserProbe:
    """Checks native browser/chrome AX state against a private owner-selected mapping."""
    def __init__(self,native,profile,*,owner_confirmed=False):self.native=native;self.profile=profile;self.latest=None;self.owner_confirmed=owner_confirmed
    def identity(self,target):
        state=_payload(self.native.state(**target));self.latest=state
        tabs=state.get('tabs',[])
        tab=next((t for t in tabs if t.get('tab_id',t.get('id'))==target.get('tab_id')),None)
        if tab is None and state.get('tab_id')==target.get('tab_id'):tab=state
        if not tab:raise PermissionError('selected tab is absent from current native state')
        # Native AX browser chrome provides profile identity that DOM content alone
        # cannot attest. Match exact configured markers, never infer from task text.
        chrome=self.native._call('capture',mode='ax',pid=target['pid'],window_id=target['window_id'],app=self.profile['app'],max_elements=500)
        chrome_text=json.dumps(chrome,ensure_ascii=False)
        page_text=json.dumps(state,ensure_ascii=False)
        native_identity=state.get('identity') or {}
        structured_match=(native_identity.get('account_id'),native_identity.get('profile'))==(self.profile['account_id'],self.profile['profile'])
        if not structured_match and not self.owner_confirmed:raise PermissionError('native profile/account metadata unavailable; exact-window owner confirmation required')
        profile_marker=self.profile.get('profile_marker');account_marker=self.profile.get('account_marker')
        if not profile_marker or profile_marker not in chrome_text:raise PermissionError('selected Chrome profile not verified in native chrome state')
        if not account_marker or account_marker not in chrome_text+page_text:raise PermissionError('selected account not visible in native evidence')
        url=tab.get('url') or state.get('url')
        if not isinstance(url,str):raise PermissionError('current tab URL unavailable')
        return {'account_id':self.profile['account_id'],'profile':self.profile['profile'],'app':self.profile['app'],'url':url,
                'sensitive':bool(re.search(r'(?i)(accounts\.google\.com|/password|/security|/oauth|/login)',url)),
                'evidence':'native-structured-identity' if structured_match else 'owner-confirmed-exact-window; observed markers are drift hints, not account attestation'}
    def field(self,target,ref):
        state=self.latest
        if not state:raise PermissionError('fresh native state required')
        entries=state.get('content_refs') or state.get('refs') or state.get('snapshot',{}).get('refs',{})
        if isinstance(entries,dict):entry=entries.get(ref)
        else:entry=next((e for e in entries if e.get('ref')==ref),None)
        if not isinstance(entry,dict):raise PermissionError('field ref absent from current native snapshot')
        attrs=entry.get('attributes') or {};role=str(entry.get('role') or attrs.get('role') or '').lower()
        kind=entry.get('input_type') or attrs.get('type') or ('textarea' if attrs.get('tag')=='textarea' else None)
        if not kind:raise PermissionError('native field type unavailable; no guessed typing')
        tabs=state.get('tabs',[]);tab=next((t for t in tabs if t.get('tab_id',t.get('id'))==target.get('tab_id')),state)
        label=str(entry.get('label') or entry.get('name') or '')
        return {'role':role,'type':kind,'label':label,'url':tab.get('url'),
                'sensitive':bool(re.search(r'(?i)password|token|secret|credit.card|card.number|cvv|security.code',label))}

class PermissionsBridge:
    def __init__(self,service,*,native_owner=False,origin_resolver=None,native_factory=NativeCUAAdapter,session_validator=None):
        self.service=service;self.store=service.store;self.runtime=service.paths.runtime_dir
        self.permissions=Permissions(self.store,authorize_owner=lambda op,value:native_owner)
        self.root=self.runtime.parent
        self.origin_resolver=origin_resolver;self.native_factory=native_factory;self.session_validator=session_validator
        self.store.connection.execute('CREATE TABLE IF NOT EXISTS browser_turn_bindings(stage_session_id TEXT PRIMARY KEY,grant_id TEXT NOT NULL,profile_id TEXT,target_json TEXT NOT NULL,revoked INTEGER NOT NULL DEFAULT 0)')
        if 'owner_confirmed' not in {r[1] for r in self.store.connection.execute('PRAGMA table_info(browser_turn_bindings)')}:
            self.store.connection.execute('ALTER TABLE browser_turn_bindings ADD COLUMN owner_confirmed INTEGER NOT NULL DEFAULT 0')
        if 'scope_id' not in {r[1] for r in self.store.connection.execute('PRAGMA table_info(browser_turn_bindings)')}:self.store.connection.execute('ALTER TABLE browser_turn_bindings ADD COLUMN scope_id TEXT')
        self.store.connection.execute('CREATE TABLE IF NOT EXISTS browser_native_selections(token TEXT PRIMARY KEY,state TEXT NOT NULL,session_id TEXT,value_json TEXT NOT NULL,expires_at REAL NOT NULL,nonce TEXT UNIQUE,unused TEXT)')
        self.store.connection.commit()
    def profiles(self):
        value=[{'id':'public','label':'Public research (no signed-in account)','context_id':'personal','account_id':'public','profile':'public-unauthed','app':'none','configured_only':True}]
        path=self.runtime/'browser-profiles.json'
        if path.exists():
            if path.is_symlink() or path.stat().st_mode&0o077:raise PermissionError('browser profile mapping must be private and non-symlink')
            parsed=json.loads(path.read_text())
            for record in parsed.get('profiles',[]):
                if not all(record.get(k) for k in ('id','label','context_id','account_id','profile','app')):raise ValueError('incomplete private browser profile mapping')
                value.append({**record,'configured_only':True})
        else:
            import jarvis_local_state as local
            value.extend(discover_chrome_profiles(Path.home()/'Library/Application Support/Google/Chrome/Local State',local.PERSONAL_ACCOUNT))
        return value
    def _session(self,value):
        sid=_identifier(value)
        if self.session_validator:self.session_validator(sid)
        else:
            import jarvis_local_state as local
            db=local._canonical_session_db()
            try:local._jarvis_session(db,sid)
            finally:db.close()
        return sid
    def _grant_profile(self,gid):
        grant=self.permissions.get(gid)
        if grant['expired'] or grant['status']!='active':raise PermissionError('grant is expired or revoked')
        matches=[p for p in self.profiles() if (p['context_id'],p['account_id'],p['profile'])==(grant['context_id'],grant['account_id'],grant['profile'])]
        if len(matches)!=1:raise PermissionError('grant has no unique configured profile')
        return grant,matches[0]
    def _native(self,sid,scope_id=None):
        native=self.native_factory(session_id=sid)
        if scope_id:
            from hermes_attention.scoped_browser import ScopedCUAAdapter
            return ScopedCUAAdapter(self.root,scope_id,native)
        return native
    def _inventory(self,gid,sid=None):
        grant,profile=self._grant_profile(gid);limitations=[];items=[]
        if profile['id']=='public':targets=[{'target':{},'label':'Cookie-free public research','windowLabel':'No signed-in browser','fingerprint':{}}]
        else:
            native=self.native_factory(session_id='jarvis-owner-target-inventory')
            try:windows=_payload(native._call('list_windows')).get('windows',[])
            except Exception as error:return {'data':[],'limitations':[str(error)[:200]]}
            from hermes_attention.scoped_browser import active_scopes
            scopes=[scope for scope in active_scopes(self.root,gid) if sid and scope.get('owner_session')==sid]
            targets=[]
            for window in windows:
                if window.get('app_name')!=profile['app']:continue
                target={k:window.get(k) for k in ('pid','window_id')}
                if any(type(v) is not int or v<=0 for v in target.values()):continue
                if grant['resources'] and f"native:{target['pid']}:{target['window_id']}" not in grant['resources']:continue
                try:
                    matching=[scope for scope in scopes if scope['target']==target]
                    if len(matching)>1:raise PermissionError('Multiple scoped connections; stop them before selecting')
                    scope_id=matching[0]['id'] if matching else None
                    reader=self._native('jarvis-owner-target-inventory',scope_id) if scope_id else native
                    raw=reader.state(**target)
                    if _browser_consent_required(raw):
                        targets.append({'target':target,'fingerprint':{},'label':'Browser setup required; contents not inspected','windowLabel':str(window.get('title') or 'Browser window')[:200],'native_window_title':window.get('title'),'driverConsentRequired':True})
                        limitations.append('This observed window requires driver-level browser authorization. Jarvis has not enabled remote debugging or inspected its tabs.')
                        continue
                    state=_payload(raw)
                    if state.get('exact_binding') is not True:raise PermissionError('exact browser binding unavailable')
                    for tab in state.get('tabs',[]):
                        if not (tab.get('tab_id') or tab.get('id')) or not isinstance(tab.get('url'),str):continue
                        targets.append({'target':target,'fingerprint':{'url':tab['url'],'title':tab.get('title','')},'scopeId':scope_id,'label':str(tab.get('title') or tab['url'])[:200],'windowLabel':str(window.get('title') or 'Browser window')[:200]})
                except Exception as error:limitations.append(str(error)[:180])
            limitations.append('Account/profile labels are configured. Native confirmation of the exact window is required; page markers do not prove identity. Browser subresource containment is unverified.')
        now=time.time()
        with self.store.connection:
            self.store.connection.execute('DELETE FROM browser_native_selections WHERE expires_at<?',(now,))
            for target in targets:
                token=secrets.token_urlsafe(24)
                value={**target,'grantId':gid,'profile_id':profile['id'],'accountLabel':profile['account_id'],'profileLabel':profile['label'],'profile_binding':{k:profile.get(k) for k in ('context_id','account_id','profile','app','profile_marker','account_marker')}}
                self.store.connection.execute('INSERT INTO browser_native_selections VALUES(?,?,?,?,?,?,?)',(token,'inventory',None,json.dumps(value),now+300,None,None))
                items.append({'targetId':token,**{k:value[k] for k in ('label','accountLabel','profileLabel','windowLabel')}})
        return {'data':items,'limitations':limitations}
    def _selection_row(self,token,state):
        row=self.store.connection.execute('SELECT * FROM browser_native_selections WHERE token=?',(token,)).fetchone()
        if not row or row['state']!=state or row['expires_at']<=time.time():raise PermissionError('selection is absent, used or expired')
        value=json.loads(row['value_json']);grant,profile=self._grant_profile(value['grantId'])
        if value['profile_binding']!={k:profile.get(k) for k in value['profile_binding']}:raise PermissionError('profile mapping changed since selection')
        return row,value,profile
    def _fresh_target(self,value,profile,sid,confirmed):
        if profile['id']=='public':return {}
        native=self._native(sid,value.get('scopeId'));target=value['target'];state=_payload(native.state(**target))
        if state.get('exact_binding') is not True:raise PermissionError('exact browser binding unavailable')
        matches=[t for t in state.get('tabs',[]) if {'url':t.get('url'),'title':t.get('title','')}==value['fingerprint']]
        if len(matches)!=1:raise PermissionError('selected tab changed or is ambiguous; select it again')
        target={**target,'tab_id':matches[0].get('tab_id') or matches[0].get('id')}
        ObservedBrowserProbe(native,profile,owner_confirmed=confirmed).identity(target)
        return target
    def selection(self,operation,request):
        self.permissions._owner(operation,request)
        if operation=='browser_targets':return self._inventory(request['grantId'],self._session(request['sessionId']) if request.get('sessionId') else None)
        if operation=='prepare-selection':
            sid=self._session(request['sessionId']);row,value,profile=self._selection_row(request['targetId'],'inventory')
            if value['grantId']!=request['grantId']:raise PermissionError('target grant differs')
            if value.get('scopeId'):
                from hermes_attention.scoped_browser import read_scope
                if read_scope(self.root,value['scopeId']).get('owner_session')!=sid:raise PermissionError('Scoped browser belongs to another conversation')
            if value.get('driverConsentRequired'):
                from hermes_attention.scoped_browser import policy,consent_generation
                value['scopeGeneration']=consent_generation(self.root)
                grant,_=self._grant_profile(value['grantId']);policy(grant,profile,value['target'])
            # Before confirmation, only native exact bind metadata is used; account
            # labels are expressly configured values requiring owner attestation.
            nonce=secrets.token_urlsafe(32)
            with self.store.connection:
                changed=self.store.connection.execute("UPDATE browser_native_selections SET state='prepared',session_id=?,nonce=?,expires_at=?,value_json=? WHERE token=? AND state='inventory'",(sid,nonce,time.time()+120,json.dumps(value),row['token'])).rowcount
                if changed!=1:raise PermissionError('target already selected')
            text='Allow this Jarvis conversation to use '+value['label']+' in '+value['windowLabel']+'? Confirm that this exact window belongs to '+value['accountLabel']+' / '+value['profileLabel']+'. Existing task permission limits still apply.'
            if value.get('driverConsentRequired'):
                text='Confirm this observed window belongs to '+value['accountLabel']+' / '+value['profileLabel']+': '+value['windowLabel']+'. Browser preparation may open a temporary setup tab and enable Chrome remote debugging. Stop would revoke the driver connection but would not turn that Chrome setting off. Allow Jarvis to prepare this exact window in a separate task-only driver, restricted to the grant domains and operations for at most ten minutes? No sends, generic clicks, or global browser grant are enabled.'
                text+=' Allowed HTTPS domains: '+', '.join(grant['domains'])+'. Task operations: '+', '.join(grant['operations'])+'.'
            return {'nonce':nonce,'confirmationText':text}
        if operation=='commit-selection':
            row=self.store.connection.execute('SELECT token FROM browser_native_selections WHERE nonce=?',(request['nonce'],)).fetchone()
            if not row:raise PermissionError('native confirmation missing')
            row,value,profile=self._selection_row(row['token'],'prepared');self._session(row['session_id'])
            if value.get('driverConsentRequired'):
                native=self.native_factory(session_id='jarvis-owner-window-recheck')
                windows=_payload(native._call('list_windows')).get('windows',[])
                matches=[w for w in windows if w.get('pid')==value['target']['pid'] and w.get('window_id')==value['target']['window_id'] and w.get('app_name')==profile['app'] and w.get('title')==value.get('native_window_title')]
                if len(matches)!=1:raise PermissionError('Observed browser window changed; select it again')
                from hermes_attention.scoped_browser import launch,policy
                grant,_=self._grant_profile(value['grantId']);policy(grant,profile,value['target'])
                with self.store.connection:
                    changed=self.store.connection.execute("UPDATE browser_native_selections SET state='setup-requested',nonce=NULL WHERE token=? AND state='prepared'",(row['token'],)).rowcount
                    if changed!=1:raise PermissionError('confirmation already used')
                scoped=launch(self.root,grant,profile,value['target'],owner_session=row['session_id'],generation=value.get('scopeGeneration'))
                _payload(scoped['result'])
                return {'status':'setup-complete','message':'Browser setup completed for this bounded task. Show observed browser targets again to choose an exact tab. Stop revokes this connection; Chrome remote debugging remains a separate browser setting.','scopeId':scoped['scopeId'],'sideEffects':scoped['result'].get('side_effects',{}),'bound':False}
            self._fresh_target(value,profile,'jarvis-owner-selection-'+row['token'],True)
            with self.store.connection:
                changed=self.store.connection.execute("UPDATE browser_native_selections SET state='selected',nonce=NULL,expires_at=? WHERE token=? AND state='prepared'",(time.time()+600,row['token'])).rowcount
                if changed!=1:raise PermissionError('confirmation already used')
            return {'selectionId':row['token'],'expiresAt':datetime.fromtimestamp(time.time()+600,UTC).isoformat(),'status':'selected',**{k:value[k] for k in ('grantId','label','accountLabel','profileLabel','windowLabel')}}
        if operation=='bind-selection':
            sid=self._session(request['sessionId']);row,value,profile=self._selection_row(request['selectionId'],'selected')
            if row['session_id']!=sid:raise PermissionError('selection belongs to another conversation')
            stage=_identifier(request['stageSessionId']);target=self._fresh_target(value,profile,stage,True)
            result=self.management('bind-turn',{'stage_session_id':stage,'grant_id':value['grantId'],'profile_id':profile['id'],'target':target,'owner_confirmed_target':profile['id']!='public','scope_id':value.get('scopeId')})
            return {**result,'selectionId':row['token']}
        raise ValueError('unsupported selection operation')

    def management(self,operation,request=None):
        request=request or {}
        if operation in {'browser_targets','prepare-selection','commit-selection','bind-selection'}:return self.selection(operation,request)
        if operation=='snapshot':
            grants=self.permissions.list()
            for grant in grants:
                audit=self.store.connection.execute('SELECT operation,result,created_at FROM personal_grant_audit WHERE grant_id=? ORDER BY created_at DESC LIMIT 1',(grant['grant_id'],)).fetchone()
                grant['last_receipt']=dict(audit) if audit else None
                grant['last_audit']=grant['last_receipt']
            return {'grants':grants,'stops':[dict(r) for r in self.store.connection.execute('SELECT * FROM personal_capability_stops')],'profiles':[{k:v for k,v in p.items() if k not in {'profile_marker','account_marker'}} for p in self.profiles()]}
        if operation=='issue':
            matched=[p for p in self.profiles() if (p['context_id'],p['account_id'],p['profile'])==(request.get('context_id'),request.get('account_id'),request.get('profile'))]
            if len(matched)!=1:raise PermissionError('account/profile/context must match one configured identity; relabeling is unavailable')
            profile=matched[0]
            if request.get('apps') and set(request['apps'])-{profile['app']}:raise PermissionError('app differs from configured profile')
            if profile['id']=='public' and set(request.get('operations',[]))-{'browser.read','browser.download'}:raise PermissionError('public identity supports cookie-free research/download only')
            return self.permissions.issue(**request)
        if operation=='revoke':
            self.permissions.revoke(request['grant_id'])
            from hermes_attention.scoped_browser import stop_scopes
            return {'revoked':True,'scopedBrowsers':stop_scopes(self.root,request['grant_id'])}
        if operation=='stop':
            self.permissions.stop(request['capability'],request.get('stopped',True))
            from hermes_attention.scoped_browser import stop_scopes
            stopped=request.get('stopped',True)
            return {'stopped':stopped,'scopedBrowsers':stop_scopes(self.root) if stopped and (request['capability']=='all' or request['capability'].startswith('browser.')) else []}
        if operation=='bind-turn':
            self.permissions._owner('bind-turn',request)
            sid=_identifier(request['stage_session_id']);grant=self.permissions.get(request['grant_id'])
            if grant['expired'] or grant['status']!='active':raise PermissionError('cannot bind revoked/expired grant')
            target=request.get('target') or {};profile_id=request.get('profile_id','public')
            profile=next((p for p in self.profiles() if p['id']==profile_id),None)
            if not profile or (profile['context_id'],profile['account_id'],profile['profile'])!=(grant['context_id'],grant['account_id'],grant['profile']):raise PermissionError('native profile binding differs from grant')
            if profile_id!='public':
                if set(target)!={'pid','window_id','tab_id'}:raise ValueError('exact native pid/window/tab required')
                for k in ('pid','window_id'):
                    if type(target[k]) is not int or target[k]<=0:raise ValueError('positive native target required')
                if request.get('scope_id'):
                    from hermes_attention.scoped_browser import read_scope
                    scope=read_scope(self.root,request['scope_id'])
                    if scope['grant_id']!=grant['grant_id'] or scope['target']!={k:target[k] for k in ('pid','window_id')}:raise PermissionError('Scoped browser belongs to another grant or window')
                native=self._native(sid,request.get('scope_id'));ObservedBrowserProbe(native,profile,owner_confirmed=request.get('owner_confirmed_target') is True).identity(target)
            existing=self.store.connection.execute('SELECT * FROM browser_turn_bindings WHERE stage_session_id=?',(sid,)).fetchone()
            if existing and (existing['revoked'] or existing['grant_id']!=grant['grant_id'] or existing['target_json']!=json.dumps(target,sort_keys=True) or existing['scope_id']!=request.get('scope_id')):raise PermissionError('API stage cannot be rebound or reactivated')
            with self.store.connection:self.store.connection.execute('INSERT OR IGNORE INTO browser_turn_bindings(stage_session_id,grant_id,profile_id,target_json,revoked,owner_confirmed) VALUES(?,?,?,?,0,?)',(sid,grant['grant_id'],profile_id,json.dumps(target,sort_keys=True),int(request.get('owner_confirmed_target') is True)))
            if request.get('scope_id'):
                with self.store.connection:self.store.connection.execute('UPDATE browser_turn_bindings SET scope_id=? WHERE stage_session_id=?',(request['scope_id'],sid))
            return {'bound':True,'stage_session_id':sid,'grant_id':grant['grant_id']}
        if operation=='unbind-turn':
            self.permissions._owner('unbind-turn',request)
            with self.store.connection:self.store.connection.execute('UPDATE browser_turn_bindings SET revoked=1 WHERE stage_session_id=?',(_identifier(request['stage_session_id']),))
            return {'revoked':True}
        raise ValueError('unsupported native permission operation')
    def dispatch(self,operation,payload=None):
        """Agent-visible: select no grants, accounts, profiles, sessions or paths."""
        if self.origin_resolver:origin=self.origin_resolver()
        else:
            from tools.async_delegation import _current_origin_session_id
            origin=_current_origin_session_id()
        binding=self.store.connection.execute('SELECT * FROM browser_turn_bindings WHERE stage_session_id=?',(origin,)).fetchone() if origin else None
        if not binding or binding['revoked']:raise PermissionError('browser requires a current native-issued Jarvis task grant')
        payload=payload or {};allowed={'research':{'url'},'download':{'url','filename'},'read':set(),'navigate':{'url'},'prepare-field':{'ref','text'}}
        if operation not in allowed or set(payload)-allowed[operation]:raise PermissionError('unavailable browser operation or authority-bearing arguments')
        profile=next((p for p in self.profiles() if p['id']==binding['profile_id']),None)
        if not profile:raise PermissionError('configured browser profile removed')
        target=json.loads(binding['target_json']);native=self._native(origin,binding['scope_id'])
        probe=ObservedBrowserProbe(native,profile,owner_confirmed=bool(binding['owner_confirmed']))
        actor=BrowserTasks(self.permissions,download_root=self.runtime/'browser-downloads',native=native,identity_probe=probe.identity,field_probe=probe.field)
        gid=binding['grant_id']
        if operation=='research':return actor.research(gid,**payload)
        if operation=='download':return actor.download(gid,**payload)
        if operation=='read':return actor.native_read(gid,target)
        if operation=='navigate':return actor.navigate(gid,target,**payload)
        return actor.prepare_field(gid,target,**payload)

def main():
    service=None
    try:
        raw=sys.stdin.buffer.read(1048577)
        if len(raw)>1048576:raise ValueError('permission request too large')
        value=json.loads(raw);service=AttentionService()
        result=PermissionsBridge(service,native_owner=True).management(value['operation'],value.get('request',{}))
        print(json.dumps({'ok':True,'result':result},ensure_ascii=False));return 0
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error)[:400]}));return 2
    finally:
        if service:service.close()
if __name__=='__main__':raise SystemExit(main())
