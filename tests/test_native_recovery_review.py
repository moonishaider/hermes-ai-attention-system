"""Independent persisted-outcome holdouts; no provider clients or real state."""
import importlib.util,json,sqlite3,tempfile,unittest
from pathlib import Path
from hermes_attention.conversation_turns import transition
spec=importlib.util.spec_from_file_location('turn_recovery',Path(__file__).resolve().parents[1]/'scripts/jarvis_turn_recovery.py')
recovery=importlib.util.module_from_spec(spec);spec.loader.exec_module(recovery)
class RecoveryHoldouts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.path=self.root/'attention.db'
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE native_personal_turns(session_id TEXT,turn_id TEXT,nonce_hash TEXT,state TEXT,preparation_id TEXT,result_json TEXT)')
            db.execute('CREATE TABLE native_cancelled_turns(session_id TEXT,turn_id TEXT)')
        self.request={'sessionId':'jarvis_owner','turnId':'turn1'}
    def seed(self,state,cancel=False):
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT INTO native_personal_turns VALUES(?,?,?,?,?,?)',('jarvis_owner','turn1','hash',state,'prep1',json.dumps({'status':state,'resource':'owned-test-event'})))
            if cancel:db.execute('INSERT INTO native_cancelled_turns VALUES(?,?)',('jarvis_owner','turn1'))
    def recover(self):return recovery.reconcile(self.request,database=self.path,session_validator=lambda sid:None)
    def test_crash_after_claim_is_unresolved_even_if_cancelled(self):
        self.seed('executing',cancel=True);before=self.path.read_bytes();result=self.recover()
        self.assertEqual(result['status'],'unresolved');self.assertFalse(result['action_repeated']);self.assertEqual(before,self.path.read_bytes())
    def test_completed_provider_receipt_survives_late_cancel(self):
        self.seed('completed',cancel=True);result=self.recover()
        self.assertEqual(result['status'],'completed');self.assertEqual(result['result']['resource'],'owned-test-event')
    def test_prepared_preview_remains_owner_reviewable(self):
        self.seed('prepared');self.assertEqual(self.recover()['status'],'waiting_action')
    def test_read_does_not_create_missing_database(self):
        absent=self.root/'absent.db';result=recovery.reconcile(self.request,database=absent,session_validator=lambda sid:None)
        self.assertEqual(result['status'],'none');self.assertFalse(absent.exists())
    def test_foreign_session_never_reads_receipt(self):
        self.seed('completed')
        with self.assertRaises(PermissionError):recovery.reconcile({**self.request,'sessionId':'slack_foreign'},database=self.path,session_validator=lambda sid:None)
    def test_canonical_terminal_is_authority_for_conflicting_replay(self):
        class Database:
            def __init__(self):self.rows=[]
            def get_session(self,sid):return {'source':'desktop'}
            def get_messages(self,sid):return self.rows
            def append_messages_batch(self,sid,rows):self.rows.extend(rows)
            def close(self):pass
        db=Database();request={**self.request,'context':'personal','ownerRequest':'Owner task'}
        transition(lambda:db,self.root,request,finish=False)
        transition(lambda:db,self.root,{**request,'status':'interrupted','assistantMessage':'Outcome unknown'},finish=True)
        result=transition(lambda:db,self.root,{**request,'status':'completed','assistantMessage':'Late response'},finish=True)
        self.assertEqual(result['status'],'interrupted');self.assertEqual(result['assistantMessage'],'Outcome unknown');self.assertTrue(result['terminalConflict']);self.assertEqual(len(db.rows),2)
if __name__=='__main__':unittest.main()
