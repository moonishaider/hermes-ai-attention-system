import sys,tempfile,unittest,json
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
from hermes_attention.storage import Store
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import jarvis_turn_intent as routing

class RoutingTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(':memory:');self.addCleanup(self.store.close)
        self.service=SimpleNamespace(store=self.store,paths=SimpleNamespace(runtime_dir=Path(self.tmp.name).resolve()))
        self.now=datetime(2026,9,5,18,tzinfo=timezone.utc);self.calls=[]
    def call(self,owner,output,tid='one'):
        def model(payload):self.calls.append(payload);return output
        return routing.handle({'sessionId':'jarvis_fixture','turnId':tid,'ownerRequest':owner},service=self.service,session_validator=lambda s:None,model=model,now=self.now)
    def test_owner_dates_and_cached_revision(self):
        first=self.call('Prepare my daily work report for yesterday',{'route':'dloa','dloa':{'reportDateText':'yesterday'}})
        self.assertEqual(first['dloa'],{'reportDate':'2026-09-04','refresh':False})
        self.assertTrue(self.call('Prepare my daily work report for yesterday',{},tid='one')['cacheHit']);self.assertEqual(len(self.calls),1)
        revision=self.call('Tighten the third bullet',{'route':'dloa'},tid='two');self.assertEqual(revision['dloa'],{'refresh':False})
        with self.assertRaises(PermissionError):self.call('Different owner request',{},tid='one')
    def test_generated_dates_and_ambiguous_overrides_cannot_change_window(self):
        r=self.call('Prepare report',{'route':'dloa','dloa':{'reportDateText':'2026-10-10'}})
        self.assertTrue(r['needsClarification']);self.assertEqual(r['dloa'],{'refresh':False})
        r=self.call('Start at six on my off day',{'route':'dloa','dloa':{'startOverrideText':'six'}},tid='two')
        self.assertTrue(r['needsClarification'])
    def test_explicit_now_and_iso_override(self):
        r=self.call('From 2026-09-04T06:00:00-04:00 up to now; refresh sources',{'route':'dloa','dloa':{'startOverrideText':'2026-09-04T06:00:00-04:00','throughText':'now','refreshText':'refresh sources'}})
        self.assertEqual(r['dloa']['startOverride'],'2026-09-04T10:00:00+00:00');self.assertTrue(r['dloa']['refresh']);self.assertEqual(r['dloa']['through'],self.now.isoformat())
    def test_model_cannot_widen_negative_refresh_or_preserve_clause(self):
        out=self.call('Do not refresh sources; just polish the report',{'route':'dloa','dloa':{'refreshText':'refresh sources'}})
        self.assertFalse(out['dloa']['refresh'])
        out=self.call('Preserve yesterday evidence and leave the sources alone',{'route':'dloa','dloa':{'refreshText':'leave the sources alone'}},tid='two')
        self.assertFalse(out['dloa']['refresh'])

    def test_explicit_semantic_source_continuation_literal_binding(self):
        out=self.call('Continue collecting remaining meeting evidence for my DLOA',{'route':'dloa','dloa':{'continueSourcesText':'Continue collecting remaining meeting evidence'}})
        self.assertTrue(out['dloa']['continueSources'])
        out=self.call('Do not continue collecting sources; edit the report',{'route':'dloa','dloa':{'continueSourcesText':'continue collecting sources'}},tid='two')
        self.assertFalse(out['dloa']['continueSources'])

    def test_personal_cache_requires_same_reference_context(self):
        text='Put a reading block on my personal calendar tomorrow';intent={'operation':'calendar.create','summary':'Reading'}
        self.call(text,{'route':'personal','personalIntent':intent})
        payload={'owner_request':text,'references':[],'attachment_ids':[]}
        self.assertEqual(routing.cached_personal(self.store.connection,'jarvis_fixture','one',payload),intent)
        self.assertIsNone(routing.cached_personal(self.store.connection,'other','one',payload))
        self.assertIsNone(routing.cached_personal(self.store.connection,'jarvis_fixture','one',{**payload,'references':[{'id':'changed'}]}))
    def test_invalid_model_authority_fields_rejected(self):
        with self.assertRaises(ValueError):self.call('Hello',{'route':'personal','personalIntent':{'operation':'draft.create','owner_token':'forged'}})
        with self.assertRaises(ValueError):self.call('Hello',{'route':'evil'})

    def test_month_name_dates_require_literal_complete_owner_date(self):
        for text in ['September 4, 2026','Sep 4, 2026','September 4 2026']:
            self.assertEqual(routing.temporal(text,'Report for '+text,'reportDate',self.now),'2026-09-04')
        for text,owner in [('September 4, 2026','Report September 5, 2026'),('September 4','Report September 4'),('September 31, 2026','Report September 31, 2026')]:
            with self.assertRaises(ValueError):routing.temporal(text,owner,'reportDate',self.now)
        with self.assertRaises(ValueError):routing.temporal('September 5 at 08:30','Through September 5 at 08:30','through',self.now)
