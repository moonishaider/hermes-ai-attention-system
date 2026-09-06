import copy,json,sys,time,unittest
from pathlib import Path
from datetime import datetime,UTC,timedelta
from unittest.mock import patch
from hermes_attention.scoped_browser import policy,WorkerPolicy

class ScopedBrowserTest(unittest.TestCase):
 def fixture(self):
  profile={'app':'Google Chrome','context_id':'personal','account_id':'owner@example.invalid','profile':'Default'}
  grant={**profile,'apps':['Google Chrome'],'status':'active','expired':False,'resources':['native:10:20'],'domains':['example.com'],'operations':['browser.read','browser.navigate','browser.form'],'expires_at':(datetime.now(UTC)+timedelta(hours=1)).isoformat()}
  return grant,profile,{'pid':10,'window_id':20}
 def test_bounded_manifest_excludes_generic_inputs_and_global_grants(self):
  grant,profile,target=self.fixture();m=policy(grant,profile,target)
  self.assertEqual(m['resources']['browser']['origins'],['https://example.com'])
  self.assertFalse(m['resources']['desktop']['display']);self.assertNotIn('click',m['allow']['tools']);self.assertNotIn('get_accessibility_tree',m['allow']['tools']);self.assertNotIn('browser_click',m['allow']['tools'])
  self.assertEqual(m['expires_after'],'600s');self.assertNotIn('grant',json.dumps(m))
  for changed in ({'domains':[]},{'domains':['*.example.com']},{'account_id':'other'},{'context_id':'inside-success'},{'resources':['native:11:20']},{'expired':True}):
   with self.assertRaises(PermissionError):policy({**grant,**changed},profile,target)
 def test_one_route_retains_refs_and_rejects_drift_replay_stop(self):
  sys.path.append(str(Path.home()/'.hermes/hermes-agent'))
  from tools.computer_use.browser_route import CuaTypedBrowserRoute
  calls=[];blocked=[False]
  def call(name,args):
   calls.append((name,args))
   if name=='get_browser_state':
    value={'status':'ok','target_id':'target-one','binding_quality':'exact','mutation_allowed':True,'tabs':[{'tab_id':'tab-one','url':'https://example.com','title':'Example'}]}
    if 'tab_id' in args:value['content_refs']=[{'ref':'p1:1','actions':['type'],'role':'textbox','input_type':'text','label':'City'}]
   else:value={'status':'ok'}
   return {'data':value}
  def check(operation):
   if blocked[0]:raise PermissionError('Emergency stop active')
  grant,profile,target=self.fixture();cfg={'target':target,'manifest':policy(grant,profile,target)}
  route=CuaTypedBrowserRoute(session_id='owned-session',call_tool=call,has_tool=lambda _:True);worker=WorkerPolicy(cfg,route,check)
  worker.dispatch('prepare',{});worker.dispatch('state',target);worker.dispatch('state',{**target,'tab_id':'tab-one'})
  self.assertEqual(worker.dispatch('type',{'tab_id':'tab-one','ref':'p1:1','text':'Synthetic'})['status'],'ok')
  stale=worker.dispatch('type',{'tab_id':'tab-one','ref':'p1:1','text':'Again'});self.assertFalse(stale['ok'])
  with self.assertRaises(PermissionError):worker.dispatch('prepare',{})
  with self.assertRaises(PermissionError):worker.dispatch('state',{**target,'window_id':21})
  with patch('hermes_attention.browser_tasks.public_url',return_value=('other.com',['1.1.1.1'])):
   with self.assertRaises(PermissionError):worker.dispatch('navigate',{'tab_id':'tab-one','url':'https://other.com'})
  with self.assertRaises(PermissionError):worker.dispatch('click',{})
  blocked[0]=True
  with self.assertRaises(PermissionError):worker.dispatch('state',target)
  self.assertTrue(worker.dispatch('stop',{})['revocationRequested'])
  with self.assertRaises(PermissionError):worker.dispatch('state',target)
  self.assertEqual({args['session'] for _,args in calls},{'owned-session'})

 def test_stop_marks_pending_workers_and_hides_live_scope(self):
  import tempfile
  from hermes_attention.scoped_browser import active_scopes,stop_scopes
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory).resolve();base=root/'runtime-data/scoped-browsers';base.mkdir(parents=True,mode=0o700)
   for identity in ('a'*32,'b'*32):
    folder=base/identity;folder.mkdir(mode=0o700)
    cfg={'id':identity,'grant_id':'same-grant','expires_at':time.time()+60,'rpc':str(folder/'rpc.sock'),'target':{'pid':10,'window_id':20 if identity[0]=='a' else 21}}
    p=folder/'scope.json';p.write_text(json.dumps(cfg));p.chmod(0o600)
   (base/('a'*32)/'rpc.sock').touch()
   self.assertEqual(len(active_scopes(root,'same-grant')),1)
   result=stop_scopes(root)
   self.assertEqual(len(result),2);self.assertTrue(all(v['revocationRequested'] for v in result))
   self.assertEqual(active_scopes(root,'same-grant'),[])
   self.assertTrue((base/('b'*32)/'stop-request.json').exists())

 def test_startup_deadline_revokes_scope_before_late_worker_can_launch(self):
  import tempfile
  from hermes_attention.scoped_browser import launch
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory).resolve();sockets=root/'sockets';sockets.mkdir(mode=0o700)
   grant,profile,target=self.fixture();grant['grant_id']='test-grant'
   config={'enabled':True,'app':'synthetic-app','binarySha256':'synthetic'}
   with patch('jarvis_cua_driver.configuration',return_value=(config,'synthetic-binary')),patch('hermes_attention.scoped_browser.subprocess.Popen') as spawn,patch('hermes_attention.scoped_browser.tempfile.mkdtemp',return_value=str(sockets)),patch('hermes_attention.scoped_browser.time.monotonic',side_effect=[0,36]):
    with self.assertRaisesRegex(RuntimeError,'startup unconfirmed'):launch(root,grant,profile,target,owner_session='test-session',generation='initial')
   self.assertEqual(spawn.call_count,1)
   markers=list((root/'runtime-data/scoped-browsers').glob('*/stop-request.json'))
   self.assertEqual(len(markers),1);self.assertEqual(markers[0].stat().st_mode&0o777,0o600)

 def test_quit_barrier_refuses_delayed_confirmed_registration(self):
  import tempfile
  from hermes_attention.scoped_browser import launch,consent_generation,stop_scopes
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory).resolve();generation=consent_generation(root)
   # Full Quit wins before an already-confirmed helper reaches registration.
   self.assertEqual(stop_scopes(root),[])
   self.assertNotEqual(consent_generation(root),generation)
   grant,profile,target=self.fixture();grant['grant_id']='synthetic'
   with patch('jarvis_cua_driver.configuration',return_value=({'enabled':True},'synthetic')),patch('hermes_attention.scoped_browser.subprocess.Popen') as spawn:
    with self.assertRaisesRegex(PermissionError,'predates Stop'):launch(root,grant,profile,target,owner_session='task',generation=generation)
   spawn.assert_not_called();self.assertEqual(list((root/'runtime-data/scoped-browsers').glob('*/scope.json')),[])

class PersistentTransportTest(unittest.IsolatedAsyncioTestCase):
 async def test_private_rpc_keeps_one_mcp_transport_and_stops_exact_daemon(self):
  import asyncio,tempfile,hashlib
  from contextlib import asynccontextmanager
  from types import SimpleNamespace
  from mcp.types import CallToolResult
  from hermes_attention.storage import Store
  from hermes_attention.personal_permissions import Permissions
  from hermes_attention.scoped_browser import serve,rpc,stop_scopes
  sys.path.append(str(Path.home()/'.hermes/hermes-agent'))
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory).resolve();identity='a'*32;folder=root/'runtime-data/scoped-browsers'/identity;folder.mkdir(parents=True,mode=0o700);folder.parent.chmod(0o700)
   binary=root/'pinned';binary.write_bytes(b'synthetic pinned binary')
   store=Store(root/'runtime-data/hermes_attention.sqlite3');permissions=Permissions(store,authorize_owner=lambda *_:True)
   grant=permissions.issue(title='Synthetic',context_id='personal',account_id='owner@example.invalid',profile='Default',operations=['browser.read'],domains=['example.com'],apps=['Google Chrome'])
   profile={'context_id':'personal','account_id':'owner@example.invalid','profile':'Default','app':'Google Chrome'};target={'pid':10,'window_id':20}
   cfg={'id':identity,'grant_id':grant['grant_id'],'profile':profile,'target':target,'expires_at':time.time()+60,'secret':'private-test-secret','rpc':str(root/'rpc.sock'),'driver_socket':str(root/'driver.sock'),'binary':str(binary),'app':'synthetic-app','binarySha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'manifest':policy(grant,profile,target)}
   path=folder/'scope.json';path.write_text(json.dumps(cfg));path.chmod(0o600);events=[]
   @asynccontextmanager
   async def stdio(params):
    events.append(('transport-open',params.args));yield object(),object();events.append(('transport-closed',None))
   class Session:
    def __init__(self,*args):pass
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def initialize(self):events.append(('initialize',None))
    async def list_tools(self):return SimpleNamespace(tools=[SimpleNamespace(name=n) for n in cfg['manifest']['allow']['tools']])
    async def call_tool(self,name,args):
     events.append((name,args));value={'status':'ok'}
     if name=='get_browser_state':value.update(target_id='owned-target',binding_quality='exact',mutation_allowed=True,tabs=[{'tab_id':'owned-tab','url':'https://example.com'}])
     return CallToolResult(content=[],structuredContent=value)
   def command(args,**kw):
    events.append(('process',args))
    if args[0]=='/usr/bin/open':Path(cfg['driver_socket']).touch()
    return SimpleNamespace(returncode=0)
   with patch('mcp.client.stdio.stdio_client',stdio),patch('mcp.ClientSession',Session),patch('hermes_attention.scoped_browser.subprocess.run',side_effect=command):
    task=asyncio.create_task(serve(root,identity))
    for _ in range(100):
     if Path(cfg['rpc']).exists():break
     await asyncio.sleep(.01)
    await asyncio.to_thread(rpc,root,identity,'prepare')
    await asyncio.to_thread(rpc,root,identity,'state',target)
    await asyncio.to_thread(rpc,root,identity,'state',target)
    stopped=await asyncio.to_thread(stop_scopes,root,wait=True)
    self.assertTrue(stopped[0]['revocation_confirmed'])
    await asyncio.wait_for(task,3)
   self.assertEqual(sum(e[0]=='transport-open' for e in events),1);self.assertEqual(sum(e[0]=='initialize' for e in events),1);self.assertEqual(sum(e[0]=='end_session' for e in events),1)
   self.assertFalse(Path(cfg['rpc']).exists());self.assertTrue(json.loads((folder/'stop.json').read_text())['stopped'])
   launches=[e[1] for e in events if e[0]=='process'];self.assertIn('--permission-mode',launches[0]);self.assertIn('bounded',launches[0]);self.assertNotIn('--grant',launches[0]);self.assertEqual(launches[-1],[str(binary),'stop','--socket',cfg['driver_socket']])
   store.close()
