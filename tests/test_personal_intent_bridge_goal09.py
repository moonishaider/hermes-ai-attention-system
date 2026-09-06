import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from hermes_attention.storage import Store
from hermes_attention.documents import DocumentWorkspace
from hermes_attention.action_firewall import ActionFirewall
from hermes_attention.personal_intents import SemanticPersonalActions
from hermes_attention.personal_google_actions import PersonalCalendarActions,PersonalGmailDraftActions

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import jarvis_personal_intent as bridge


class IntentBridgeTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(':memory:');self.addCleanup(self.store.close)
        root=Path(self.temp.name).resolve()
        self.docs=DocumentWorkspace(root/'documents')
        self.service=SimpleNamespace(store=self.store,paths=SimpleNamespace(runtime_dir=root))
        self.mode='auto-explicit';self.enabled=True;self.calls=[];self.model_calls=[]
        self.output={'operation':'calendar.create','summary':'Synthetic reading','start':'2026-09-10T10:00:00+05:00','end':'2026-09-10T10:30:00+05:00'}
        self.firewall=ActionFirewall(self.store,b's'*32,global_kill_switch=False)
        for family,cap,target in [('calendar',bridge.local.CALENDAR_CAPABILITY,{'account':bridge.local.PERSONAL_ACCOUNT,'calendar_id':'primary'}),('draft',bridge.local.GMAIL_CAPABILITY,{'account':bridge.local.PERSONAL_ACCOUNT,'resource':'draft'})]:
            self.firewall.register_capability(capability_id=cap,context_id='personal',account_id=bridge.local.PERSONAL_ACCOUNT,target_lock=target,permission_inventory=bridge._inventory(family),enabled=True)
            self.firewall.set_capability_kill_switch(cap,False)
        self.patches=[patch.object(bridge.local,'_personal_action_mode',side_effect=lambda service:self.mode),patch.object(bridge.local,'_personal_actions_enabled',side_effect=lambda service:self.enabled),patch.object(bridge.local,'PersonalGoogleActionTokenManager',return_value=SimpleNamespace(status=lambda:{'connected':True}))]
        for p in self.patches:p.start();self.addCleanup(p.stop)
    def transport(self,method,url,body,params,**kwargs):
        self.calls.append((method,url,body))
        if method=='POST':return {'id':'synthetic-resource','htmlLink':'https://example.invalid/resource',**body}
        raise AssertionError('Unexpected provider call')
    def factory(self,service,session):
        def model(payload):self.model_calls.append(payload);return copy.deepcopy(self.output)
        def load(identity):
            record=self.docs.get(identity,session)
            return {'content':self.docs.path(identity,session).read_bytes(),'filename':record['display_name'],'mime_type':record['mime']}
        engine=SemanticPersonalActions(self.store,model=model,calendar=PersonalCalendarActions(self.store,self.transport,calendar_id='primary',capability_id=bridge.local.CALENDAR_CAPABILITY),gmail=PersonalGmailDraftActions(self.store,self.transport,capability_id=bridge.local.GMAIL_CAPABILITY),firewall=self.firewall,account_id=bridge.local.PERSONAL_ACCOUNT,capability_ids={'calendar':bridge.local.CALENDAR_CAPABILITY,'draft':bridge.local.GMAIL_CAPABILITY},permission_inventory=bridge._inventory,attachment_loader=load)
        return engine,self.mode,self.enabled,self.docs
    def call(self,**overrides):
        request={'operation':'prepare','sessionId':'jarvis_fixture','turnId':'turn1','ownerRequest':'Tomorrow at ten, pencil in half an hour for reading.','nativeNonce':'native-fixture-nonce-1234',**overrides}
        return bridge.handle(request,service=self.service,session_validator=lambda session: {'id':session} if session=='jarvis_fixture' else (_ for _ in ()).throw(PermissionError('not Jarvis owner')),engine_factory=self.factory,calendar_conflicts=lambda a,b:[])

    def test_undone_change_does_not_hide_creation_cleanup(self):
        import json
        bridge.ensure_schema(self.store.connection)
        self.factory(self.service,'session')
        self.store.connection.execute("INSERT INTO personal_event_changes VALUES(?,?,?,?,?,?)",('change','event','{}','{}','undone','2026-09-06'))
        resource={'result':{'provider_id':'event','resource_kind':'calendar-event','change_id':'change'},'preview':{'event':{'summary':'Fixture'}}}
        # Exercise the actual native receipt reader without a provider call.
        with patch.object(bridge,'json',json):
            class Rows:
                def execute(inner,sql,args):
                    if 'native_personal_turns' in sql:return type('Result',(),{'fetchall':lambda inner:[{'result_json':json.dumps(resource)}]})()
                    return self.store.connection.execute(sql,args)
            refs=bridge._references(Rows(),'session')
        self.assertIsNone(refs[0]['change_id']);self.assertEqual(refs[0]['id'],'event')

    def test_auto_explicit_one_actual_intercepted_transport_and_replay(self):
        result=self.call();self.assertEqual(result['status'],'completed');self.assertEqual(len(self.calls),1)
        again=self.call();self.assertTrue(again['replayed_receipt']);self.assertEqual(len(self.calls),1);self.assertEqual(len(self.model_calls),1)
        self.assertEqual(self.model_calls[0]['owner_request'],'Tomorrow at ten, pencil in half an hour for reading.')
        with self.assertRaises(PermissionError):self.call(ownerRequest='Different task')
        with self.assertRaises(PermissionError):self.call(nativeNonce='different-native-nonce')

    def test_preview_requires_exact_native_confirmation_and_binding(self):
        self.mode='preview';result=self.call();self.assertEqual(result['status'],'prepared');self.assertEqual(self.calls,[])
        with self.assertRaises(PermissionError):self.call(operation='execute',preparationId=result['preparationId'],confirmed=False)
        with self.assertRaises(PermissionError):self.call(operation='execute',preparationId='invented',confirmed=True)
        done=self.call(operation='execute',preparationId=result['preparationId'],confirmed=True)
        self.assertEqual(done['status'],'completed');self.assertEqual(len(self.calls),1)

    def test_none_and_source_cannot_mint_native_authority(self):
        self.output={'operation':'none'};result=self.call(ownerRequest='What does a calendar event mean?')
        self.assertEqual(result['status'],'none');self.assertFalse(self.calls)
        with self.assertRaises(ValueError):self.call(owner_token='invented')
        with self.assertRaises(PermissionError):self.call(sessionId='foreign')

    def test_revoked_standing_grant_before_execute(self):
        self.mode='preview';prepared=self.call();self.enabled=False
        with self.assertRaises(PermissionError):self.call(operation='execute',preparationId=prepared['preparationId'],confirmed=True)
        self.assertEqual(self.calls,[])

    def test_attachment_forgotten_after_preview_blocks_sendless_draft(self):
        self.mode='preview'
        record=self.docs.ingest_bytes(b'Value\n10\n',name='selected.csv',conversation_id='jarvis_fixture')
        self.output={'operation':'draft.create','subject':'Synthetic draft','body':'Selected table','attachment_ids':[record['id']]}
        prepared=self.call();self.assertEqual(prepared['status'],'prepared')
        self.docs.forget(record['id'],'jarvis_fixture')
        result=self.call(operation='execute',preparationId=prepared['preparationId'],confirmed=True)
        self.assertEqual(result['status'],'rejected');self.assertEqual(self.calls,[])

    def test_uncertain_transport_is_never_replayed(self):
        def broken(*args,**kwargs):self.calls.append('attempt');raise TimeoutError('fixture timeout')
        self.transport=broken
        result=self.call();self.assertEqual(result['status'],'uncertain')
        replay=self.call();self.assertEqual(replay['status'],'uncertain');self.assertEqual(self.calls,['attempt'])

    def test_interrupted_executing_turn_replays_uncertain_and_cancellation_before_claim(self):
        self.mode='preview';prepared=self.call()
        with self.store.connection:self.store.connection.execute("UPDATE native_personal_turns SET state='executing' WHERE turn_id='turn1'")
        self.assertEqual(self.call()['status'],'uncertain')
        self.assertEqual(self.call(operation='execute',preparationId=prepared['preparationId'],confirmed=True)['status'],'uncertain');self.assertEqual(self.calls,[])
        with self.store.connection:
            self.store.connection.execute("UPDATE native_personal_turns SET state='prepared' WHERE turn_id='turn1'")
            self.store.connection.execute("INSERT INTO native_cancelled_turns VALUES('jarvis_fixture','turn1')")
        engine,_,_,_=self.factory(self.service,'jarvis_fixture')
        self.assertEqual(bridge._execute(self.service,engine,'jarvis_fixture','turn1','native-fixture-nonce-1234',prepared,explicit_confirmation=True)['status'],'cancelled');self.assertEqual(self.calls,[])

    def test_cancel_after_claim_and_completion_reports_actual_outcome(self):
        self.mode='preview';prepared=self.call()
        with self.store.connection:self.store.connection.execute("UPDATE native_personal_turns SET state='executing' WHERE turn_id='turn1'")
        self.assertEqual(self.call(operation='cancel')['status'],'uncertain')
        self.assertEqual(self.call()['status'],'uncertain')
        completed={'status':'completed','result':{'provider_id':'synthetic-id'}}
        import json
        with self.store.connection:self.store.connection.execute("UPDATE native_personal_turns SET state='completed',result_json=? WHERE turn_id='turn1'",(json.dumps(completed),))
        self.assertEqual(self.call(operation='cancel')['status'],'completed')
        self.assertEqual(self.call()['status'],'completed');self.assertEqual(self.calls,[])

    def test_cancel_before_model_or_during_preparation_never_dispatches(self):
        self.call(operation='cancel')
        self.assertEqual(self.call()['status'],'cancelled');self.assertEqual(self.calls,[])
        self.assertEqual(self.model_calls,[])
        original=self.factory
        def factory(service,session):
            engine,mode,enabled,docs=original(service,session)
            def cancelled_model(payload):
                self.call(operation='cancel',turnId='turn2')
                return copy.deepcopy(self.output)
            engine.model=cancelled_model
            return engine,mode,enabled,docs
        self.factory=factory
        self.assertEqual(self.call(turnId='turn2')['status'],'cancelled')
        self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
