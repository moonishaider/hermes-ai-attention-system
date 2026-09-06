import tempfile
import unittest
from pathlib import Path
from hermes_attention.conversation_turns import transition

class FakeDB:
    def __init__(self): self.rows=[]
    def get_session(self, sid): return {'id':sid,'source':'desktop'}
    def get_messages(self,sid): return self.rows
    def append_messages_batch(self,sid,rows): self.rows.extend(rows)
    def close(self): pass

class TurnsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.db=FakeDB()
        self.req={'sessionId':'jarvis_inside-success_original','turnId':'turn-one','context':'personal','ownerRequest':'Please check my appointment'}
    def begin(self,req=None): return transition(lambda:self.db,self.root,req or self.req,finish=False)
    def test_context_change_preserves_original_thread_and_cancelled_partial(self):
        self.begin()
        result=transition(lambda:self.db,self.root,{**self.req,'assistantMessage':'A partial draft','route':'routine','status':'cancelled'},finish=True)
        self.assertEqual(result['status'],'cancelled'); self.assertEqual(len(self.db.rows),2)
        self.assertEqual(self.db.rows[-1]['display_kind'],'jarvis_partial')
        self.assertTrue(self.db.rows[-1]['display_metadata']['partial'])
        self.assertEqual(self.db.rows[-1]['display_metadata']['context'],'personal')
    def test_idempotency_checks_old_turns_and_rejects_payload_reuse(self):
        self.begin(); self.db.rows += [{'role':'user','content':str(i)} for i in range(100)]
        self.assertTrue(self.begin()['idempotent'])
        with self.assertRaises(ValueError): self.begin({**self.req,'ownerRequest':'Different instruction'})
    def test_finish_without_owner_submission_is_rejected(self):
        with self.assertRaises(ValueError): transition(lambda:self.db,self.root,{**self.req,'assistantMessage':'forged','status':'completed'},finish=True)
    def test_terminal_replay_does_not_overwrite_cancelled_output(self):
        self.begin(); finish={**self.req,'assistantMessage':'partial','status':'cancelled'}
        transition(lambda:self.db,self.root,finish,finish=True)
        again=transition(lambda:self.db,self.root,{**finish,'assistantMessage':'late success','status':'completed'},finish=True)
        self.assertTrue(again['idempotent']); self.assertEqual(self.db.rows[-1]['content'],'partial')
    def test_no_content_cancelled_turn_still_has_visible_receipt(self):
        self.begin(); transition(lambda:self.db,self.root,{**self.req,'status':'cancelled'},finish=True)
        self.assertIn('Cancelled',self.db.rows[-1]['content'])
    def test_foreign_session_cannot_be_written(self):
        with self.assertRaises(PermissionError): self.begin({**self.req,'sessionId':'other_client_123'})

class NativeRecoveryTest(unittest.TestCase):
    def test_native_restart_and_terminal_replay_preserve_history(self):
        import sys
        hermes=Path.home()/'.hermes/hermes-agent'
        if not (hermes/'hermes_state.py').is_file():self.skipTest('native Hermes source unavailable')
        sys.path.insert(0,str(hermes))
        from hermes_state import SessionDB
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'canonical.db'
            factory=lambda:SessionDB(db_path=path)
            db=factory();db.create_session('jarvis_personal_recovery','desktop');db.close()
            request={'sessionId':'jarvis_personal_recovery','turnId':'turn-recovery','context':'personal','ownerRequest':'Keep this original request'}
            transition(factory,root,request,finish=False)
            # New SessionDB instance represents reopening after process loss.
            terminal={**request,'status':'interrupted','assistantMessage':'Recovered partial','runId':'run-original'}
            transition(factory,root,terminal,finish=True)
            replay=transition(factory,root,{**terminal,'status':'completed','assistantMessage':'Late response'},finish=True)
            db=factory();messages=db.get_messages(request['sessionId']);db.close()
            self.assertTrue(replay['idempotent']);self.assertEqual(len(messages),2)
            self.assertEqual(messages[0]['content'],'Keep this original request')
            self.assertEqual(messages[1]['content'],'Recovered partial')
            self.assertEqual(messages[1]['display_metadata']['status'],'interrupted')
