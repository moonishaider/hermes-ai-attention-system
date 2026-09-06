"""Typed intent execution tests; model and provider are explicitly intercepted."""
import base64
import copy
from datetime import datetime,UTC
from email import policy
from email.parser import BytesParser
import unittest
from hermes_attention.storage import Store
from hermes_attention.action_firewall import ActionFirewall
from hermes_attention.personal_google_actions import PersonalCalendarActions,PersonalGmailDraftActions,PersonalGoogleActionTransport
from hermes_attention.personal_intents import SemanticPersonalActions

class ProviderFixture:
    def __init__(self):
        self.calls=[];self.event={'id':'owned1','summary':'Walk','etag':'v1','organizer':{'self':True},'start':{'dateTime':'2026-09-06T08:00:00+05:00'},'end':{'dateTime':'2026-09-06T09:00:00+05:00'}};self.drafts={}
    def __call__(self,method,url,body,params,**headers):
        self.calls.append((method,url,body,params,headers))
        if '/drafts' in url:
            if method=='POST':self.drafts['draft1']={'id':'draft1','message':body['message']};return self.drafts['draft1']
            if method=='GET':return copy.deepcopy(self.drafts['draft1'])
            if method=='PUT':self.drafts['draft1']=body;return body
        if method=='GET':return copy.deepcopy(self.event)
        if method=='PATCH':
            if headers.get('if_match')!=self.event['etag']:raise RuntimeError('412 etag mismatch')
            self.event.update(body);self.event['etag']='v'+str(int(self.event['etag'][1:])+1);return copy.deepcopy(self.event)
        if method=='POST':self.event.update(body);return copy.deepcopy(self.event)
        if method=='DELETE':return {}
        raise AssertionError('unexpected provider request')

class IntentTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:');self.transport=ProviderFixture();self.output={};self.model_calls=[];self.account='owner@example.invalid';self.inventory={'calendar':{'events':'owned'},'draft':{'drafts':'only'}}
        def model(request):self.model_calls.append(request);return copy.deepcopy(self.output)
        self.firewall=ActionFirewall(self.store,b'a'*32,global_kill_switch=False)
        for family,target in [('calendar',{'account':self.account,'calendar_id':'primary'}),('draft',{'account':self.account,'resource':'draft'})]:
            self.firewall.register_capability(capability_id=family,context_id='personal',account_id=self.account,target_lock=target,permission_inventory=self.inventory[family],enabled=True)
            self.firewall.set_capability_kill_switch(family,False)
        self.files={'file1':{'filename':'synthetic.csv','content':b'value\n3\n','mime_type':'text/csv'}}
        self.actions=SemanticPersonalActions(self.store,model=model,calendar=PersonalCalendarActions(self.store,self.transport,calendar_id='primary',capability_id='calendar'),gmail=PersonalGmailDraftActions(self.store,self.transport,capability_id='draft'),firewall=self.firewall,account_id=self.account,capability_ids={'calendar':'calendar','draft':'draft'},permission_inventory=lambda family:self.inventory[family],attachment_loader=lambda aid:self.files[aid])
    def tearDown(self):self.store.close()
    def prepare(self,text='Please do this',references=None,attachment_ids=None):return self.actions.prepare(text,timezone='Asia/Karachi',now=datetime.now(UTC).isoformat(),references=references,attachment_ids=attachment_ids)
    def execute(self,p):
        token=self.firewall.issue_owner_intent(session_nonce='fixture',action_type=p['action_type'],request_text=p['request_binding'],trusted_local_interaction=True)
        return self.actions.execute(p['preparation_id'],owner_token=token,session_nonce='fixture')
    def test_provider_time_mismatch_is_uncertain_not_success(self):
        original=self.transport
        def transport(method,*args,**kwargs):
            result=original(method,*args,**kwargs)
            if method=='PATCH':result['start']={'dateTime':'2026-09-06T00:00:00+05:00'}
            return result
        self.actions.calendar.transport=transport
        self.output={'operation':'calendar.update','reference_id':'owned1','shift_minutes':30}
        prepared=self.prepare(references=[{'id':'owned1','kind':'calendar','account_id':self.account}])
        with self.assertRaises(RuntimeError):self.execute(prepared)
        status=self.store.connection.execute('SELECT status FROM personal_intent_preparations WHERE preparation_id=?',(prepared['preparation_id'],)).fetchone()[0]
        self.assertEqual(status,'uncertain')

    def test_model_optional_undo_change_must_match_selected_current_change(self):
        ref={'id':'owned1','kind':'calendar','account_id':self.account,'change_id':'current-change'}
        self.output={'operation':'calendar.undo','reference_id':'owned1','change_id':'current-change'}
        prepared=self.prepare(references=[ref]);self.assertEqual(prepared['preview']['change_id'],'current-change')
        self.output['change_id']='different-change'
        with self.assertRaisesRegex(PermissionError,'differs'):self.prepare(references=[ref])
        self.assertTrue(all(c[0]=='GET' for c in self.transport.calls))

    def test_invalid_schema_diagnostic_includes_only_key_names(self):
        self.output={'operation':'calendar.undo','secret_field':'private value must not leak'}
        with self.assertRaises(ValueError) as raised:self.prepare()
        self.assertIn('secret_field',str(raised.exception));self.assertNotIn('private value',str(raised.exception))

    def test_relative_move_uses_fresh_provider_times_and_preserves_duration(self):
        self.transport.event.update(start={'dateTime':'2026-09-07T15:00:00+05:00'},end={'dateTime':'2026-09-07T15:30:00+05:00'})
        self.output={'operation':'calendar.update','reference_id':'owned1','shift_minutes':30}
        prepared=self.prepare('Move that focus block thirty minutes later, preserving its duration and no attendees.',references=[{'id':'owned1','kind':'calendar','account_id':self.account,'start':{'dateTime':'2026-09-06T00:00:00+05:00'}}])
        self.assertEqual(self.model_calls[-1]['references'][0]['start']['dateTime'],'2026-09-07T15:00:00+05:00')
        self.execute(prepared)
        self.assertEqual(self.transport.event['start']['dateTime'],'2026-09-07T15:30:00+05:00')
        self.assertEqual(self.transport.event['end']['dateTime'],'2026-09-07T16:00:00+05:00')

    def test_relative_move_cannot_supply_now_fallback(self):
        self.output={'operation':'calendar.update','reference_id':'owned1','shift_minutes':30,'start':datetime.now(UTC).isoformat(),'end':datetime.now(UTC).isoformat()}
        with self.assertRaises(ValueError):self.prepare(references=[{'id':'owned1','kind':'calendar','account_id':self.account}])
        self.assertTrue(all(call[0]=='GET' for call in self.transport.calls))

    def test_wording_is_forwarded_to_model_without_magic_sentence(self):
        self.output={'operation':'calendar.create','summary':'Reading','start':'2026-09-06T10:00:00+05:00','end':'2026-09-06T10:30:00+05:00'}
        for wording in ['Pencil in half an hour for reading at ten tomorrow.','Tomorrow, ten till half past: reading time please.','Block 10–10:30 tomorrow for my book.']:
            prepared=self.prepare(wording);self.assertEqual(prepared['status'],'prepared');self.assertEqual(self.model_calls[-1]['owner_request'],wording)
        self.assertEqual(self.transport.calls,[])
    def test_blank_optional_fields_do_not_reject_or_clear_event(self):
        self.output={'operation':'calendar.create','summary':'Fixture','start':'2026-09-07T15:00:00+05:00','end':'2026-09-07T15:30:00+05:00','description':'','location':None}
        prepared=self.prepare();self.assertEqual(prepared['status'],'prepared')
        self.assertNotIn('description',prepared['preview']['event']);self.assertNotIn('location',prepared['preview']['event'])
        self.output={'operation':'calendar.update','reference_id':'owned1','summary':'Fixture revised','description':'   ','location':''}
        self.transport.event['description']='Preserve this saved note'
        prepared=self.prepare(references=[{'id':'owned1','kind':'calendar','account_id':self.account}]);self.execute(prepared)
        self.assertEqual(self.transport.event['description'],'Preserve this saved note')
    def test_reschedule_existing_and_undo_exact_snapshot(self):
        ref={'id':'owned1','kind':'calendar','account_id':self.account,'summary':'Walk'}
        self.output={'operation':'calendar.update','reference_id':'owned1','start':'2026-09-06T09:00:00+05:00','end':'2026-09-06T10:00:00+05:00'}
        result=self.execute(self.prepare('Move that walk an hour later',references=[ref]));self.assertTrue(result['undo_available']);self.assertEqual(self.transport.event['start']['dateTime'],'2026-09-06T09:00:00+05:00')
        self.output={'operation':'calendar.undo','reference_id':'owned1'};ref['change_id']=result['change_id'];self.execute(self.prepare('Undo that change',references=[ref]))
        self.assertEqual(self.transport.event['start']['dateTime'],'2026-09-06T08:00:00+05:00')
    def test_older_receipt_cannot_undo_newer_change(self):
        ref={'id':'owned1','kind':'calendar','account_id':self.account}
        self.output={'operation':'calendar.update','reference_id':'owned1','summary':'First edit'}
        first=self.execute(self.prepare(references=[ref]))
        self.output['summary']='Second edit'
        second=self.execute(self.prepare(references=[ref]));ref['change_id']=second['change_id']
        self.output={'operation':'calendar.undo','reference_id':'owned1'}
        calls=len(self.transport.calls)
        result=self.prepare('Undo my calendar change '+first['change_id']+' for event owned1',references=[ref])
        self.assertEqual(result['status'],'clarify');self.assertEqual(len(self.transport.calls),calls)
        self.assertEqual(self.transport.event['summary'],'Second edit')
        result=self.prepare('Undo my calendar change '+second['change_id']+' for event owned1',references=[ref])
        self.execute(result);self.assertEqual(self.transport.event['summary'],'First edit')
    def test_body_only_draft_update_preserves_subject_and_empty_recipient(self):
        self.output={'operation':'draft.create','subject':'Jarvis fixture','body':'Initial body','recipient':''}
        self.execute(self.prepare())
        self.output={'operation':'draft.update','reference_id':'draft1','subject':None,'recipient':'','body':'Revision two.'}
        prepared=self.prepare('Update only the unsent draft body. Keep its subject and recipients.',references=[{'id':'draft1','kind':'draft','account_id':self.account}])
        self.assertEqual(self.model_calls[-1]['references'][0]['subject'],'Jarvis fixture')
        self.assertIn('Initial body',self.model_calls[-1]['references'][0]['body'])
        self.execute(prepared)
        raw=self.transport.drafts['draft1']['message']['raw'];message=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw+'='*(-len(raw)%4)))
        self.assertEqual(message['Subject'],'Jarvis fixture');self.assertIsNone(message['To']);self.assertIn('Revision two.',message.get_body(preferencelist=('plain',)).get_content())
        self.assertFalse(any('/send' in call[1] for call in self.transport.calls))

    def test_blank_draft_update_fields_do_not_erase_existing_recipient(self):
        self.output={'operation':'draft.create','subject':'Preserved','body':'Original','recipient':'person@example.invalid'}
        self.execute(self.prepare())
        self.output={'operation':'draft.update','reference_id':'draft1','subject':'   ','recipient':None,'body':'Updated'}
        prepared=self.prepare(references=[{'id':'draft1','kind':'draft','account_id':self.account}])
        self.assertEqual(prepared['preview']['subject'],'Preserved');self.assertEqual(prepared['preview']['recipient'],'person@example.invalid')

    def test_draft_create_attachment_update_read_never_send(self):
        self.output={'operation':'draft.create','subject':'Review','body':'Please review this.','attachment_ids':['file1']}
        self.execute(self.prepare('Prepare this draft with the selected table',attachment_ids=['file1']))
        ref={'id':'draft1','kind':'draft','account_id':self.account}
        self.output={'operation':'draft.update','reference_id':'draft1','body':'A shorter note.'}
        self.execute(self.prepare('Make that draft shorter',references=[ref]))
        raw=self.transport.drafts['draft1']['message']['raw'];message=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw+'='*(-len(raw)%4)))
        self.assertEqual(message['Subject'],'Review');self.assertEqual(len(list(message.iter_attachments())),1)
        self.assertIn('A shorter note.',message.get_body(preferencelist=('plain',)).get_content())
        self.assertTrue(all('/send' not in call[1] for call in self.transport.calls))
    def test_hallucinated_ids_other_accounts_and_invitation_fields_stop(self):
        self.output={'operation':'calendar.update','reference_id':'madeup','summary':'x'}
        self.assertEqual(self.prepare(references=[])['status'],'clarify')
        self.output={'operation':'calendar.create','attendees':['someone']}
        with self.assertRaises(ValueError):self.prepare()
        self.output={'operation':'draft.create','subject':'x','body':'y','attachment_ids':['secret-file']}
        with self.assertRaises(PermissionError):self.prepare()
        self.assertEqual(self.transport.calls,[])
    def test_stale_event_and_invalid_token_cannot_mutate(self):
        self.output={'operation':'calendar.update','reference_id':'owned1','summary':'A walk'}
        p=self.prepare(references=[{'id':'owned1','kind':'calendar','account_id':self.account}])
        with self.assertRaises(PermissionError):self.actions.execute(p['preparation_id'],owner_token='fake',session_nonce='fixture')
        self.transport.event['etag']='v2'
        with self.assertRaises(PermissionError):self.execute(p)
        self.assertFalse(any(c[0]=='PATCH' for c in self.transport.calls))
    def test_mime_cannot_hide_recipient_or_sender(self):
        raw=base64.urlsafe_b64encode(b'Subject: Hi\nTo: other@example.invalid\n\nBody').decode()
        with self.assertRaises(PermissionError):self.actions.gmail.create(raw_base64url=raw,recipient='reviewed@example.invalid')
        raw=base64.urlsafe_b64encode(b'Subject: Hi\nBcc: secret@example.invalid\n\nBody').decode()
        with self.assertRaises(PermissionError):self.actions.gmail.create(raw_base64url=raw)
        self.assertEqual(self.transport.calls,[])
    def test_transport_read_is_individual_personal_event_only(self):
        self.assertTrue(PersonalGoogleActionTransport._allowed('GET','https://www.googleapis.com/calendar/v3/calendars/primary/events/owned1'))
        self.assertFalse(PersonalGoogleActionTransport._allowed('GET','https://www.googleapis.com/calendar/v3/calendars/primary/events'))
        self.assertFalse(PersonalGoogleActionTransport._allowed('GET','https://www.googleapis.com/calendar/v3/calendars/work/events/owned1'))
if __name__=='__main__':unittest.main()
