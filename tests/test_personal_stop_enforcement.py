"""UI stop persistence must prevent intercepted provider requests, across both APIs."""
import base64
import json
import unittest
import test_personal_intents as fixtures
from hermes_attention.personal_permissions import Permissions

class StopEnforcementTests(unittest.TestCase):
    setUp=fixtures.IntentTests.setUp
    tearDown=fixtures.IntentTests.tearDown
    prepare=fixtures.IntentTests.prepare
    execute=fixtures.IntentTests.execute

    def permissions(self):return Permissions(self.store,authorize_owner=lambda *_:True)
    def event(self):return {'summary':'Fixture','start':{'dateTime':'2026-09-07T10:00:00+05:00'},'end':{'dateTime':'2026-09-07T11:00:00+05:00'}}
    def seed(self):
        self.actions.calendar.create_explicit(self.event())
        self.raw=base64.urlsafe_b64encode(b'Subject: Fixture\n\nBody').decode()
        self.actions.gmail.create(raw_base64url=self.raw)
        self.transport.calls.clear()

    def test_ui_all_stop_blocks_every_legacy_entry(self):
        self.seed();self.permissions().stop('all')
        for call in [lambda:self.actions.calendar.create_explicit(self.event()),lambda:self.actions.calendar.get_existing('owned1'),lambda:self.actions.calendar.update_created('owned1',{'summary':'New'}),lambda:self.actions.calendar.update_existing_personal('owned1',{'summary':'New'},expected_etag='v1'),lambda:self.actions.calendar.undo_created('owned1'),lambda:self.actions.gmail.create(raw_base64url=self.raw),lambda:self.actions.gmail.get_created('draft1'),lambda:self.actions.gmail.update_created('draft1',raw_base64url=self.raw)]:
            with self.assertRaisesRegex(PermissionError,'emergency stop'):call()
        self.assertEqual(self.transport.calls,[])

    def test_individual_stops_block_corresponding_legacy_operations(self):
        self.seed();p=self.permissions()
        for operation,call in [('calendar.create',lambda:self.actions.calendar.create_explicit(self.event())),('calendar.update',lambda:self.actions.calendar.update_existing_personal('owned1',{'summary':'New'},expected_etag='v1')),('calendar.undo',lambda:self.actions.calendar.undo_created('owned1')),('draft.create',lambda:self.actions.gmail.create(raw_base64url=self.raw)),('draft.read',lambda:self.actions.gmail.get_created('draft1')),('draft.update',lambda:self.actions.gmail.update_created('draft1',raw_base64url=self.raw))]:
            p.stop(operation)
            with self.assertRaisesRegex(PermissionError,'emergency stop'):call()
            p.stop(operation,False)
        self.assertEqual(self.transport.calls,[])

    def test_semantic_preclaim_stop_is_known_rejection_for_every_operation(self):
        self.seed();p=self.permissions()
        ref=lambda kind,id:{'id':id,'kind':kind,'account_id':self.account}
        cases=[({'operation':'calendar.create','summary':'New','start':'2026-09-07T10:00:00+05:00','end':'2026-09-07T11:00:00+05:00'},None),({'operation':'calendar.update','reference_id':'owned1','summary':'New'},[ref('calendar','owned1')]),({'operation':'calendar.undo','reference_id':'owned1'},[ref('calendar','owned1')]),({'operation':'draft.create','subject':'New','body':'Body'},None),({'operation':'draft.read','reference_id':'draft1'},[ref('draft','draft1')]),({'operation':'draft.update','reference_id':'draft1','subject':'New'},[ref('draft','draft1')])]
        for output,refs in cases:
            self.output=output;prepared=self.prepare(references=refs)
            self.transport.calls.clear();p.stop(output['operation'])
            with self.assertRaisesRegex(PermissionError,'emergency stop'):self.execute(prepared)
            self.assertEqual(self.transport.calls,[])
            row=self.store.connection.execute('SELECT status,result_json FROM personal_intent_preparations WHERE preparation_id=?',(prepared['preparation_id'],)).fetchone()
            self.assertEqual(row['status'],'rejected');self.assertIs(json.loads(row['result_json'])['external_write'],False)
            p.stop(output['operation'],False)

    def test_update_stop_preserves_read_and_snapshot_undo(self):
        ref={'id':'owned1','kind':'calendar','account_id':self.account}
        self.output={'operation':'calendar.update','reference_id':'owned1','summary':'Changed'}
        result=self.execute(self.prepare(references=[ref]));ref['change_id']=result['change_id']
        self.permissions().stop('calendar.update');self.permissions().stop('calendar.create')
        self.actions.calendar.get_existing('owned1')
        self.output={'operation':'calendar.undo','reference_id':'owned1'}
        self.execute(self.prepare(references=[ref]));self.assertEqual(self.transport.event['summary'],'Walk')

    def test_existing_firewall_revocation_still_denies_after_stop_resume(self):
        self.output={'operation':'calendar.create','summary':'New','start':'2026-09-07T10:00:00+05:00','end':'2026-09-07T11:00:00+05:00'}
        prepared=self.prepare();p=self.permissions();p.stop('all');p.stop('all',False)
        self.firewall.set_capability_kill_switch('calendar',True)
        with self.assertRaises(PermissionError):self.execute(prepared)
        self.assertEqual(self.transport.calls,[])
