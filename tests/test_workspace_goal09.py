import unittest
from tempfile import TemporaryDirectory
from hermes_attention.storage import Store
from hermes_attention.workspace import Workspace

class Native:
    def pending(self):return []
    def confirmed(self):return {'memory':[],'user':[]}
class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.store=Store(':memory:')
        self.workspace=Workspace(self.store,self.temp.name,native=Native(),owner=True)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def test_owner_boundary_is_not_a_request_flag(self):
        workspace=Workspace(self.store,self.temp.name,native=Native())
        with self.assertRaises(PermissionError):workspace.dispatch('learning.snapshot',{'owner':True})
    def test_workflow_roundtrip(self):
        spec={'name':'Prepare review','kind':'workflow','context_id':'personal','tools':['list_tasks','save_output'],'steps':[{'id':'gather','tool':'list_tasks'},{'id':'save','tool':'save_output','args':{'title':'Review','content':{'from_step':'gather'}}}]}
        result=self.workspace.dispatch('capabilities.create',{'spec':spec});cid=result['capability_id']
        self.assertEqual(self.workspace.dispatch('capabilities.list',{})['data'][0]['spec'],spec)
        with self.assertRaises(ValueError):self.workspace.dispatch('capabilities.activate',{'capabilityId':cid})
        dry=self.workspace.dispatch('capabilities.run',{'capabilityId':cid,'mode':'dry','fixtures':{'gather':[]}})
        self.assertEqual(dry['status'],'completed')
        self.workspace.dispatch('capabilities.activate',{'capabilityId':cid})
        live=self.workspace.dispatch('capabilities.run',{'capabilityId':cid,'mode':'active','runId':'test-owner'})
        artifact=live['outputs']['save']['artifact_id']
        self.assertEqual(self.workspace.dispatch('capabilities.output',{'artifactId':artifact})['title'],'Review')
    def test_invalid_operation_and_context(self):
        with self.assertRaises(ValueError):self.workspace.dispatch('shell',{'cmd':'anything'})
        with self.assertRaises(ValueError):self.workspace.dispatch('capabilities.create',{'spec':{'context_id':'new-ungiven'}})
    def test_memory_snapshot_uses_native_store(self):
        self.assertFalse(self.workspace.dispatch('learning.snapshot',{})['automatic_pending_approval'])
if __name__=='__main__':unittest.main()
