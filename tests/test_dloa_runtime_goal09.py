import asyncio
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from hermes_attention.dloa import SourcePage
from hermes_attention.dloa_runtime import DloaCoordinator,GithubCommitCollector,ZoomMeetingCollector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import jarvis_dloa


class CoordinatorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name).resolve();config=root/'config';(config/'actions').mkdir(parents=True)
        (config/'integrations.json').write_text(json.dumps({'external_sources':[{'id':'github_inside_success_readonly','owner_boundary':'Example-Work'},{'id':'github_personal_readonly','owner_boundary':'owner'}]}))
        (config/'actions/inside_success_daily_report.json').write_text(json.dumps({'workspace_id':'T_SYNTHETIC','author_user_id':'owner','channel_name':'daily-report'}))
        self.skill=root/'SKILL.md';self.skill.write_text('08:30 Miami workday. Meetings first. Preserve prior validated work.')
        self.paths=SimpleNamespace(config_dir=config,runtime_dir=root/'runtime-data',database=root/'absent.sqlite')
        self.syncs=0;self.reads=[]
        def sync(**kwargs):self.syncs+=1;return {'ok':True,'threads_read':2,'maximum_threads':kwargs['maximum_threads']}
        service=SimpleNamespace(sync_codex=sync,close=lambda:None)
        def collectors(plans,window,sync_result):
            async def collect(plan,window,cursor):
                self.reads.append(plan.source)
                return SourcePage([{'id':plan.source+'1','text':'Source-specific synthetic activity','occurred_at':'2026-09-04T14:00:00Z','actor_id':'owner'}],exhausted=True,coverage='full_declared_scope')
            return {p.source:collect for p in plans}
        self.coordinator=DloaCoordinator(self.paths,service_factory=lambda:service,collector_factory=collectors,skill_path=self.skill)

    async def test_whole_plan_once_then_revision_no_collection_or_sync(self):
        first=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='first',owner_request='DLOA for 2026-09-04')
        self.assertEqual(self.syncs,1);self.assertEqual(len(self.reads),6)
        self.assertEqual(first['synthesisPacket']['window']['start'],'2026-09-04T12:30:00+00:00')
        report=self.coordinator.finish(conversation_id='jarvis_fixture',turn_id='first',manifest_id=first['manifestId'],canonical_text='Original report',status='completed')
        self.assertTrue(report['saved'])
        next_=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='second',owner_request='Make the third bullet clearer without refreshing')
        self.assertTrue(next_['cacheHit']);self.assertEqual(self.syncs,1);self.assertEqual(len(self.reads),6)
        self.assertEqual(next_['synthesisPacket']['previous_report']['text'],'Original report')

    async def test_retained_boundary_ignores_transport_and_empty_failure_but_not_authority(self):
        from dataclasses import replace
        import copy
        first=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='original',owner_request='DLOA for 2026-09-04')
        state=self.coordinator.workspace._read();original=state['manifests'][first['manifestId']]
        original['window']['start']=original['window']['start'].replace('+00:00','Z')
        empty=copy.deepcopy(original);empty.update(id='ev_empty',created_at='2099-01-01T00:00:00Z')
        for source in empty['sources']:source['items']=[]
        state['manifests'][empty['id']]=empty;self.coordinator.workspace._save(state)
        plans,lock,github=self.coordinator._plans()
        self.coordinator._plans=lambda:([replace(p,timeout_seconds=65,page_size=1,max_pages=1) for p in plans],lock,github)
        second=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='revision',owner_request='Polish without refreshing')
        self.assertEqual(second['manifestId'],first['manifestId']);self.assertEqual(len(self.reads),6)
        for field,value in [('connection_id','changed'),('account_id','changed'),('owner_ids',('changed',)),('scope','changed'),('required',False)]:
            altered=[replace(p,**{field:value}) if p.source=='slack-owner' else p for p in plans]
            self.coordinator._plans=lambda:(altered,lock,github)
            with self.assertRaises(PermissionError):await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='denied_'+field,owner_request='Polish without refreshing')
        self.assertEqual(len(self.reads),6)
        self.coordinator._plans=lambda:(plans,lock,github)
        self.skill.write_text('Updated owner skill. 08:30 Miami.')
        changed=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='skill',owner_request='Polish without refreshing')
        self.assertNotEqual(changed['manifestId'],first['manifestId']);self.assertEqual(changed['synthesisPacket']['skill']['text'],self.skill.read_text())
        self.assertEqual(len(self.reads),6)

    async def test_refresh_retains_missing_evidence_and_exact_identity_version(self):
        from dataclasses import replace
        from hermes_attention.dloa import digest
        first=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='refreshbase',owner_request='DLOA for 2026-09-04')
        state=self.coordinator.workspace._read();old=state['manifests'][first['manifestId']];item=old['sources'][0]['items'][0]
        version={'conversation_id':'jarvis_fixture','manifest_id':old['id'],'original_text_sha256':item['sha256'],'version_id':'fixture'}
        state['identity_fact_versions']={item['evidence_id']:version};self.coordinator.workspace._save(state)
        plans,lock,github=self.coordinator._plans();self.coordinator._plans=lambda:([replace(p,timeout_seconds=65) for p in plans],lock,github)
        def collectors(plans,window,sync):
            async def empty(plan,window,cursor):return SourcePage([],exhausted=True,coverage='full_declared_scope')
            return {p.source:empty for p in plans}
        self.coordinator.collector_factory=collectors
        new=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='refreshnew',owner_request='Refresh DLOA for 2026-09-04',refresh=True)
        state=self.coordinator.workspace._read();manifest=state['manifests'][new['manifestId']]
        self.assertEqual(manifest['previous_id'],old['id']);self.assertEqual(sum(len(r['items']) for r in manifest['sources']),6)
        self.assertEqual(len(manifest['delta']['not_seen_on_refresh']),6);self.assertEqual(manifest['delta']['added'],[])
        self.assertTrue(all(r['retained_not_seen_ids'] and r['status']=='partial' for r in manifest['sources']))
        self.assertEqual(state['identity_version_bindings'][manifest['id']][item['evidence_id']],digest(version));self.assertEqual(state['identity_fact_versions'][item['evidence_id']],version)
        def changed_collectors(plans,window,sync):
            async def changed(plan,window,cursor):
                return SourcePage([{'id':plan.source+'1','text':'Source-specific synthetic activity','occurred_at':'2026-09-04T14:00:00Z','actor_id':'different_actor','provenance':{'corrected':True}}],exhausted=True,coverage='full_declared_scope')
            return {p.source:changed for p in plans}
        self.coordinator.collector_factory=changed_collectors
        changed=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='changedfacts',owner_request='Refresh DLOA for 2026-09-04',refresh=True)
        self.assertNotIn(item['evidence_id'],self.coordinator.workspace._read().get('identity_version_bindings',{}).get(changed['manifestId'],{}))
        self.coordinator._plans=lambda:([replace(p,account_id='different') for p in plans],lock,github)
        with self.assertRaises(PermissionError):await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='refreshdenied',owner_request='Refresh DLOA for 2026-09-04',refresh=True)

    async def test_zoom_refresh_reuses_existing_extraction_receipt(self):
        from hermes_attention.dloa_synthesis import _item_keys
        first=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='zoomold',owner_request='DLOA for 2026-09-04')
        state=self.coordinator.workspace._read();old=state['manifests'][first['manifestId']];item=next(r for r in old['sources'] if r['source']=='zoom')['items'][0]
        item['provenance']={'asset_retrieved_at':'old','asset_full_sha256':'full','asset_permissions':{'recording':True}}
        oldkey=_item_keys(old,[item])[item['evidence_id']];cached={'evidence_id':item['evidence_id'],'source_sha256':item['sha256'],'facts':[],'limitations':[],'status':'processed'}
        state.setdefault('extraction_cache',{})[oldkey]=cached;self.coordinator.workspace._save(state)
        def collectors(plans,window,sync):
            async def collect(plan,window,cursor):
                rows=[]
                if plan.source=='zoom':rows=[{'id':item['source_id'],'text':item['text'],'occurred_at':item['occurred_at'],'actor_id':item['actor_id'],'provenance':{**item['provenance'],'asset_retrieved_at':'new'}}]
                return SourcePage(rows,exhausted=True,coverage='full_declared_scope')
            return {p.source:collect for p in plans}
        self.coordinator.collector_factory=collectors
        refreshed=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='zoomnew',owner_request='Refresh DLOA for 2026-09-04',refresh=True)
        state=self.coordinator.workspace._read();new=state['manifests'][refreshed['manifestId']];newitem=next(r for r in new['sources'] if r['source']=='zoom')['items'][0];newkey=_item_keys(new,[newitem])[newitem['evidence_id']]
        self.assertNotEqual(newkey,oldkey);self.assertEqual(state['extraction_cache'][newkey],cached);self.assertEqual(state['extraction_refresh_aliases'][newkey]['original_key'],oldkey)

    def test_zoom_refresh_identity_ignores_only_transport_metadata(self):
        import copy,hashlib
        from hermes_attention.dloa import same_refresh_evidence
        old={'evidence_id':'asset','text':'Exact asset bytes','sha256':hashlib.sha256(b'Exact asset bytes').hexdigest(),'source':'zoom','actor_id':'a','provenance':{'asset_retrieved_at':'old','asset_coverage':'cached','asset_permissions':{'recording':True},'asset_full_sha256':'full'}}
        new=copy.deepcopy(old);new['provenance'].update(asset_retrieved_at='new',asset_coverage='fresh',asset_truncated=False,asset_next_offset=100)
        self.assertTrue(same_refresh_evidence(old,new))
        for mutate in [lambda x:x.update(text='Changed bytes'),lambda x:x.update(actor_id='other'),lambda x:x['provenance'].update(asset_permissions={'recording':False}),lambda x:x['provenance'].update(asset_full_sha256='changed')]:
            changed=copy.deepcopy(new);mutate(changed);self.assertFalse(same_refresh_evidence(old,changed))

    async def test_empty_catalogue_skips_composition_preserves_extraction_cost_no_report(self):
        prepared=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='emptyfacts',owner_request='DLOA for 2026-09-04')
        calls=[]
        def model(prompt):
            value=json.JSONDecoder().raw_decode(prompt.split('\n',1)[1])[0];self.assertIsInstance(value,list);calls.append(1)
            return {'success':True,'text':json.dumps({'items':[{'evidence_id':i['evidence_id'],'facts':[],'limitations':[]} for i in value]}),'usage_known':True,'input_tokens':100,'output_tokens':10,'estimated_cost_usd':0.02}
        result={'status':'processing_pending'}
        while result['status']=='processing_pending':result=self.coordinator.synthesize(conversation_id='jarvis_fixture',turn_id='emptyfacts',manifest_id=prepared['manifestId'],model=model)
        self.assertTrue(result['noEvidence']);self.assertEqual(result['currentTurnModelCalls'],1);self.assertEqual(result['totalCostUsd'],0.02);self.assertEqual(len(calls),1)
        finished=self.coordinator.finish(conversation_id='jarvis_fixture',turn_id='emptyfacts',manifest_id=prepared['manifestId'],canonical_text=result['text'],status='completed')
        self.assertFalse(finished['saved']);self.assertTrue(finished['noEvidence'])

    async def test_synthesis_has_no_collectors_and_durable_single_attempt(self):
        prepared=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='synthesis',owner_request='DLOA for 2026-09-04')
        calls=[]
        def model(prompt):
            calls.append(prompt);value=json.JSONDecoder().raw_decode(prompt.split('\n',1)[1])[0];return {'success':True,'text':json.dumps({'items':[{'evidence_id':i['evidence_id'],'facts':[{'text':'Synthetic source activity','span_start':i['source_spans'][0]['span_id'],'span_end':i['source_spans'][0]['span_id'],'attribution':'uncertain'}],'limitations':[]} for i in value]}) if isinstance(value,list) else json.dumps({'sections':[],'context_fact_ids':[]}), 'usage':{'input_tokens':100},'latency_ms':50}
        result=self.coordinator.synthesize(conversation_id='jarvis_fixture',turn_id='synthesis',manifest_id=prepared['manifestId'],model=model)
        while result['status']=='processing_pending':result=self.coordinator.synthesize(conversation_id='jarvis_fixture',turn_id='synthesis',manifest_id=prepared['manifestId'],model=model)
        self.assertEqual(result['status'],'completed');self.assertIn('08:30 Miami',calls[-1]);self.assertEqual(len(self.reads),6)
        again=self.coordinator.synthesize(conversation_id='jarvis_fixture',turn_id='synthesis',manifest_id=prepared['manifestId'],model=model)
        self.assertTrue(again['cacheHit']);self.assertEqual(len(calls),2)
        with self.assertRaises(PermissionError):self.coordinator.synthesize(conversation_id='other',turn_id='synthesis',manifest_id=prepared['manifestId'],model=model)
        next_=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='timeout',owner_request='Revise report')
        def failed(prompt):calls.append(prompt);raise TimeoutError('test')
        self.assertEqual(self.coordinator.synthesize(conversation_id='jarvis_fixture',turn_id='timeout',manifest_id=next_['manifestId'],model=failed)['status'],'uncertain')
        self.assertEqual(self.coordinator.synthesize(conversation_id='jarvis_fixture',turn_id='timeout',manifest_id=next_['manifestId'],model=model)['status'],'uncertain');self.assertEqual(len(calls),3)

    async def test_production_route_split_uses_routine_nonthinking_extraction_and_difficult_final(self):
        from unittest.mock import patch
        import hashlib
        prepared=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='routes',owner_request='DLOA for 2026-09-04')
        state=self.coordinator.workspace._read()
        for source in state['manifests'][prepared['manifestId']]['sources']:
            item=source['items'][0];item['text']='synthetic padding '*2000;item['sha256']=hashlib.sha256(item['text'].encode()).hexdigest()
        self.coordinator.workspace._save(state);calls=[]
        class Client:
            config={'routes':{'routine':{'thinking':False}}}
            def __init__(self,*args,**kwargs):pass
            def generate(self,route,prompt,**kwargs):
                value=json.JSONDecoder().raw_decode(prompt.split('\n',1)[1])[0];calls.append(route)
                self_outer.assertEqual(route,'routine' if isinstance(value,list) else 'difficult')
                self_outer.assertEqual(kwargs['max_output_tokens'],8192)
                self_outer.assertEqual(kwargs.get('thinking_override'),False if route=='difficult' else None)
                return {'success':True,'text':json.dumps({'items':[{'evidence_id':i['evidence_id'],'facts':[{'text':'Synthetic source activity','span_start':i['source_spans'][0]['span_id'],'span_end':i['source_spans'][0]['span_id'],'attribution':'uncertain'}],'limitations':[]} for i in value]}) if isinstance(value,list) else json.dumps({'sections':[],'context_fact_ids':[]})}
        self_outer=self;self.coordinator.service_factory=lambda:SimpleNamespace(store=None,close=lambda:None)
        with patch('hermes_attention.runtime_models.DirectModelClient',Client):
            result={'status':'processing_pending'}
            while result['status']=='processing_pending':result=self.coordinator.synthesize(conversation_id='jarvis_fixture',turn_id='routes',manifest_id=prepared['manifestId'])
        self.assertEqual(result['status'],'completed');self.assertEqual(calls[-1],'difficult');self.assertTrue(all(x=='routine' for x in calls[:-1]));self.assertEqual(len(calls),7)

    async def test_native_recovery_prepares_exact_retained_manifest_and_original_instructions(self):
        from unittest.mock import patch
        prepared=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='failed',owner_request='DLOA for 2026-09-04 with original detailed instructions')
        db=SimpleNamespace(get_messages=lambda sid:[{'role':'user','content':'Retry retained evidence only','display_metadata':{'jarvis_turn_id':'new'}}],close=lambda:None)
        request={'operation':'recovery-prepare','sessionId':'jarvis_fixture','failedTurnId':'failed','turnId':'new'}
        with patch.object(jarvis_dloa.local,'_jarvis_session',return_value=None):
            result=jarvis_dloa.handle(request,coordinator=self.coordinator,db_factory=lambda:db)
            self.assertEqual(result,jarvis_dloa.handle(request,coordinator=self.coordinator,db_factory=lambda:db))
            with self.assertRaises(PermissionError):jarvis_dloa.handle({**request,'turnId':'forged'},coordinator=self.coordinator,db_factory=lambda:db)
        self.assertEqual(result['manifestId'],prepared['manifestId']);self.assertEqual(len(self.reads),6)
        binding=self.coordinator.workspace._read()['native_turns']['jarvis_fixture:new']
        self.assertIn('original detailed instructions',binding['owner_request']);self.assertIn('Retry retained evidence only',binding['owner_request'])

    async def test_multipass_final_includes_tail_and_revision_reuses_extractions(self):
        import hashlib
        prepared=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='multipass',owner_request='DLOA for 2026-09-04')
        state=self.coordinator.workspace._read();manifest=state['manifests'][prepared['manifestId']]
        for index,source in enumerate(manifest['sources']):
            item=source['items'][0];item['text']='synthetic context '*3500+('TAIL WORK FINISHED' if index==5 else '');item['sha256']=hashlib.sha256(item['text'].encode()).hexdigest()
        self.coordinator.workspace._save(state);extractions=[]
        def model(prompt):
            data=json.JSONDecoder().raw_decode(prompt.split('\n',1)[1])[0]
            if isinstance(data,list):
                extractions.extend(i['evidence_id'] for i in data)
                return {'success':True,'text':json.dumps({'items':[{'evidence_id':i['evidence_id'],'facts':[{'text':'Tail completion retained','span_start':i['source_spans'][-1]['span_id'],'span_end':i['source_spans'][-1]['span_id'],'attribution':'uncertain'}] if any('TAIL WORK FINISHED' in span['text'] for span in i['source_spans']) else [],'limitations':[]} for i in data]})}
            self.assertTrue(data['facts'])
            return {'success':True,'text':json.dumps({'sections':[],'context_fact_ids':[f['fact_id'] for f in data['facts']]})}
        result=self.coordinator.synthesize(conversation_id='jarvis_fixture',turn_id='multipass',manifest_id=prepared['manifestId'],model=model)
        while result['status']=='processing_pending':result=self.coordinator.synthesize(conversation_id='jarvis_fixture',turn_id='multipass',manifest_id=prepared['manifestId'],model=model)
        self.assertEqual(result['status'],'completed');self.assertEqual(len(extractions),6)
        revision=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='revise-large',owner_request='Tighten the same evidence')
        self.assertEqual(self.coordinator.synthesize(conversation_id='jarvis_fixture',turn_id='revise-large',manifest_id=revision['manifestId'],model=model)['status'],'completed')
        self.assertEqual(len(extractions),6)


    async def test_bounded_source_continuation_preserves_other_evidence_and_turn_binding(self):
        from unittest.mock import patch
        first=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='first',owner_request='DLOA for 2026-09-04')
        async def enrich(items):
            for item in items:item['text']+=' Extra transcript';item['provenance']['asset_retrieved_at']='2026-09-05T18:00:00Z'
            return [],0
        async def close():pass
        collector=SimpleNamespace(enrich=enrich,close=close,asset_reads=1,retained_chunks=lambda items,limit:[])
        with patch('hermes_attention.dloa_runtime.ZoomMeetingCollector',return_value=collector):
            result=await self.coordinator.continue_sources(conversation_id='jarvis_fixture',turn_id='continue',manifest_id=first['manifestId'],owner_request='Continue remaining meeting evidence',max_batches=1)
            replay=await self.coordinator.continue_sources(conversation_id='jarvis_fixture',turn_id='continue',manifest_id=first['manifestId'],owner_request='Continue remaining meeting evidence',max_batches=1)
        self.assertTrue(replay['cacheHit']);self.assertEqual(len(self.reads),6);self.assertEqual(self.syncs,1)
        old=self.coordinator.workspace.get(first['manifestId'],'jarvis_fixture');new=self.coordinator.workspace.get(result['manifestId'],'jarvis_fixture')
        self.assertEqual(old['sources'][:5],new['sources'][:5]);self.assertNotEqual(old['sources'][5]['items'][0]['sha256'],new['sources'][5]['items'][0]['sha256'])
        self.assertEqual(result['remaining']['meetingAssets'],0)

    async def test_continuation_uses_next_page_without_rereading_finished_assets(self):
        from unittest.mock import patch
        prepared=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='cursor',owner_request='DLOA for 2026-09-04')
        state=self.coordinator.workspace._read();source=next(s for s in state['manifests'][prepared['manifestId']]['sources'] if s['source']=='zoom')
        source['cursor_after']='opaque-fixture-cursor';source['items'][0]['provenance'].update(asset_retrieved_at='2020-01-01T00:00:00Z',asset_truncated=False)
        original_text=source['items'][0]['text'];self.coordinator.workspace._save(state);calls=[]
        collector=ZoomMeetingCollector('zoom_fixture')
        async def call(args,**kwargs):
            calls.append((args,kwargs));self.assertFalse(kwargs.get('tool_name'))
            self.assertEqual(args['next_page_token'],'opaque-fixture-cursor');return {'meetings':[]}
        async def close():pass
        collector.reader.call=call;collector.close=close
        with patch('hermes_attention.dloa_runtime.ZoomMeetingCollector',return_value=collector):
            result=await self.coordinator.continue_sources(conversation_id='jarvis_fixture',turn_id='next',manifest_id=prepared['manifestId'],owner_request='Continue existing meeting evidence',max_batches=1)
        self.assertEqual(len(calls),1);self.assertEqual(result['assetReads'],0);self.assertFalse(result['remaining']['meetingPages'])
        source=next(s for s in self.coordinator.workspace.get(result['manifestId'],'jarvis_fixture')['sources'] if s['source']=='zoom')
        self.assertEqual(source['items'][0]['text'],original_text)

    async def test_finish_crash_before_and_after_atomic_save_never_orphans_or_duplicates(self):
        from unittest.mock import patch
        first=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='first',owner_request='DLOA for 2026-09-04')
        args=dict(conversation_id='jarvis_fixture',turn_id='first',manifest_id=first['manifestId'],canonical_text='Canonical complete text',status='completed',run_id='native-run')
        original=self.coordinator.workspace._save
        with patch.object(self.coordinator.workspace,'_save',side_effect=OSError('before replacement')):
            with self.assertRaises(OSError):self.coordinator.finish(**args)
        self.assertEqual(self.coordinator.workspace._read()['reports'],{})
        def after(state):original(state);raise OSError('after replacement')
        with patch.object(self.coordinator.workspace,'_save',side_effect=after):
            with self.assertRaises(OSError):self.coordinator.finish(**args)
        reports=self.coordinator.workspace._read()['reports'];self.assertEqual(len(reports),1)
        self.assertEqual(next(iter(reports.values()))['canonical_turn_id'],'first')
        self.assertTrue(self.coordinator.finish(**args)['idempotent']);self.assertEqual(len(self.coordinator.workspace._read()['reports']),1)

    async def test_same_turn_refresh_retry_is_idempotent_changed_input_denied(self):
        first=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='first',owner_request='DLOA for 2026-09-04',refresh=True)
        retry=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='first',owner_request='DLOA for 2026-09-04',refresh=True)
        self.assertEqual(first['manifestId'],retry['manifestId']);self.assertEqual(self.syncs,1)
        with self.assertRaises(ValueError):await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='first',owner_request='Different input')

    async def test_cancelled_report_not_finished_and_cross_turn_binding_denied(self):
        first=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='first',owner_request='DLOA for 2026-09-04')
        self.assertFalse(self.coordinator.finish(conversation_id='jarvis_fixture',turn_id='first',manifest_id=first['manifestId'],canonical_text='Partial',status='cancelled')['saved'])
        with self.assertRaises(PermissionError):self.coordinator.finish(conversation_id='jarvis_fixture',turn_id='other',manifest_id=first['manifestId'],canonical_text='Wrong thread',status='completed')

    async def test_explicit_refresh_and_multi_day_extension(self):
        first=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='first',owner_request='DLOA for 2026-09-04')
        second=await self.coordinator.prepare(conversation_id='jarvis_fixture',turn_id='second',owner_request='Extend up to this supplied point',report_date='2026-09-04',through='2026-09-06T15:00:00Z',start_override='2026-09-04T10:00:00Z',refresh=True)
        self.assertFalse(second['cacheHit']);self.assertEqual(self.syncs,2)
        self.assertEqual(second['synthesisPacket']['window']['start'],'2026-09-04T10:00:00+00:00')


class ProviderShapeTest(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_truncated_asset_recovers_once_and_chunks_preserve_tail(self):
        from datetime import datetime,timezone
        with tempfile.TemporaryDirectory() as directory:
            collector=ZoomMeetingCollector('zoom_fixture',cache_root=Path(directory).resolve());calls=[]
            collector._cache('meeting',{'text':'legacy prefix','truncated':True,'retrieved_at':'2026-01-01T00:00:00Z'})
            full={'recording':{'has_permission':True,'transcripts':[{'text':'abcde'*32000}]}}
            async def read(*args,**kwargs):calls.append(1);return full
            collector.reader.call=read
            raw=[{'id':'meeting','text':'Synthetic topic','source_ref':None,'provenance':{'asset_retrieved_at':'2026-01-01T00:00:00Z','asset_truncated':True}}]
            await collector.enrich(raw);self.assertEqual(len(calls),1)
            item={**raw[0],'source_id':'meeting','evidence_id':'base','connection_id':'zoom_fixture'}
            first=collector.retained_chunks([item],limit=2);self.assertEqual(len(first),2);self.assertTrue(item['provenance']['asset_truncated'])
            # Recreated collector has expired freshness cache but uses retained bytes for this manifest.
            data=collector._cache('meeting',retained=True);data['retrieved_at']='2026-01-01T00:00:00Z';collector._cache('meeting',data)
            resumed=ZoomMeetingCollector('zoom_fixture',cache_root=Path(directory).resolve());resumed.reader.call=read
            raws=[{'id':item['source_id'],'text':item['text'],'source_ref':None,'provenance':item['provenance']}]
            await resumed.enrich(raws);second=resumed.retained_chunks([item],limit=2)
            self.assertEqual(len(calls),1);self.assertFalse(item['provenance']['asset_truncated'])
            chunks=first+second;assembled=data['text']+''.join(c['text'] for c in chunks)
            self.assertEqual(assembled,data['full_text']);self.assertEqual(len({c['evidence_id'] for c in chunks}),len(chunks))
            self.assertEqual(chunks[-1]['provenance']['asset_end'],len(data['full_text']))
            await resumed.enrich(raws);self.assertEqual(len(calls),1)

    async def test_already_fetched_asset_not_reread_without_any_cache(self):
        collector=ZoomMeetingCollector('zoom_fixture');calls=[]
        async def read(*args,**kwargs):calls.append(1);raise AssertionError('must not read')
        collector.reader.call=read
        items=[{'id':'done','text':'Retained original','provenance':{'asset_retrieved_at':'2020-01-01T00:00:00Z','asset_truncated':False}}]
        await collector.enrich(items);self.assertEqual(calls,[]);self.assertEqual(items[0]['text'],'Retained original')

    async def test_current_zoom_shape_and_asset_reads_are_not_attendance(self):
        collector=ZoomMeetingCollector('zoom_readonly');calls=[]
        async def call(args,**kwargs):
            calls.append((args,kwargs))
            if kwargs.get('tool_name')=='get_meeting_assets':return {'deep_url':'https://zoom.us/meeting','recording':{'transcripts':[{'text':'Synthetic transcript'}],'cdn_urls':['https://example.invalid/signed?token=secret']}}
            return {'meetings':[{'meeting_uuid':'uuid/with+symbols=','meeting_start_time':'2026-09-04T14:00:00Z','topic':'Synthetic meeting'}],'has_more':True}
        collector.reader.call=call
        plan=SimpleNamespace(page_size=50);window=SimpleNamespace(start='2026-09-04T12:30:00Z',end='2026-09-05T12:30:00Z')
        result=await collector(plan,window,None)
        self.assertEqual(len(calls),2);self.assertIsNone(result.items[0]['actor_id'])
        self.assertNotIn('token=secret',result.items[0]['text'])
        self.assertIn('Synthetic transcript',result.items[0]['text'])
        self.assertTrue(any('continuation' in note for note in result.limitations))
        self.assertIn('%252F',calls[1][0]['meetingId'])

    async def test_zoom_filters_outside_window_before_bounded_asset_reads(self):
        collector=ZoomMeetingCollector('zoom_readonly');assets=[]
        async def call(args,**kwargs):
            if kwargs.get('tool_name'):
                assets.append(args['meetingId']);return {'summary':'Synthetic summary'}
            return {'meetings':[{'meeting_uuid':'outside','meeting_start_time':'2026-08-01T12:00:00Z'},{'meeting_uuid':'one','meeting_start_time':'2026-09-04T14:00:00Z'},{'meeting_uuid':'two','meeting_start_time':'2026-09-04T15:00:00Z'},{'meeting_uuid':'three','meeting_start_time':'2026-09-04T16:00:00Z'}]}
        collector.reader.call=call
        plan=SimpleNamespace(page_size=50);window=SimpleNamespace(start='2026-09-04T12:30:00Z',end='2026-09-05T12:30:00Z')
        first=await collector(plan,window,None);second=await collector(plan,window,'page2')
        self.assertEqual(assets,['one','two']);self.assertEqual(len(first.items),3);self.assertEqual(len(second.items),3)
        self.assertTrue(any('outside' in item for item in first.limitations));self.assertTrue(any('2 meeting' in item for item in second.limitations))

    async def test_zoom_asset_cache_continues_pending_without_rereading_first_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory).resolve();calls=[]
            async def call(args,**kwargs):
                calls.append(args['meetingId']);return {'summary':'Synthetic '+args['meetingId']}
            def rows():return [{'id':str(i),'text':'Meeting '+str(i),'source_ref':None,'provenance':{}} for i in range(4)]
            first=ZoomMeetingCollector('zoom_readonly',cache_root=cache);first.reader.call=call
            data=rows();_,pending=await first.enrich(data)
            self.assertEqual(pending,2);self.assertEqual(calls,['0','1'])
            second=ZoomMeetingCollector('zoom_readonly',cache_root=cache);second.reader.call=call
            data=rows();_,pending=await second.enrich(data)
            self.assertEqual(pending,0);self.assertEqual(calls,['0','1','2','3'])
            self.assertTrue(all(x['provenance']['asset_retrieved_at'] for x in data))

    async def test_github_current_compact_shape_matches_exact_owner_and_url(self):
        collector=GithubCommitCollector('github_inside_success_readonly','Example-Work')
        async def call(args):return {'total_count':1,'items':[{'sha':'abc','html_url':'https://github.com/Example-Work/repo/commit/abc','repository':{'full_name':'Example-Work/repo'},'author':{'login':'owner'},'commit':{'message':'Synthetic code','committer':{'date':'2026-09-04T14:00:00Z'}}}]}
        collector.reader.call=call
        result=await collector(SimpleNamespace(page_size=20),SimpleNamespace(start='2026-09-04T12:30:00Z',end='2026-09-05T12:30:00Z'),None)
        self.assertEqual(len(result.items),1);self.assertEqual(result.items[0]['actor_id'],'owner')

    async def test_github_source_owner_escape_rejected(self):
        collector=GithubCommitCollector('github_inside_success_readonly','Example-Work')
        async def call(args):return {'items':[{'sha':'x','repository':{'owner':{'login':'unrelated'}},'commit':{'message':'irrelevant'}}]}
        collector.reader.call=call
        with self.assertRaises(PermissionError):await collector(SimpleNamespace(page_size=20),SimpleNamespace(start='2026-09-04T12:30:00Z',end='2026-09-05T12:30:00Z'),None)


class NativeFinishTest(unittest.TestCase):
    def test_only_canonical_completed_content_is_forwarded(self):
        db=SimpleNamespace(get_session=lambda sid:{'id':sid,'source':'desktop'},get_messages=lambda sid:[{'role':'assistant','content':'Canonical exact report','display_metadata':{'jarvis_turn_id':'t1','status':'completed','run_id':'run1'}}],close=lambda:None)
        calls=[]
        c=SimpleNamespace(finish=lambda **kwargs:calls.append(kwargs) or {'saved':True})
        result=jarvis_dloa.handle({'operation':'finish','sessionId':'jarvis_fixture','turnId':'t1','manifestId':'ev_test'},coordinator=c,db_factory=lambda:db)
        self.assertTrue(result['saved']);self.assertEqual(calls[0]['canonical_text'],'Canonical exact report')
        with self.assertRaises(ValueError):jarvis_dloa.handle({'operation':'finish','sessionId':'jarvis_fixture','turnId':'t1','manifestId':'ev_test','canonical_text':'forged'},coordinator=c,db_factory=lambda:db)

if __name__=='__main__':unittest.main()

class CancellationBridgeTest(unittest.TestCase):
    def test_exact_native_cancel_marker_only(self):
        import sqlite3
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory).resolve()/'fixture.sqlite'
            with sqlite3.connect(database) as conn:
                conn.execute('CREATE TABLE native_cancelled_turns(session_id TEXT,turn_id TEXT)');conn.execute('INSERT INTO native_cancelled_turns VALUES(?,?)',('jarvis_fixture','cancelled'))
            db=SimpleNamespace(get_messages=lambda sid:[{'content':'cancel everything','display_metadata':{'jarvis_turn_id':'different','status':'cancelled'}}],close=lambda:None)
            with patch.object(jarvis_dloa.local,'_jarvis_session',return_value=None):
                self.assertTrue(jarvis_dloa.cancellation_requested('jarvis_fixture','cancelled',database,lambda:db))
                self.assertFalse(jarvis_dloa.cancellation_requested('jarvis_fixture','active',database,lambda:db))
                self.assertFalse(jarvis_dloa.cancellation_requested('other','cancelled',database,lambda:db))
