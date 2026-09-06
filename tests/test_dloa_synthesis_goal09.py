import json,tempfile,unittest,hashlib
from pathlib import Path
from hermes_attention.dloa import DloaWorkspace
from hermes_attention.dloa_synthesis import evidence_packet

class SynthesisTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.w=DloaWorkspace(Path(self.tmp.name).resolve());self.items=[]
  for i in range(4):
   text='irrelevant '*6000+('TAIL ONLY: delivered workbook' if i==3 else '')
   self.items.append({'evidence_id':str(i),'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'actor_state':'owner','source':'fixture'})
  self.manifest={'skill':{'text':'usual private format'},'sources':[{'items':self.items}],'coverage_complete':False};self.packet={'omitted_evidence_ids':['3'],'evidence':[]};self.calls=[]
 def model(self,prompt):
  items=json.loads(prompt.split('\n',1)[1]);self.calls.append([i['evidence_id'] for i in items]);rows=[]
  for i in items:
   selected=next((span for span in i['source_spans'] if 'TAIL ONLY' in span['text']),None)
   facts=[{'text':'Delivered workbook','span_start':selected['span_id'],'span_end':selected['span_id'],'attribution':'owner'}] if selected else []
   rows.append({'evidence_id':i['evidence_id'],'facts':facts,'limitations':[]})
  return {'success':True,'text':json.dumps({'items':rows})}
 def test_successful_extraction_retains_provider_cache_counts_in_aggregate(self):
  from hermes_attention.dloa_synthesis import current_turn_usage
  manifest={**self.manifest,'sources':[{'items':self.items[:1]}]}
  def model(prompt):return {**self.model(prompt),'input_tokens':100,'output_tokens':20,'cached_input_tokens':10,'usage_known':True,'estimated_cost_usd':0.01}
  result=evidence_packet(self.w,manifest,self.packet,model,origin_turn='cache-count')
  if result['status']=='processing_pending':result=evidence_packet(self.w,manifest,self.packet,lambda _:self.fail('No re-extraction'),origin_turn='cache-count')
  self.assertEqual(result['status'],'completed')
  state=self.w._read();self.assertEqual(next(iter(state['extraction_attempts'].values()))['usage']['cached_input_tokens'],10)
  state['style_review_attempts']={'cache-count':{'usage':{'input_tokens':20,'output_tokens':5,'cached_input_tokens':5,'usage_known':True,'estimated_cost_usd':0.001}}};self.w._save(state)
  final={'input_tokens':30,'output_tokens':6,'cached_input_tokens':8,'usage_known':True,'estimated_cost_usd':0.002}
  aggregate=current_turn_usage(self.w,'cache-count',final)
  self.assertEqual(aggregate['usageBreakdown']['cached_input_tokens'],23)
  self.assertEqual(aggregate['totalUsage']['input_tokens'],150)
  self.assertIsNone(current_turn_usage(self.w,'cache-count',{**final,'cached_input_tokens':None})['usageBreakdown']['cached_input_tokens'])

 def test_whitespace_only_revalidation_is_atomic_exact_and_idempotent(self):
  from hermes_attention.dloa_synthesis import revalidate_extraction,_source_quote,_item_keys
  self.assertEqual(_source_quote('done today','work done\n  today.'),'done\n  today')
  self.assertEqual(_source_quote('personal/company','personal/\ncompany'),'personal/\ncompany')
  self.assertEqual(_source_quote('alpha:beta','alpha:\r\n  beta'),'alpha:\r\n  beta')
  for quote,text in [('something','some\nthing'),('alpha:changed','alpha:\nbeta'),('personal/company','personal/ company')]:
   with self.assertRaises(ValueError):_source_quote(quote,text)
  for quote in ['done tomorrow','Done today','done ... today']:
   with self.assertRaises(ValueError):_source_quote(quote,'done\n today')
  item={'evidence_id':'one','text':'done\n today','sha256':hashlib.sha256(b'done\n today').hexdigest(),'actor_state':'other'}
  manifest={'skill':{},'sources':[{'items':[item]}]};keys=_item_keys(manifest,[item])
  response=json.dumps({'items':[{'evidence_id':'one','facts':[{'text':'Done','quote':'done today','attribution':'other'}],'limitations':[]}]})
  attempt={'origin_turn':'s:t','status':'uncertain','failure_reason':'Extraction quote is not supported by its chunk','keys':list(keys.values()),'response_received':True,'failed_response_truncated':False,'usage':{'usage_known':True,'estimated_cost_usd':0.1},'failed_response_text':response,'failed_response_sha256':hashlib.sha256(response.encode()).hexdigest()}
  state={'native_turns':{'s:t':{'manifest_id':'m'}},'manifests':{'m':manifest},'extraction_attempts':{'b':attempt}};self.w._save(state)
  d=revalidate_extraction(self.w,'s','t',diagnose=True);self.assertTrue(d['eligible']);digest=d['batches'][0]['attemptDigest']
  with self.assertRaises(ValueError):revalidate_extraction(self.w,'s','t','b','wrong')
  self.assertNotIn('extraction_cache',self.w._read())
  revalidate_extraction(self.w,'s','t','b',digest)
  self.assertTrue(revalidate_extraction(self.w,'s','t','b',digest)['cacheHit'])
  saved=self.w._read();self.assertEqual(saved['extraction_attempts']['b'],attempt);self.assertEqual(next(iter(saved['extraction_cache'].values()))['facts'][0]['quote'],'done\n today')
  from hermes_attention.dloa_synthesis import diagnose_extraction
  original=json.loads(json.dumps(saved))
  for danger in ['unknown','final']:
   altered=json.loads(json.dumps(saved))
   if danger=='unknown':altered['extraction_attempts']['unknown']={'origin_turn':'s:t','status':'running','keys':['unknown']}
   else:altered['synthesis_attempts']={'s:t':{'status':'running'}}
   self.w._save(altered);self.assertFalse(revalidate_extraction(self.w,'s','t',diagnose=True)['eligible'])
  self.w._save(original)
  child=json.loads(json.dumps(original));child['native_turns']['s:child']={'manifest_id':'m','recovery_of':'s:t'};child['extraction_local_edges']={'s:child':{'parent':'s:t','batches':{'b':digest}}};self.w._save(child)
  diagnosis=diagnose_extraction(self.w,'/nonexistent','s','child');self.assertTrue(diagnosis['eligible']);self.assertEqual(diagnosis['lineageTurnIds'],['child','t'])
  self.assertEqual(revalidate_extraction(self.w,'s','child',diagnose=True)['incompleteBatches'],[])
  child['extraction_local_edges']['s:child']['batches']['b']='tampered';self.w._save(child);self.assertFalse(diagnose_extraction(self.w,'/nonexistent','s','child')['eligible'])
  for bad in ['paraphrase','owner','truncated','unknown']:
   copy=json.loads(json.dumps(state));a=copy['extraction_attempts']['b']
   if bad in {'paraphrase','owner'}:
    v=json.loads(a['failed_response_text']);v['items'][0]['facts'][0]['quote' if bad=='paraphrase' else 'attribution']='done tomorrow' if bad=='paraphrase' else 'owner';a['failed_response_text']=json.dumps(v);a['failed_response_sha256']=hashlib.sha256(a['failed_response_text'].encode()).hexdigest()
   elif bad=='truncated':a['failed_response_truncated']=True
   else:a['response_received']=False
   self.w._save(copy);self.assertEqual(revalidate_extraction(self.w,'s','t',diagnose=True)['eligible'],bad in {'paraphrase','owner'});self.assertNotIn('extraction_cache',self.w._read())

 def test_source_span_reconstruction_rejects_cross_item_and_owner_widening(self):
  from hermes_attention.dloa_synthesis import _spans,_item_keys,_validate_rows
  a={'evidence_id':'a','text':'first\n'+('x'*1000)+' tail','sha256':'shaA','actor_state':'other'}
  b={**a,'evidence_id':'b','sha256':'shaB'};manifest={'skill':{}};keys=_item_keys(manifest,[a,b]);spans=_spans(a)
  self.assertEqual(''.join(x['text'] for x in spans),a['text'])
  fact={'text':'Supported detail','span_start':spans[0]['span_id'],'span_end':spans[-1]['span_id'],'attribution':'other'}
  value={'items':[{'evidence_id':'a','facts':[fact],'limitations':[]}]}
  normalized=_validate_rows(value,[a],keys,span_mode=True);self.assertEqual(normalized[keys['a']]['facts'][0]['quote'],a['text'])
  for patch in [{'span_start':_spans(b)[0]['span_id']},{'span_start':spans[-1]['span_id'],'span_end':spans[0]['span_id']},{'quote':'made up'}]:
   with self.assertRaises(ValueError):_validate_rows({'items':[{'evidence_id':'a','facts':[{**fact,**patch}],'limitations':[]}]},[a],keys,span_mode=True)

  owner={**fact,'attribution':'owner'};original=json.dumps(owner,sort_keys=True)
  result=_validate_rows({'items':[{'evidence_id':'a','facts':[owner],'limitations':[]}]},[a],keys,span_mode=True)[keys['a']]
  self.assertEqual(result['facts'][0]['attribution'],'uncertain');self.assertEqual(result['facts'][0]['quote'],a['text']);self.assertEqual(result['attribution_normalization'][0]['original_attribution'],'owner');self.assertEqual(json.dumps(owner,sort_keys=True),original)
  with self.assertRaises(ValueError):_validate_rows({'items':[{'evidence_id':'a','facts':[{**owner,'span_start':'invented'}],'limitations':[]}]},[a],keys,span_mode=True)

 def test_partial_received_salvage_preserves_invalid_item_for_new_turn(self):
  from hermes_attention.dloa_synthesis import _item_keys,revalidate_extraction
  items=[{'evidence_id':str(n),'text':'Completed exact work','sha256':hashlib.sha256(b'Completed exact work').hexdigest(),'actor_state':'owner'} for n in range(2)]
  manifest={'skill':{},'sources':[{'items':items}],'coverage_complete':False};keys=_item_keys(manifest,items)
  response=json.dumps({'items':[{'evidence_id':i['evidence_id'],'facts':[{'text':'Fact','quote':'Completed exact work' if n==0 else 'Invented quote','attribution':'owner'}],'limitations':[]} for n,i in enumerate(items)]})
  attempt={'origin_turn':'s:old','status':'uncertain','failure_reason':'Extraction quote is not supported by its chunk','keys':list(keys.values()),'response_received':True,'failed_response_truncated':False,'usage':{'usage_known':True,'estimated_cost_usd':0.1},'failed_response_text':response,'failed_response_sha256':hashlib.sha256(response.encode()).hexdigest()}
  self.w._save({'native_turns':{'s:old':{'manifest_id':'m'}},'manifests':{'m':manifest},'extraction_attempts':{'b':attempt}})
  diagnosis=revalidate_extraction(self.w,'s','old',diagnose=True);d=diagnosis['batches'][0];self.assertEqual((d['chunkCount'],d['validatedChunkCount'],d['remainingChunkCount']),(2,1,1))
  receipt=revalidate_extraction(self.w,'s','old','b',d['attemptDigest']);self.assertEqual(receipt['status'],'salvaged');self.assertEqual(receipt['remainingChunkCount'],1)
  state=self.w._read();self.assertEqual(state['extraction_attempts']['b'],attempt);self.assertNotIn(keys['1'],state['extraction_cache'])
  self.assertTrue(revalidate_extraction(self.w,'s','old','b',d['attemptDigest'])['cacheHit'])
  self.assertEqual(evidence_packet(self.w,manifest,{},lambda p:self.fail('Old replay'),origin_turn='s:old')['status'],'uncertain')
  state['native_turns']['s:new']={'manifest_id':'m','recovery_of':'s:old'};state['extraction_local_edges']={'s:new':{'parent':'s:old','batches':{'b':d['attemptDigest']}}};self.w._save(state);calls=[]
  def model(prompt):
   rows=json.loads(prompt.split('\n',1)[1]);calls.extend(i['evidence_id'] for i in rows)
   return {'success':True,'text':json.dumps({'items':[{'evidence_id':i['evidence_id'],'facts':[],'limitations':['No supported relevant fact']} for i in rows]})}
  self.assertEqual(evidence_packet(self.w,manifest,{},model,origin_turn='s:new')['status'],'processing_pending');self.assertEqual(calls,['1'])

 def test_three_turn_ancestry_known_failure_recovery_and_unknown_denial(self):
  from hermes_attention.dloa_synthesis import diagnose_extraction,acknowledge_extraction
  database=Path(self.tmp.name)/'absent.sqlite';session='jarvis_chain'
  failure={'success':False,'error_class':'IncompleteOutput','response_received':True,'usage_known':True,'input_tokens':1,'output_tokens':8192,'estimated_cost_usd':0.01}
  def bind(turn,parent=None):
   state=self.w._read();state.setdefault('native_turns',{})[session+':'+turn]={'manifest_id':'same',**({'recovery_of':session+':'+parent} if parent else {})};self.w._save(state)
  bind('a');evidence_packet(self.w,self.manifest,self.packet,lambda p:failure,origin_turn=session+':a')
  a=diagnose_extraction(self.w,database,session,'a')['batches'][0]['batchId'];bind('b','a');acknowledge_extraction(self.w,database,session,'a','b',a)
  evidence_packet(self.w,self.manifest,self.packet,lambda p:failure,origin_turn=session+':b')
  b=next(k for k,v in self.w._read()['extraction_attempts'].items() if v['origin_turn']==session+':b')
  bind('c','b');acknowledge_extraction(self.w,database,session,'b','c',b)
  blocked=evidence_packet(self.w,self.manifest,self.packet,self.model,origin_turn=session+':c');self.assertEqual(blocked['status'],'uncertain');self.assertEqual(self.calls,[])
  diagnosis=diagnose_extraction(self.w,database,session,'c');self.assertTrue(diagnosis['eligible']);self.assertEqual(diagnosis['lineageTurnIds'],['c','b','a']);self.assertEqual({x['actualFailedTurnId'] for x in diagnosis['batches']},{'a','b'})
  baseline=self.w._read();state=self.w._read();state['extraction_attempts']['unknown']={'origin_turn':session+':a','status':'running','keys':['unknown']};self.w._save(state)
  self.assertFalse(diagnose_extraction(self.w,database,session,'c')['eligible']);self.w._save(baseline)
  state=self.w._read();state['synthesis_attempts']={session+':a':{'status':'running'}};self.w._save(state)
  self.assertFalse(diagnose_extraction(self.w,database,session,'c')['eligible']);self.w._save(baseline)
  bind('d','c')
  for batch in diagnosis['batches']:acknowledge_extraction(self.w,database,session,'c','d',batch['batchId'])
  bind('competitor','c')
  with self.assertRaises(PermissionError):acknowledge_extraction(self.w,database,session,'c','competitor',a)
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,self.model,origin_turn=session+':d',max_batches=100)['status'],'completed')
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,self.model,origin_turn=session+':c')['status'],'uncertain')
  self.assertEqual(self.w._read()['extraction_attempts'][a],baseline['extraction_attempts'][a])

 def test_exact_known_failure_ack_new_turn_only_preserves_old_attempt(self):
  from hermes_attention.dloa_synthesis import diagnose_extraction,acknowledge_extraction
  response={'success':False,'error_class':'IncompleteOutput','response_received':True,'usage_known':True,'input_tokens':50,'output_tokens':8192,'estimated_cost_usd':0.03,'text':'partial'}
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,lambda p:response,origin_turn='jarvis_test:old')['status'],'uncertain')
  diagnosis=diagnose_extraction(self.w,Path(self.tmp.name)/'absent.sqlite','jarvis_test','old');self.assertTrue(diagnosis['eligible']);bid=diagnosis['batches'][0]['batchId']
  state=self.w._read();old_attempt=json.loads(json.dumps(state['extraction_attempts'][bid]));state['native_turns']={'jarvis_test:old':{'manifest_id':'same'},'jarvis_test:new':{'manifest_id':'same','recovery_of':'jarvis_test:old'}};self.w._save(state)
  with self.assertRaises(PermissionError):acknowledge_extraction(self.w,Path(self.tmp.name)/'absent.sqlite','jarvis_test','old','old',bid)
  first=acknowledge_extraction(self.w,Path(self.tmp.name)/'absent.sqlite','jarvis_test','old','new',bid)
  self.assertEqual(first['status'],'acknowledged')
  # A crash before dispatch can safely resume exact setup, with no model call.
  self.w=DloaWorkspace(self.w.root)
  diagnosis=diagnose_extraction(self.w,Path(self.tmp.name)/'absent.sqlite','jarvis_test','old')
  self.assertTrue(diagnosis['eligible']);self.assertEqual(diagnosis['batches'][0]['acknowledgedNewTurnId'],'new')
  self.assertEqual(first,acknowledge_extraction(self.w,Path(self.tmp.name)/'absent.sqlite','jarvis_test','old','new',bid))
  state=self.w._read();state['native_turns']['jarvis_test:competing']={'manifest_id':'same','recovery_of':'jarvis_test:old'};self.w._save(state)
  with self.assertRaisesRegex(PermissionError,'another recovery turn'):
   acknowledge_extraction(self.w,Path(self.tmp.name)/'absent.sqlite','jarvis_test','old','competing',bid)
  self.assertEqual(len(self.w._read()['extraction_recoveries']),1)
  result=evidence_packet(self.w,self.manifest,self.packet,self.model,origin_turn='jarvis_test:new',max_batches=100);self.assertEqual(result['status'],'completed')
  self.assertEqual(self.w._read()['extraction_attempts'][bid],old_attempt)
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,self.model,origin_turn='jarvis_test:old')['status'],'uncertain')
 def test_legacy_unique_receipt_required_and_ambiguity_denied(self):
  import sqlite3
  from hermes_attention.dloa_synthesis import diagnose_extraction
  database=Path(self.tmp.name).resolve()/'receipts.sqlite'
  with sqlite3.connect(database) as db:
   db.execute('CREATE TABLE model_attempts(attempt_id,feature,provider,model,usage_known,status,created_at)')
   db.execute('CREATE TABLE usage_events(event_id,feature,provider,model,success,input_tokens,output_tokens,cost_usd,occurred_at)')
   db.execute("INSERT INTO model_attempts VALUES('m1','dloa-synthesis','test','model',1,'IncompleteOutput','2026-09-05T10:01:00+00:00')")
   db.execute("INSERT INTO usage_events VALUES(1,'dloa-synthesis','test','model',0,100,8192,0.1,'2026-09-05T10:01:00+00:00')")
  state=self.w._read();state['extraction_attempts']={'batch':{'origin_turn':'jarvis_test:old','status':'uncertain','started_at':'2026-09-05T10:00:00+00:00','usage':{'input_tokens':100,'output_tokens':8192,'estimated_cost_usd':0.1,'usage_known':True}}};self.w._save(state)
  result=diagnose_extraction(self.w,database,'jarvis_test','old');self.assertTrue(result['eligible']);self.assertEqual(result['batches'][0]['modelAttemptId'],'m1')
  with sqlite3.connect(database) as db:db.execute("INSERT INTO usage_events VALUES(2,'dloa-synthesis','test','model',0,100,8192,0.1,'2026-09-05T10:01:00+00:00')")
  self.assertFalse(diagnose_extraction(self.w,database,'jarvis_test','old')['eligible'])

 def test_timeout_diagnosis_never_eligible(self):
  from hermes_attention.dloa_synthesis import diagnose_extraction
  evidence_packet(self.w,self.manifest,self.packet,lambda p:{'success':False,'error_class':'TimeoutError','usage_known':False},origin_turn='jarvis_test:old')
  self.assertFalse(diagnose_extraction(self.w,Path(self.tmp.name)/'absent.sqlite','jarvis_test','old')['eligible'])

 def test_many_small_items_bound_response_cardinality(self):
  items=[{'evidence_id':str(i),'text':'Small work evidence','sha256':str(i),'actor_state':'owner'} for i in range(46)]
  manifest={**self.manifest,'sources':[{'items':items}]}
  result=evidence_packet(self.w,manifest,self.packet,self.model)
  self.assertEqual(result['status'],'processing_pending');self.assertEqual(result['completedChunks'],8)
  self.assertEqual(len(self.calls[0]),8)
 def test_incomplete_output_preserves_private_diagnostics_without_retry(self):
  response={'success':False,'error_class':'IncompleteOutput','response_received':True,'text':'{"items": [partial','input_tokens':100,'output_tokens':8192,'estimated_cost_usd':0.02,'usage_known':True}
  result=evidence_packet(self.w,self.manifest,self.packet,lambda p:response)
  self.assertEqual(result['status'],'uncertain')
  attempt=next(iter(self.w._read()['extraction_attempts'].values()))
  self.assertEqual(attempt['model_error_class'],'IncompleteOutput');self.assertEqual(attempt['failed_response_text'],response['text'])
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,lambda p:self.fail('must not auto retry'))['status'],'uncertain')

 def test_current_turn_usage_excludes_historical_cache_and_unknown_total(self):
  from hermes_attention.dloa_synthesis import current_turn_usage
  state=self.w._read();state['extraction_attempts']={
   'old':{'origin_turn':'old','usage':{'input_tokens':900,'output_tokens':900,'estimated_cost_usd':9,'usage_known':True}},
   'new':{'origin_turn':'current','usage':{'input_tokens':100,'output_tokens':20,'estimated_cost_usd':0.2,'usage_known':True}}}
  self.w._save(state)
  result=current_turn_usage(self.w,'current',{'input_tokens':50,'output_tokens':10,'estimated_cost_usd':0.1,'usage_known':True})
  self.assertEqual(result['totalUsage'],{'input_tokens':150,'output_tokens':30});self.assertAlmostEqual(result['totalCostUsd'],0.3)
  result=current_turn_usage(self.w,'current',{'success':False,'usage_known':False,'estimated_cost_usd':None})
  self.assertIsNone(result['totalCostUsd']);self.assertEqual(result['knownCostSubtotalUsd'],0.2);self.assertFalse(result['totalUsageKnown'])

 def test_same_bytes_corrected_actor_invalidates_owner_cache(self):
  original=evidence_packet(self.w,self.manifest,self.packet,self.model,max_batches=100)
  self.assertEqual(original['status'],'completed');count=len(self.calls)
  self.items[-1]['actor_state']='other';self.items[-1]['actor_id']='corrected-colleague'
  def corrected(prompt):
   value=self.model(prompt);parsed=json.loads(value['text'])
   for row in parsed['items']:
    for fact in row['facts']:fact['attribution']='other'
   value['text']=json.dumps(parsed);return value
  result=evidence_packet(self.w,self.manifest,self.packet,corrected,max_batches=100)
  self.assertEqual(result['status'],'completed');self.assertEqual(len(self.calls),count+1)
  self.assertEqual(self.calls[-1],['3'])
  self.assertEqual(result['packet']['evidence'][-1]['validated_extraction']['facts'][0]['attribution'],'other')
  # Cached corruption cannot bypass the current actor guard.
  state=self.w._read()
  for cached in state['extraction_cache'].values():
   if cached['evidence_id']=='3':cached['facts'][0]['attribution']='owner'
  self.w._save(state)
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,corrected)['status'],'uncertain')

 def test_one_batch_per_invocation_progress_and_separate_finalization(self):
  tokens=[]
  for expected in range(1,5):
   result=evidence_packet(self.w,self.manifest,self.packet,self.model)
   self.assertEqual(result['status'],'processing_pending');self.assertEqual(len(self.calls),expected)
   self.assertEqual(result['completedChunks'],expected);tokens.append(result['progressToken'])
  self.assertEqual(len(set(tokens)),4)
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,self.model)['status'],'completed')
  self.assertEqual(len(self.calls),4)

 def test_tail_fact_and_revision_use_every_chunk_once(self):
  out=evidence_packet(self.w,self.manifest,self.packet,self.model,max_batches=100)
  self.assertEqual(out['status'],'completed');self.assertEqual(out['packet']['omitted_evidence_ids'],[])
  self.assertEqual(out['packet']['evidence'][-1]['validated_extraction']['facts'][0]['text'],'Delivered workbook')
  self.assertEqual(sorted(sum(self.calls,[])),['0','1','2','3']);count=len(self.calls)
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,self.model,max_batches=100),out);self.assertEqual(len(self.calls),count)
 def test_cancel_after_committed_batch_resume_skips_it(self):
  result=evidence_packet(self.w,self.manifest,self.packet,self.model,max_batches=100,cancelled=lambda:bool(self.calls))
  self.assertEqual(result['status'],'cancelled');self.assertEqual(len(self.calls),1)
  self.w=DloaWorkspace(self.w.root)
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,self.model,max_batches=100)['status'],'completed')
  self.assertEqual(sorted(sum(self.calls,[])),['0','1','2','3'])
 def test_uncertain_batch_never_rebilled_and_bad_quote_denied(self):
  def invalid(prompt):
   value=self.model(prompt);data=json.loads(value['text']);data['items'][0]['facts']=[{'text':'Fake','quote':'invented quote','attribution':'owner'}];value['text']=json.dumps(data);return value
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,invalid)['status'],'uncertain');count=len(self.calls)
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,self.model,max_batches=100)['status'],'uncertain');self.assertEqual(len(self.calls),count)
 def test_missing_chunk_entry_cannot_claim_completed(self):
  self.assertEqual(evidence_packet(self.w,self.manifest,self.packet,lambda p:{'success':True,'text':'{"items":[]}'})['status'],'uncertain')
if __name__=='__main__':unittest.main()
