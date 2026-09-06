import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from hermes_attention.storage import Store
from hermes_attention.domain import ContextLabel
from hermes_attention.context_sync import ContextSync
class SyncTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name);self.store=Store(':memory:');router=SimpleNamespace(classify=lambda *a,**k:(ContextLabel('unknown',0.5,'uploaded fixture','v1'),));self.service=SimpleNamespace(store=self.store,router=router,refresh_work_ledger=lambda **_:None);self.sync=ContextSync(self.service)
 def tearDown(self):self.store.close();self.tmp.cleanup()
 def export(self):
  (self.folder/'conversations.json').write_text(json.dumps([{'id':'synthetic-conversation','title':'Synthetic review','create_time':1788600000,'mapping':{'m':{'message':{'author':{'role':'user'},'content':{'parts':['Review my synthetic test task.']}}}}}]))
 def test_explicit_folder_then_enable_and_idempotent_actual_import(self):
  self.export()
  with self.assertRaises(PermissionError):self.sync.register(self.folder,'chatgpt','2026-01-01')
  identity=self.sync.register(self.folder,'chatgpt','2026-01-01',owner_authorized=True)['folderId']
  self.assertEqual(self.sync.scan()['data'],[]);self.sync.enable(identity,True)
  first=self.sync.scan(identity,force=True);self.assertEqual(first['data'][0]['status'],'updated')
  self.assertEqual(self.store.connection.execute('SELECT count(*) FROM evidence').fetchone()[0],1)
  self.assertEqual(self.sync.scan(identity,force=True)['data'][0]['status'],'no-change')
  provenance=json.loads(self.store.connection.execute('SELECT provenance_json FROM evidence').fetchone()[0]);self.assertEqual(provenance['source_system'],'chatgpt_export');self.assertEqual(provenance['account_id'],'user-export')
 def test_oversized_export_is_partial_not_successful_no_change(self):
  path=self.folder/'large.json'
  with path.open('wb') as handle:handle.truncate(65*1024*1024)
  identity=self.sync.register(self.folder,'chatgpt','2026-01-01',owner_authorized=True)['folderId'];self.sync.enable(identity,True)
  result=self.sync.scan(identity,force=True)['data'][0]
  self.assertEqual(result['status'],'partial');self.assertEqual(result['files'][0]['status'],'skipped-size-limit')
 def test_failure_is_not_no_change_and_no_symlink_escape(self):
  (self.folder/'invalid.json').write_text('invalid');identity=self.sync.register(self.folder,'chatgpt','2026-01-01',owner_authorized=True)['folderId'];self.sync.enable(identity,True)
  self.assertEqual(self.sync.scan(identity,force=True)['data'][0]['status'],'failed')
  (self.folder/'invalid.json').unlink();(self.folder/'outside.json').symlink_to('/etc/passwd')
  self.assertEqual(self.sync.scan(identity,force=True)['data'][0]['status'],'failed');self.assertEqual(self.store.connection.execute('SELECT count(*) FROM evidence').fetchone()[0],0)
