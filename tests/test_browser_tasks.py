import tempfile
from pathlib import Path
from datetime import datetime,UTC,timedelta
import unittest
from unittest.mock import patch
from hermes_attention.storage import Store
from hermes_attention.personal_permissions import Permissions
from hermes_attention.browser_tasks import BrowserTasks,PublicFetcher,public_url

def resolver(host,port,**kwargs):return [(2,1,6,'',('93.184.216.34' if host!='private.invalid' else '127.0.0.1',443))]
class Response:
    def __init__(self,status,body=b'',headers=None):self.status=status;self.body=body;self.headers=headers or {}
    def read(self,n):return self.body[:n]
    def getheader(self,k):return self.headers.get(k)
class Connection:
    responses=[];requests=[]
    def __init__(self,host,ip):self.host=host;self.ip=ip
    def request(self,method,path,headers):self.requests.append((self.host,self.ip,method,path,headers))
    def getresponse(self):return self.responses.pop(0)
    def close(self):pass
class Native:
    def __init__(self):self.calls=[]
    def state(self,**args):return {'data':{'snapshot':'Synthetic form'}}
    def navigate(self,**args):self.calls.append(('navigate',args));return {'success':True}
    def type_field(self,**args):self.calls.append(('type',args));return {'success':True}
    def protected_network(self,target):return False
class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:');self.tmp=tempfile.TemporaryDirectory();self.now=datetime(2026,9,5,tzinfo=UTC)
        self.owner_calls=[]
        def owner(op,value):self.owner_calls.append(op);return True
        self.permissions=Permissions(self.store,authorize_owner=owner,clock=lambda:self.now)
        self.native=Native();self.identity={'account_id':'owner','profile':'Profile 1','app':'chrome','url':'https://example.invalid/form'}
        self.fetcher=PublicFetcher(resolver=resolver,connection_factory=Connection);Connection.requests=[];Connection.responses=[]
        self.browser=BrowserTasks(self.permissions,download_root=Path(self.tmp.name).resolve(),fetcher=self.fetcher,native=self.native,identity_probe=lambda target:self.identity,field_probe=lambda target,ref:{'role':'textbox','type':'text','label':'Name','url':self.identity['url']})
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def grant(self,operations,public=False,context='personal'):
        return self.permissions.issue(title='Synthetic browser task',context_id=context,account_id='public' if public else 'owner',profile='public-unauthed' if public else 'Profile 1',operations=operations,apps=['chrome'],resources=[])
    def test_public_dns_redirect_guard_and_pinned_path(self):
        Connection.responses=[Response(302,headers={'Location':'https://private.invalid/secret'})]
        with self.assertRaises(PermissionError):self.browser.research(self.grant(['browser.read'],True)['grant_id'],'https://example.invalid/search?q=one')
        self.assertEqual(len(Connection.requests),1);self.assertEqual(Connection.requests[0][1],'93.184.216.34');self.assertEqual(Connection.requests[0][3],'/search?q=one')
    def test_download_output_hash_and_no_execution(self):
        Connection.responses=[Response(200,b'a,b\n1,2\n',{'Content-Type':'text/csv'})]
        result=self.browser.download(self.grant(['browser.download'],True)['grant_id'],'https://example.invalid/report','report.csv')
        self.assertEqual(Path(result['path']).read_bytes(),b'a,b\n1,2\n');self.assertFalse(result['opened_or_executed'])
    def test_task_bound_native_flow_has_no_per_keystroke_owner_prompt(self):
        grant=self.grant(['browser.navigate','browser.form','browser.read']);target={'pid':42,'window_id':7,'tab_id':'opaque'}
        with patch('hermes_attention.browser_tasks.public_url',lambda url:('example.invalid',['93.184.216.34'])):
            result=self.browser.navigate(grant['grant_id'],target,'https://example.invalid/form')
            self.browser.prepare_field(grant['grant_id'],target,ref='field1',text='Synthetic name')
            self.browser.prepare_field(grant['grant_id'],target,ref='field2',text='Synthetic city')
        self.assertEqual(self.owner_calls,['grant']);self.assertEqual(len(self.native.calls),3);self.assertFalse(result['browser_network_containment_verified'])
    def test_company_write_account_swap_revocation_and_independent_stop(self):
        with self.assertRaises(PermissionError):self.grant(['browser.form'],context='inside-success')
        grant=self.grant(['browser.read','browser.form']);self.permissions.stop('browser.form')
        self.browser.native_read(grant['grant_id'],{'pid':42,'window_id':7})
        self.identity['profile']='Other profile'
        with self.assertRaises(PermissionError):self.browser.native_read(grant['grant_id'],{'pid':42,'window_id':7})
        self.permissions.revoke(grant['grant_id'])
        with self.assertRaises(PermissionError):self.browser.native_read(grant['grant_id'],{'pid':42,'window_id':7})
    def test_sensitive_destinations_and_fields_block(self):
        for url in ['file:///etc/passwd','http://example.invalid','https://private.invalid','https://example.invalid/?token=anything','https://user:pass@example.invalid']:
            with self.assertRaises(PermissionError):public_url(url,resolver)
        grant=self.grant(['browser.form']);self.browser.field_probe=lambda target,ref:{'role':'textbox','type':'password','url':'https://example.invalid'}
        with self.assertRaises(PermissionError):self.browser.prepare_field(grant['grant_id'],{'pid':42,'window_id':7,'tab_id':'opaque'},ref='password',text='secret')
        self.assertEqual(self.native.calls,[])
if __name__=='__main__':unittest.main()


class NativeWindowInventoryTest(unittest.TestCase):
    def test_inventory_retains_other_spaces_without_generic_actions(self):
        import sys
        from unittest.mock import Mock
        sys.path.append(str(Path.home()/'.hermes/hermes-agent'))
        from hermes_attention.browser_tasks import NativeCUAAdapter
        backend=Mock();backend._session_id='resolved-driver-session';backend._call_capture_tool.return_value={'data':{'windows':[
            {'pid':10,'window_id':20,'app_name':'Google Chrome','title':'Personal task','is_on_screen':False,'z_index':1},
            {'pid':10,'window_id':21,'app_name':'Google Chrome','title':'Current Space','is_on_screen':True,'z_index':2},
            {'pid':None,'window_id':5}]}}
        with patch('tools.computer_use.tool._get_backend',return_value=backend),patch('tools.computer_use.tool.handle_computer_use') as generic:
            result=NativeCUAAdapter(session_id='exact-inventory')._call('list_windows')
        backend._call_capture_tool.assert_called_once_with('list_windows',{'on_screen_only':False,'session':'resolved-driver-session'})
        generic.assert_not_called();self.assertEqual([w['window_id'] for w in result['windows']],[21,20]);self.assertTrue(result['windows'][1]['off_screen'])
    def test_inventory_error_never_falls_back_or_accepts_authority(self):
        import sys
        from unittest.mock import Mock
        sys.path.append(str(Path.home()/'.hermes/hermes-agent'))
        from hermes_attention.browser_tasks import NativeCUAAdapter
        backend=Mock();backend._session_id='resolved-error-session';backend._call_capture_tool.return_value={'isError':True,'data':'refused'}
        adapter=NativeCUAAdapter(session_id='exact-inventory-error')
        with patch('tools.computer_use.tool._get_backend',return_value=backend),patch('tools.computer_use.tool.handle_computer_use') as generic:
            with self.assertRaises(RuntimeError):adapter._call('list_windows')
            with self.assertRaises(PermissionError):adapter._call('list_windows',on_screen_only=True)
        generic.assert_not_called();self.assertEqual(backend._call_capture_tool.call_count,1)
