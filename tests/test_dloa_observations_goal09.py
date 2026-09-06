import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from hermes_attention.dloa_observations import observation_items,adapt_observation_caches,valid_cache
from hermes_attention.dloa_synthesis import _item_keys,evidence_packet
from hermes_attention.dloa import DloaWorkspace

class ObservationTest(unittest.TestCase):
 def fixture(self):
  a={'evidence_id':'resource','source_id':'message','text':'owner body','sha256':hashlib.sha256(b'owner body').hexdigest(),'source':'slack-owner','actor_state':'owner','actor_id':'owner','account_id':'team','connection_id':'slack','provenance':{'proof':'trusted'}}
  b={**copy.deepcopy(a),'source':'slack-colleagues','text':'search body','sha256':hashlib.sha256(b'search body').hexdigest(),'actor_state':'uncertain','actor_id':None}
  m={'id':'m','conversation_id':'s','skill':{},'sources':[{'source':i['source'],'items':[i]} for i in [a,b]],'coverage_complete':False}
  return a,b,m
 def test_distinct_views_exact_cache_adaptation_and_immutable_manifest(self):
  a,b,m=self.fixture();before=json.dumps(m,sort_keys=True);items=observation_items(m)
  self.assertEqual(len(items),2);self.assertEqual(len({i['evidence_id'] for i in items}),2);self.assertTrue(all(i['resource_evidence_id']=='resource' for i in items))
  reverse={**m,'sources':list(reversed(m['sources']))}
  self.assertEqual({i['evidence_id'] for i in items},{i['evidence_id'] for i in observation_items(reverse)})
  legacy=_item_keys(m,[b])['resource'];record={'evidence_id':'resource','source_sha256':b['sha256'],'status':'processed','facts':[],'limitations':[]};state={'extraction_cache':{legacy:record}}
  self.assertTrue(adapt_observation_caches(state,m));keys=_item_keys(m,items)
  self.assertEqual(sum(keys[i['evidence_id']] in state['extraction_cache'] for i in items),1);self.assertEqual(json.dumps(m,sort_keys=True),before)
  self.assertFalse(adapt_observation_caches(state,m));self.assertEqual(state['extraction_cache'][legacy],record)
  self.assertFalse(valid_cache({'evidence_id':'resource','source_sha256':b['sha256']},b))
 def test_identical_slack_sweeps_dedup_but_actor_difference_does_not(self):
  a,b,m=self.fixture();m['sources'][1]['items']=[{**copy.deepcopy(a),'source':'slack-colleagues'}]
  items=observation_items(m);self.assertEqual(len(items),1);self.assertEqual(items[0]['evidence_id'],'resource');self.assertEqual(len(items[0]['observation_collection_sources']),2)
  m['sources'][1]['items'][0]['actor_id']='other';self.assertEqual(len(observation_items(m)),2)
 def test_new_observation_only_extracted_and_unknown_legacy_attempt_denied(self):
  a,b,m=self.fixture();legacy=_item_keys(m,[b])['resource'];record={'evidence_id':'resource','source_sha256':b['sha256'],'status':'processed','facts':[],'limitations':[]}
  with tempfile.TemporaryDirectory() as t:
   w=DloaWorkspace(Path(t).resolve());state=w._read();state['extraction_cache']={legacy:record};w._save(state);seen=[]
   def model(prompt):
    rows=json.loads(prompt.split('\n',1)[1]);seen.extend(rows);return {'success':True,'text':json.dumps({'items':[{'evidence_id':i['evidence_id'],'facts':[],'limitations':[]} for i in rows]})}
   result=evidence_packet(w,m,{},model,origin_turn='s:new');self.assertEqual(len(seen),1);self.assertEqual(seen[0]['actor_id'],'owner');self.assertEqual(result['status'],'processing_pending')
   final=evidence_packet(w,m,{},lambda p:self.fail('no repeat'),origin_turn='s:new');self.assertEqual(final['status'],'completed')
  with tempfile.TemporaryDirectory() as t:
   w=DloaWorkspace(Path(t).resolve());state=w._read();state['extraction_attempts']={'unknown':{'status':'uncertain','origin_turn':'s:old','keys':[_item_keys(m,[a])['resource']]}};w._save(state)
   result=evidence_packet(w,m,{},lambda p:self.fail('must not call'),origin_turn='s:new');self.assertEqual(result['status'],'uncertain')
 def test_malformed_target_cache_fails_final_gates_without_model(self):
  from hermes_attention.dloa_final_recovery import cache_complete
  a,b,m=self.fixture();m['sources']=m['sources'][:1];key=_item_keys(m,[a])['resource']
  with tempfile.TemporaryDirectory() as t:
   w=DloaWorkspace(Path(t).resolve());state=w._read();state['extraction_cache']={key:{'evidence_id':'resource','source_sha256':a['sha256']}};w._save(state)
   self.assertFalse(cache_complete(state,m));result=evidence_packet(w,m,{},lambda p:self.fail('Malformed cache cannot rebill'),origin_turn='s:new');self.assertEqual(result['status'],'uncertain')

class AuthenticatedBodyRebindTest(unittest.TestCase):
 def fixture(self):
  body='I asked for Friday delivery. I explained billing. I reiterated Friday.'
  sha=lambda text:hashlib.sha256(text.encode()).hexdigest()
  receipt={'connection_id':'slack_inside_success_readonly','channel_id':'C123456789','message_ts':'1700000000.000001','author_id':'U123456789','fact_subject_verified':False,'response_sha256':'exact-receipt'}
  old={'evidence_id':'resource','source':'slack-owner','source_id':'message','source_ref':'https://slack.test/archives/C123456789/p1700000000000001','connection_id':'slack_inside_success_readonly','account_id':'team','occurred_at':'2023-11-14T22:13:20+00:00','kind':'activity','text':'search rendering','sha256':sha('search rendering'),'actor_state':'uncertain'}
  current={**old,'text':body,'sha256':sha(body),'actor_id':'U123456789','actor_state':'owner','provenance':{'message_ts':receipt['message_ts'],'verified_author_receipt':receipt,'verified_body_sha256':sha(body)}}
  event={'authenticated_body':body,'authenticated_body_sha256':sha(body),'receipt':receipt,'manifest_id':'old','conversation_id':'thread','original_text_sha256':old['sha256'],'evidence_id':'resource'}
  version={'version_id':'old-version','identity_receipt':event,'manifest_id':'old','conversation_id':'thread','original_text_sha256':old['sha256'],'facts':[{'text':part,'quote':part,'attribution':'owner'} for part in body.split('. ')],'event_bases':['message_act']*3}
  prior={'id':'old','conversation_id':'thread','sources':[{'source':'slack-owner','items':[old]}]}
  manifest={'id':'new','conversation_id':'thread','skill':{},'sources':[{'source':'slack-owner','items':[current]}],'window':{'report_date':'2023-11-14','start':'2023-11-14T00:00:00+00:00','end':'2023-11-15T00:00:00+00:00'}}
  cache={'status':'processed','evidence_id':'resource','source_sha256':current['sha256'],'facts':version['facts'][:2],'event_bases':['message_act']*2,'limitations':[]}
  state={'manifests':{'old':prior},'identity_fact_versions':{'resource':version},'extraction_cache':{_item_keys(manifest,[current])['resource']:cache}}
  return state,manifest,current
 def test_exact_authenticated_refresh_preserves_units_with_new_ids_and_current_lineage(self):
  from hermes_attention.dloa_report import catalogue
  state,manifest,item=self.fixture();before=copy.deepcopy(state)
  facts=catalogue(state,manifest);self.assertEqual(len(facts),3);self.assertTrue(all(f['owner_eligible'] for f in facts.values()))
  old_ids={hashlib.sha256(('old-version:'+str(i)).encode()).hexdigest()[:24] for i in range(3)}
  self.assertFalse(set(facts)&old_ids);self.assertTrue(all(f['current_source_lineage']['current_manifest_id']=='new' for f in facts.values()))
  self.assertEqual(state,before)
 def test_changed_body_actor_receipt_context_resource_or_quote_does_not_rebind(self):
  from hermes_attention.dloa_observations import identity_version_for
  for field,value in [('text','changed body'),('actor_id','U999999999'),('account_id','other'),('source_ref','https://slack.test/archives/C123456789/p1700000000000002'),('occurred_at','2026-09-06T12:14:54+00:00')]:
   state,m,item=self.fixture();item[field]=value;self.assertEqual(identity_version_for(state,m,item),{},field)
  state,m,item=self.fixture();m['conversation_id']='other';self.assertEqual(identity_version_for(state,m,item),{})
  state,m,item=self.fixture();item['provenance']['verified_author_receipt']={**item['provenance']['verified_author_receipt'],'response_sha256':'changed'};self.assertEqual(identity_version_for(state,m,item),{})
  state,m,item=self.fixture();state['identity_fact_versions']['resource']['facts'][0]['quote']='invented';self.assertEqual(identity_version_for(state,m,item),{})
  state,m,item=self.fixture();state['identity_fact_versions']['resource']['event_bases']=[];self.assertEqual(identity_version_for(state,m,item),{})
