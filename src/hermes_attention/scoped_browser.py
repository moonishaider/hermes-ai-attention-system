"""Native-approved, task-owned bounded CUA worker. No model-selected launcher flags.

One persistent MCP transport owns all target/tab/ref capabilities. The private
worker accepts only fixed typed browser operations and checks the durable grant
before every operation. No generic desktop input or existing-profile global grant.
"""
import asyncio,fcntl,hashlib,json,os,re,secrets,socket,sqlite3,subprocess,sys,tempfile,time
from pathlib import Path
from contextlib import contextmanager
from urllib.parse import urlsplit

TOOLS={'state':'get_browser_state','navigate':'browser_navigate','type':'browser_type'}
def private(path):
    path=Path(path)
    if any(p.is_symlink() for p in (path,*path.parents)):raise PermissionError('Scoped browser paths must not be redirected')
    if path.exists() and (path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077):raise PermissionError('Private owner path required')
    return path

def policy(grant,profile,target,*,now=None):
    from datetime import datetime,UTC
    now=time.time() if now is None else now
    if grant['status']!='active' or grant['expired']:raise PermissionError('Active browser grant required')
    if profile['context_id']!='personal' or grant['context_id']!='personal':raise PermissionError('Scoped existing-profile setup currently supports personal tasks only')
    if profile['app']!='Google Chrome' or profile['app'] not in grant['apps']:raise PermissionError('Exact configured Chrome app required')
    if (profile['account_id'],profile['profile'])!=(grant['account_id'],grant['profile']):raise PermissionError('Profile differs from grant')
    if set(target)!={'pid','window_id'} or any(type(v) is not int or v<=0 for v in target.values()):raise PermissionError('Exact native window required')
    if grant['resources'] and f"native:{target['pid']}:{target['window_id']}" not in grant['resources']:raise PermissionError('Window is outside grant')
    domains=grant['domains']
    if not domains or any(not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?',d) or '..' in d for d in domains):raise PermissionError('Choose exact HTTPS domains before browser setup')
    remaining=min(600,int(datetime.fromisoformat(grant['expires_at']).timestamp()-now))
    if remaining<30:raise PermissionError('Grant expires too soon for browser setup')
    operations=set(grant['operations']);tools=['start_session','end_session','list_windows','browser_prepare','get_browser_state']
    if 'browser.read' not in operations:raise PermissionError('Browser read grant required for verification')
    if 'browser.navigate' in operations:tools.append('browser_navigate')
    if 'browser.form' in operations:tools.append('browser_type')
    return {'version':3,'expires_after':str(remaining)+'s','idle_timeout':'120s','allow':{'tools':tools},'resources':{'apps':[{'bundle_id':'com.google.Chrome','launch':False,'windows':'all','terminate':'deny'}],'browser':{'profiles':[{'kind':'existing_profile'}],'origins':['https://'+d for d in domains]},'desktop':{'display':False}}}

def scope_path(root,identity):
    if not re.fullmatch(r'[a-f0-9]{32}',identity):raise PermissionError('Invalid scoped browser identity')
    return private(Path(root)/'runtime-data/scoped-browsers'/identity/'scope.json')

def read_scope(root,identity):return json.loads(scope_path(root,identity).read_text())
def rpc(root,identity,operation,args=None,*,timeout=40):
    cfg=read_scope(root,identity);endpoint=private(cfg['rpc']);message=json.dumps({'secret':cfg['secret'],'operation':operation,'args':args or {}}).encode()+b'\n'
    with socket.socket(socket.AF_UNIX) as stream:
        stream.settimeout(timeout);stream.connect(str(endpoint));stream.sendall(message);reader=stream.makefile('rb');raw=reader.readline(4_000_001)
    if len(raw)>4_000_000:raise RuntimeError('Scoped browser response exceeds bound')
    result=json.loads(raw)
    if not result.get('ok'):raise RuntimeError(result.get('error','Scoped browser failed; outcome unconfirmed'))
    return result['result']

def request_stop(root,identity):
    """Durable deny-only signal, including a worker that has not started yet."""
    folder=scope_path(root,identity).parent
    marker=private(folder/'stop-request.json')
    fd=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as stream:json.dump({'requested_at':time.time(),'scopeId':identity},stream)
    return {'scopeId':identity,'revocationRequested':True,'chromeSettingRestored':False}

@contextmanager
def registration(root):
    folder=Path(root)/'runtime-data/scoped-browsers'
    folder.mkdir(parents=True,exist_ok=True,mode=0o700);private(folder)
    fd=os.open(private(folder/'registration.lock'),os.O_RDWR|os.O_CREAT,0o600)
    with os.fdopen(fd,'r+') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        try:yield folder
        finally:fcntl.flock(stream,fcntl.LOCK_UN)

def _generation(folder):
    path=private(folder/'generation.json')
    return json.loads(path.read_text())['generation'] if path.exists() else 'initial'

def consent_generation(root):
    with registration(root) as folder:return _generation(folder)

def launch(root,grant,profile,target,*,owner_session,generation):
    """Called only after the native nonce-confirmation is consumed."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',owner_session):raise PermissionError('Canonical owner session required')
    root=Path(root);manifest=policy(grant,profile,target)
    # The existing reviewed configuration validates signed-bundle path and hash.
    import jarvis_cua_driver
    config,binary=jarvis_cua_driver.configuration(root)
    if config['enabled'] is not True:raise PermissionError('Native driver is not enabled')
    with registration(root) as registry:
        if generation!=_generation(registry):raise PermissionError('Browser setup confirmation predates Stop or Full Quit; confirm again')
        identity=secrets.token_hex(16);folder=root/'runtime-data/scoped-browsers'/identity
        folder.mkdir(mode=0o700);private(folder)
        sockets=Path(tempfile.mkdtemp(prefix='jarvis-cua-')).resolve();sockets.chmod(0o700)
        cfg={'id':identity,'owner_session':owner_session,'grant_id':grant['grant_id'],'profile':profile,'target':target,'expires_at':min(time.time()+600,__import__('datetime').datetime.fromisoformat(grant['expires_at']).timestamp()),'secret':secrets.token_urlsafe(32),'rpc':str(sockets/'rpc.sock'),'driver_socket':str(sockets/'driver.sock'),'binary':binary,'app':config['app'],'binarySha256':config['binarySha256'],'manifest':manifest,'status':'starting'}
        path=folder/'scope.json';path.write_text(json.dumps(cfg));path.chmod(0o600)
    env={k:v for k,v in os.environ.items() if k in {'HOME','PATH','TMPDIR','LANG','USER','LOGNAME'}}
    with (folder/'worker.log').open('xb') as log:
        os.chmod(log.name,0o600)
        subprocess.Popen([sys.executable,str(root/'scripts/jarvis_scoped_browser.py'),identity],cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        if Path(cfg['rpc']).exists():
            try:
                result=rpc(root,identity,'prepare')
                if result.get('ok') is False or result.get('status') in {'refused','error'} or result.get('isError'):raise RuntimeError(result.get('message','Scoped browser preparation refused'))
                return {'scopeId':identity,'result':result}
            except Exception:
                try:request_stop(root,identity)
                except Exception:pass
                raise
        if (folder/'failure.json').exists():
            request_stop(root,identity)
            raise RuntimeError(json.loads((folder/'failure.json').read_text())['error'])
        time.sleep(.1)
    request_stop(root,identity)
    raise RuntimeError('Scoped browser startup unconfirmed; no automatic retry. Inspect its retained worker receipt.')

def active_scopes(root,grant_id):
    folder=Path(root)/'runtime-data/scoped-browsers'
    if not folder.exists():return []
    private(folder);result=[]
    for p in folder.glob('*/scope.json'):
        private(p);v=json.loads(p.read_text())
        if v['grant_id']==grant_id and v['expires_at']>time.time() and Path(v['rpc']).exists() and not any((p.parent/name).exists() for name in ('stop-request.json','stop.json','failure.json')):result.append(v)
    return result

def stop_scopes(root,grant_id=None,*,wait=False):
    out=[]
    with registration(root) as folder:
        if grant_id is None:
            path=private(folder/'generation.json')
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w') as stream:json.dump({'generation':secrets.token_hex(16),'stopped_at':time.time()},stream)
        for p in folder.glob('*/scope.json'):
            private(p);v=json.loads(p.read_text())
            if grant_id is not None and v['grant_id']!=grant_id:continue
            out.append(request_stop(root,v['id']))
    # Mark every scope before waiting; no new request can retain authority.
    if wait:
        deadline=time.monotonic()+12
        while time.monotonic()<deadline and any(not (scope_path(root,v['scopeId']).parent/'stop.json').exists() for v in out):time.sleep(.1)
    for v in out:
        receipt=scope_path(root,v['scopeId']).parent/'stop.json'
        v['revocation_confirmed']=receipt.exists() and json.loads(receipt.read_text()).get('stopped') is True
    return out

class ScopedCUAAdapter:
    def __init__(self,root,identity,delegate):self.root=root;self.identity_id=identity;self.delegate=delegate
    def _call(self,action,**args):
        # Existing native AX evidence is an independent owner-window drift check.
        if action not in {'capture','list_windows'}:raise PermissionError('Generic action unavailable in scoped browser')
        return self.delegate._call(action,**args)
    def state(self,*,pid,window_id,tab_id=None):return rpc(self.root,self.identity_id,'state',{'pid':pid,'window_id':window_id,**({'tab_id':tab_id} if tab_id is not None else {})})
    def navigate(self,*,tab_id,url):return rpc(self.root,self.identity_id,'navigate',{'tab_id':tab_id,'url':url})
    def type_field(self,*,tab_id,ref,text):return rpc(self.root,self.identity_id,'type',{'tab_id':tab_id,'ref':ref,'text':text})
    def protected_network(self,target):return False

class WorkerPolicy:
    def __init__(self,cfg,route,check):self.cfg=cfg;self.route=route;self.check=check;self.prepared=False;self.stopped=False
    def dispatch(self,operation,args):
        if self.stopped:raise PermissionError('Scoped browser stopped')
        if operation=='stop':self.stopped=True;return {'revocationRequested':True,'chromeSettingRestored':False}
        self.check(operation)
        if operation=='prepare':
            if args or self.prepared:raise PermissionError('Browser preparation cannot replay')
            self.prepared=True
            return self.route.prepare(**self.cfg['target'],profile_mode='existing_profile',profile_name=None,allow_launch=False)
        if not self.prepared:raise PermissionError('Native preparation required')
        if operation=='state':
            if set(args)-{'pid','window_id','tab_id'} or any(args.get(k)!=v for k,v in self.cfg['target'].items()):raise PermissionError('Different native target refused')
            bound=self.route.observe(**self.cfg['target'])
            if args.get('tab_id') is None:return bound
            return {**bound,**self.route.observe(tab_id=args['tab_id']),'tabs':bound.get('tabs',[])}
        if operation=='navigate' and set(args)=={'tab_id','url'}:
            from .browser_tasks import public_url
            host,_=public_url(args['url'])
            if 'https://'+host not in self.cfg['manifest']['resources']['browser']['origins']:raise PermissionError('Origin outside scoped browser')
            return self.route.mutate('browser_navigate',tab_id=args['tab_id'],args={'url':args['url']})
        if operation=='type' and set(args)=={'tab_id','ref','text'}:
            if not isinstance(args['text'],str) or len(args['text'])>10000:raise PermissionError('Bounded plain text required')
            return self.route.mutate('browser_type',tab_id=args['tab_id'],args={'ref':args['ref'],'text':args['text'],'mode':'insert_text'})
        raise PermissionError('Scoped browser operation or arguments unavailable')

async def serve(root,identity):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from tools.computer_use.browser_route import CuaTypedBrowserRoute
    from tools.computer_use.cua_backend import _extract_tool_result
    root=Path(root);cfg=read_scope(root,identity);folder=scope_path(root,identity).parent
    if hashlib.sha256(Path(cfg['binary']).read_bytes()).hexdigest()!=cfg['binarySha256']:raise PermissionError('Pinned driver changed')
    manifest=folder/'capabilities.json';manifest.write_text(json.dumps(cfg['manifest']));manifest.chmod(0o600)
    env={k:v for k,v in os.environ.items() if k in {'HOME','PATH','TMPDIR','LANG','USER','LOGNAME'}};env['CUA_DRIVER_RS_TELEMETRY_ENABLED']='0'
    # LaunchServices preserves the signed CuaDriver application permission identity.
    launch_command=['/usr/bin/open','-n','-a',cfg['app'],'--args','serve','--socket',cfg['driver_socket'],'--permission-mode','bounded','--capability-manifest',str(manifest),'--approve-capability-manifest']
    loop=asyncio.get_running_loop();ending=asyncio.Event();lock=asyncio.Lock();server=None
    db=sqlite3.connect((root/'runtime-data/hermes_attention.sqlite3').as_uri()+'?mode=ro',uri=True,check_same_thread=False);db.row_factory=sqlite3.Row
    def check(operation):
        if (folder/'stop-request.json').exists():raise PermissionError('Scoped browser stop requested')
        if time.time()>=cfg['expires_at']:raise PermissionError('Scoped browser expired')
        row=db.execute('SELECT * FROM personal_grants WHERE grant_id=?',(cfg['grant_id'],)).fetchone()
        if not row or row['status']!='active' or __import__('datetime').datetime.fromisoformat(row['expires_at']).timestamp()<=time.time():raise PermissionError('Browser grant revoked or expired')
        operation={'prepare':'browser.read','state':'browser.read','navigate':'browser.navigate','type':'browser.form'}[operation]
        if operation not in json.loads(row['operations_json']):raise PermissionError('Operation not granted')
        if db.execute("SELECT 1 FROM personal_capability_stops WHERE stopped=1 AND capability IN ('all',?)",(operation,)).fetchone():raise PermissionError('Emergency stop active')
        if (row['account_id'],row['profile'],row['context_id'])!=(cfg['profile']['account_id'],cfg['profile']['profile'],cfg['profile']['context_id']):raise PermissionError('Grant identity changed')
    try:
        check('prepare')
        subprocess.run(launch_command,check=True,env=env,timeout=10)
        deadline=loop.time()+20
        while not Path(cfg['driver_socket']).exists():
            check('prepare')
            if loop.time()>deadline:raise RuntimeError('Task driver did not expose its private endpoint')
            await asyncio.sleep(.1)
        check('prepare')
        params=StdioServerParameters(command=cfg['binary'],args=['mcp','--socket',cfg['driver_socket']],env=env)
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await asyncio.wait_for(session.initialize(),10);check('prepare')
                listed=await asyncio.wait_for(session.list_tools(),10);check('prepare');names={t.name for t in listed.tools}
                async def call_async(name,args):
                    check({'browser_prepare':'prepare','get_browser_state':'state','browser_navigate':'navigate','browser_type':'type'}.get(name,'state'))
                    result=await asyncio.wait_for(session.call_tool(name,args),30)
                    return _extract_tool_result(result)
                def call(name,args):return asyncio.run_coroutine_threadsafe(call_async(name,args),loop).result(32)
                route=CuaTypedBrowserRoute(session_id='jarvis-'+identity,call_tool=call,has_tool=lambda name:name in names)
                worker=WorkerPolicy(cfg,route,check)
                await asyncio.wait_for(session.call_tool('start_session',{'session':'jarvis-'+identity}),10);check('prepare')
                async def client(reader,writer):
                    try:
                        raw=await asyncio.wait_for(reader.readline(),5)
                        if len(raw)>20000:raise PermissionError('Request too large')
                        value=json.loads(raw)
                        if set(value)!={'secret','operation','args'} or not secrets.compare_digest(str(value['secret']),cfg['secret']):raise PermissionError('Private worker identity required')
                        async with lock:
                            result=await asyncio.to_thread(worker.dispatch,value['operation'],value['args'])
                        if worker.stopped:ending.set()
                        data={'ok':True,'result':result}
                    except Exception as e:data={'ok':False,'error':str(e)[:400]}
                    writer.write(json.dumps(data).encode()+b'\n');await writer.drain();writer.close();await writer.wait_closed()
                server=await asyncio.start_unix_server(client,path=cfg['rpc'],limit=20001);os.chmod(cfg['rpc'],0o600)
                while not ending.is_set():
                    try:await asyncio.wait_for(ending.wait(),1)
                    except asyncio.TimeoutError:
                        try:check('state')
                        except PermissionError:ending.set()
                server.close();await server.wait_closed()
                await asyncio.wait_for(session.call_tool('end_session',{'session':'jarvis-'+identity}),3)
    finally:
        if server:server.close();await server.wait_closed()
        # Deny-only shutdown is addressed solely to this generated private endpoint.
        try:
            result=subprocess.run([cfg['binary'],'stop','--socket',cfg['driver_socket']],env=env,capture_output=True,timeout=10)
            receipt={'stopped':result.returncode==0,'chromeSettingRestored':False,'scopeId':identity}
        except Exception as error:receipt={'stopped':False,'error':str(error)[:200],'chromeSettingRestored':False,'scopeId':identity}
        (folder/'stop.json').write_text(json.dumps(receipt));(folder/'stop.json').chmod(0o600);db.close()
        if Path(cfg['rpc']).exists():Path(cfg['rpc']).unlink()
