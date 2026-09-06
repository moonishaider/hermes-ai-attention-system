import importlib.util
from pathlib import Path
import tempfile,json,unittest
from types import SimpleNamespace
from hermes_attention.storage import Store
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('permission_bridge',ROOT/'scripts/jarvis_permissions.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class NativeFixture:
    def __init__(self,**kw):pass
    def state(self,**kw):return {'status':'ok','identity':{'account_id':'owner@example.invalid','profile':'Personal'},'tabs':[{'tab_id':'tab','url':'https://example.invalid/form'}],'refs':{'r1':{'role':'textbox','input_type':'text','label':'City'}}}
    def _call(self,action,**kw):return {'text_summary':'Profile Personal owner@example.invalid'}
class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.store=Store(':memory:');self.service=SimpleNamespace(store=self.store,paths=SimpleNamespace(runtime_dir=self.root))
        self.bridge=module.PermissionsBridge(self.service,native_owner=True,native_factory=NativeFixture,session_validator=lambda sid: sid)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_metadata_discovery_never_infers_personal_from_profile_name(self):
        p=self.root/'Local State'
        p.write_text(json.dumps({'profile':{'info_cache':{'Profile 1':{'name':'Personal','user_name':'work@example.invalid'},'Profile 2':{'name':'Owner','user_name':'owner@example.invalid','secret_cookie':'must-not-copy'}}}}))
        records=module.discover_chrome_profiles(p,'owner@example.invalid')
        self.assertEqual(len(records),1);self.assertEqual(records[0]['profile'],'Profile 2')
        self.assertTrue(records[0]['configured_only']);self.assertTrue(records[0]['native_confirmation_required'])
        self.assertNotIn('secret_cookie',json.dumps(records));self.assertEqual(records[0]['context_id'],'personal')
        p.write_text('{invalid');self.assertEqual(module.discover_chrome_profiles(p,'owner@example.invalid'),[])
    def test_default_profile_requires_same_exact_configured_account(self):
        p=self.root/'Local State';p.write_text(json.dumps({'profile':{'info_cache':{'Default':{'name':'Person 1','user_name':'owner@example.invalid'}}}}))
        records=module.discover_chrome_profiles(p,'owner@example.invalid')
        self.assertEqual(records[0]['profile'],'Default');self.assertEqual(records[0]['profile_marker'],'Person 1')
        self.assertEqual(module.discover_chrome_profiles(p,'different@example.invalid'),[])
    def test_private_mapping_precedes_discovery_including_empty_mapping(self):
        from unittest.mock import patch
        p=self.root/'browser-profiles.json';p.write_text('{"profiles":[]}');p.chmod(0o600)
        with patch.object(module,'discover_chrome_profiles',side_effect=AssertionError('discovery must not run')):
            self.assertEqual([p['id'] for p in self.bridge.profiles()],['public'])
    def test_metadata_discovery_missing_identity_and_symlink_unavailable(self):
        p=self.root/'Local State';p.write_text(json.dumps({'profile':{'info_cache':{'Profile 1':{'name':'Personal'},'Profile 2':{'name':'Personal','user_name':''}}}}))
        self.assertEqual(module.discover_chrome_profiles(p,'owner@example.invalid'),[])
        link=self.root/'linked';link.symlink_to(p)
        self.assertEqual(module.discover_chrome_profiles(link,'owner@example.invalid'),[])
    def issue(self):return self.bridge.management('issue',{'title':'Research','context_id':'personal','account_id':'public','profile':'public-unauthed','operations':['browser.read']})
    def test_public_issue_bind_current_origin_and_no_model_mint(self):
        grant=self.issue();self.bridge.management('bind-turn',{'stage_session_id':'stage1','grant_id':grant['grant_id']})
        runtime=module.PermissionsBridge(self.service,origin_resolver=lambda:'stage1',native_factory=NativeFixture)
        with self.assertRaises(PermissionError):runtime.dispatch('issue',{})
        with self.assertRaises(PermissionError):runtime.dispatch('research',{'url':'https://example.invalid','grant_id':'fake'})
        unbound=module.PermissionsBridge(self.service,origin_resolver=lambda:'other')
        with self.assertRaises(PermissionError):unbound.dispatch('read',{})
    def test_revoked_binding_cannot_reactivate(self):
        grant=self.issue();request={'stage_session_id':'stage1','grant_id':grant['grant_id']}
        self.bridge.management('bind-turn',request);self.bridge.management('unbind-turn',{'stage_session_id':'stage1'})
        with self.assertRaises(PermissionError):self.bridge.management('bind-turn',request)
    def test_profile_cannot_be_relabelled_personal(self):
        p=self.root/'browser-profiles.json';p.write_text(json.dumps({'profiles':[{'id':'work','label':'Work','context_id':'inside-success','account_id':'work@example.invalid','profile':'Work profile','app':'Chrome'}]}));p.chmod(0o600)
        with self.assertRaises(PermissionError):self.bridge.management('issue',{'title':'Bad','context_id':'personal','account_id':'work@example.invalid','profile':'Work profile','operations':['browser.form']})
    def test_actual_probe_contract_uses_native_ax_and_current_refs(self):
        profile={'account_id':'owner@example.invalid','profile':'Personal','app':'Chrome','profile_marker':'Profile Personal','account_marker':'owner@example.invalid'}
        probe=module.ObservedBrowserProbe(NativeFixture(),profile);target={'pid':1,'window_id':2,'tab_id':'tab'}
        self.assertEqual(probe.identity(target)['account_id'],'owner@example.invalid')
        self.assertEqual(probe.field(target,'r1')['type'],'text')
        profile['account_marker']='someone-else@example.invalid'
        with self.assertRaises(PermissionError):probe.identity(target)
    def test_native_owner_gate_defaults_to_deny(self):
        untrusted=module.PermissionsBridge(self.service)
        with self.assertRaises(PermissionError):untrusted.management('issue',{'title':'Research','context_id':'personal','account_id':'public','profile':'public-unauthed','operations':['browser.read']})
    def test_public_selection_native_confirmation_then_origin_binding(self):
        grant=self.issue();inventory=self.bridge.management('browser_targets',{'grantId':grant['grant_id']})
        target=inventory['data'][0]['targetId']
        prepared=self.bridge.management('prepare-selection',{'sessionId':'owner1','grantId':grant['grant_id'],'targetId':target})
        selected=self.bridge.management('commit-selection',{'nonce':prepared['nonce']})
        self.assertEqual(selected['status'],'selected')
        with self.assertRaises(PermissionError):self.bridge.management('commit-selection',{'nonce':prepared['nonce']})
        with self.assertRaises(PermissionError):self.bridge.management('bind-selection',{'selectionId':target,'sessionId':'other','stageSessionId':'stage'})
        result=self.bridge.management('bind-selection',{'selectionId':target,'sessionId':'owner1','stageSessionId':'stage'})
        self.assertTrue(result['bound'])
        self.bridge.management('revoke',{'grant_id':grant['grant_id']})
        with self.assertRaises(PermissionError):self.bridge.management('bind-selection',{'selectionId':target,'sessionId':'owner1','stageSessionId':'next'})
    def test_renderer_target_and_expired_inventory_rejected(self):
        grant=self.issue()
        with self.assertRaises(PermissionError):self.bridge.management('prepare-selection',{'sessionId':'owner1','grantId':grant['grant_id'],'targetId':'fake-target'})
        target=self.bridge.management('browser_targets',{'grantId':grant['grant_id']})['data'][0]['targetId']
        self.store.connection.execute('UPDATE browser_native_selections SET expires_at=0')
        with self.assertRaises(PermissionError):self.bridge.management('prepare-selection',{'sessionId':'owner1','grantId':grant['grant_id'],'targetId':target})
    def test_selection_operations_unavailable_to_untrusted_runtime(self):
        bridge=module.PermissionsBridge(self.service)
        with self.assertRaises(PermissionError):bridge.management('browser_targets',{'grantId':self.issue()['grant_id']})
    def test_real_typed_contract_target_selection_and_identity_drift(self):
        class BrowserNative(NativeFixture):
            changed=False
            def _call(self,action,**kw):
                if action=='list_windows':return {'windows':[{'app_name':'Chrome','pid':10,'window_id':20,'title':'Selected owner window'}]}
                return super()._call(action,**kw)
            def state(self,**kw):
                value=super().state(**kw);value['exact_binding']=True
                value['tabs'][0]['title']='Owner form'
                if self.changed:value['tabs'][0]['url']='https://other.invalid/'
                return value
        p=self.root/'browser-profiles.json';p.write_text(json.dumps({'profiles':[{'id':'personal','label':'Personal','context_id':'personal','account_id':'owner@example.invalid','profile':'Personal','app':'Chrome','profile_marker':'Profile Personal','account_marker':'owner@example.invalid'}]}));p.chmod(0o600)
        self.bridge.native_factory=BrowserNative
        grant=self.bridge.management('issue',{'title':'Form','context_id':'personal','account_id':'owner@example.invalid','profile':'Personal','apps':['Chrome'],'operations':['browser.read']})
        inventory=self.bridge.management('browser_targets',{'grantId':grant['grant_id']});target=inventory['data'][0]['targetId']
        prepared=self.bridge.management('prepare-selection',{'sessionId':'owner1','grantId':grant['grant_id'],'targetId':target})
        selected=self.bridge.management('commit-selection',{'nonce':prepared['nonce']})
        self.assertEqual(selected['windowLabel'],'Selected owner window')
        BrowserNative.changed=True
        with self.assertRaises(PermissionError):self.bridge.management('bind-selection',{'selectionId':target,'sessionId':'owner1','stageSessionId':'stage1'})
    def test_native_adapter_binds_then_reads_selected_tab(self):
        adapter=module.NativeCUAAdapter(session_id='test');calls=[]
        def call(action,**args):
            calls.append(args)
            return {'tabs':[{'tab_id':'minted'}]} if 'pid' in args else {'refs':{'r1':{}}}
        adapter._call=call
        value=adapter.state(pid=1,window_id=2,tab_id='minted')
        self.assertEqual(calls,[{'pid':1,'window_id':2},{'tab_id':'minted'}]);self.assertIn('r1',value['refs'])
    def test_consent_required_window_needs_native_nonce_before_task_scoped_launch(self):
        from unittest.mock import patch
        class ConsentNative:
            title='Exact personal window'
            state_targets=[]
            def __init__(self,**kw):pass
            def _call(self,action,**kw):
                assert action=='list_windows'
                return {'windows':[{'app_name':'Google Chrome','pid':10,'window_id':20,'title':self.title},{'app_name':'Google Chrome','pid':10,'window_id':21,'title':'Unrelated window'},{'app_name':'Google Chrome','pid':11,'window_id':20,'title':'Other process'}]}
            def state(self,**kw):
                self.state_targets.append(kw)
                return {'status':'refused','refusal':{'code':'browser_consent_required'}}
        profile={'id':'personal','label':'Personal','context_id':'personal','account_id':'owner@example.invalid','profile':'Default','app':'Google Chrome','profile_marker':'Personal','account_marker':'owner@example.invalid'}
        p=self.root/'browser-profiles.json';p.write_text(json.dumps({'profiles':[profile]}));p.chmod(0o600)
        self.bridge.native_factory=ConsentNative
        grant=self.bridge.management('issue',{'title':'Synthetic task','context_id':'personal','account_id':profile['account_id'],'profile':'Default','apps':['Google Chrome'],'domains':['example.com'],'resources':['native:10:20'],'operations':['browser.read']})
        with patch('hermes_attention.scoped_browser.launch',return_value={'scopeId':'a'*32,'result':{'status':'ok'}}) as launch:
            targets=self.bridge.management('browser_targets',{'grantId':grant['grant_id']})
            self.assertEqual(ConsentNative.state_targets,[{'pid':10,'window_id':20}])
            self.assertEqual(len(targets['data']),1);self.assertIn('not inspected',targets['data'][0]['label']);launch.assert_not_called()
            request={'sessionId':'owner1','grantId':grant['grant_id'],'targetId':targets['data'][0]['targetId']}
            prepared=self.bridge.management('prepare-selection',request);self.assertIn('remote debugging',prepared['confirmationText']);self.assertIn('example.com',prepared['confirmationText']);launch.assert_not_called()
            ConsentNative.title='Different window'
            with self.assertRaises(PermissionError):self.bridge.management('commit-selection',{'nonce':prepared['nonce']})
            launch.assert_not_called();ConsentNative.title='Exact personal window'
            result=self.bridge.management('commit-selection',{'nonce':prepared['nonce']});self.assertEqual(result['status'],'setup-complete');self.assertFalse(result['bound']);self.assertEqual(launch.call_count,1)
            with self.assertRaises(PermissionError):self.bridge.management('commit-selection',{'nonce':prepared['nonce']})
            self.assertEqual(launch.call_count,1)
        with patch('hermes_attention.scoped_browser.stop_scopes',return_value=[]) as stop:
            self.bridge.management('stop',{'capability':'browser.read'});stop.assert_called_once_with(self.bridge.root)
if __name__=='__main__':unittest.main()
