import hashlib,json,unittest
from hermes_attention.dloa_synthesis import _item_keys
from hermes_attention.dloa_report import catalogue,render_selection,coverage_status

class ReportGroundingTest(unittest.TestCase):
 def fixture(self):
  items=[{'evidence_id':'prior','text':'DLOA - Thursday, 3 September 2026\nAttended old meeting','sha256':'prior','actor_state':'owner','source':'slack','occurred_at':'2026-09-04T13:00:00+00:00','source_ref':'https://example.com/prior'}, {'evidence_id':'current','text':'speaker says hello','sha256':'current','actor_state':'uncertain','source':'zoom','occurred_at':'2026-09-04T15:00:00+00:00','source_ref':'https://example.com/meeting'}]
  manifest={'window':{'report_date':'2026-09-04','start':'2026-09-04T12:30:00+00:00','timezone':'America/New_York','end':'2026-09-05T12:30:00+00:00'},'skill':{'text':'Use meetings first, section bullets, citations outside code block.'},'sources':[{'source':'slack','status':'partial','items':items,'limitations':['author unverified']} ]};keys=_item_keys(manifest,items)
  state={'extraction_cache':{keys[i['evidence_id']]:{'facts':[{'text':'Attended old meeting' if n==0 else 'Syed discussed Project Brain','quote':i['text'],'attribution':'owner' if n==0 else 'uncertain'}]} for n,i in enumerate(items)}}
  return state,manifest
 def test_old_report_posted_today_and_uncertain_attendance_cannot_be_owner(self):
  state,m=self.fixture();before=json.dumps(state,sort_keys=True);facts=list(catalogue(state,m).values());self.assertEqual(facts[0]['temporal_role'],'background')
  for fact in facts:
   with self.assertRaises(ValueError):render_selection({'sections':[{'section':'Meetings','fact_ids':[fact['fact_id']]}],'context_fact_ids':[]},state,m)
  text=render_selection({'sections':[],'context_fact_ids':[f['fact_id'] for f in facts]},state,m)
  self.assertIn('['+facts[0]['fact_id']+']',text);self.assertIn('Scope:',text)
  self.assertIn('Friday, 4 September 2026',text);self.assertIn('Prior-period background',text);self.assertIn('Syed discussed Project Brain',text);self.assertIn('https://example.com/meeting',text);self.assertEqual(json.dumps(state,sort_keys=True),before)
  for selection in [{'sections':[],'context_fact_ids':['madeup']},{'sections':[],'context_fact_ids':[facts[0]['fact_id']]*2},{'sections':[],'context_fact_ids':[],'text':'I attended'}]:
   with self.assertRaises(ValueError):render_selection(selection,state,m)
 def test_placement_normalization_preserves_context_and_rejects_invalid_ids(self):
  from hermes_attention.dloa_report import normalize_placement
  state,m=self.fixture();before=json.dumps(state,sort_keys=True);ids=list(catalogue(state,m))
  original={'sections':[{'section':'Meetings','fact_ids':ids}],'context_fact_ids':[]}
  selected,audit=normalize_placement(original,state,m)
  self.assertEqual(audit['movedCount'],2);self.assertEqual(selected['context_fact_ids'],ids);self.assertEqual(original['sections'][0]['fact_ids'],ids)
  self.assertEqual(json.dumps(state,sort_keys=True),before);self.assertIn('Prior-period background',render_selection(selected,state,m))
  for bad in [ids+[ids[0]],ids+['unknown']]:
   with self.assertRaises(ValueError):normalize_placement({'sections':[{'section':'Meetings','fact_ids':bad}],'context_fact_ids':[]},state,m)

 def test_asset_gaps_resolved_only_with_contiguous_complete_ranges(self):
  original={'text':'Metadata text must not fill asset gaps.\nAuthorized meeting assets (source data):\nabc','provenance':{'asset_truncated':False,'asset_total_characters':6,'asset_full_sha256':hashlib.sha256(b'abcdef').hexdigest(),'meeting_id':'m'}}
  chunk={'text':'def','provenance':{'asset_chunk':True,'asset_start':3,'asset_end':6,'asset_full_sha256':hashlib.sha256(b'abcdef').hexdigest(),'meeting_id':'m'}}
  source={'source':'zoom','status':'partial','items':[original,chunk],'cursor_after':None,'pending_assets':0,'limitations':['Cached meeting asset extraction is truncated; remaining linked content is not yet covered','Page bound reached; remaining coverage omitted','Meeting metadata is not proof of owner attendance']}
  m={'sources':[source]};effective=coverage_status(m)[0];self.assertEqual(effective['status'],'partial');self.assertFalse(any('truncated' in l for l in effective['limitations']));self.assertIn('Meeting metadata is not proof of owner attendance',effective['limitations'])
  source['has_more']=True;self.assertIn('Page bound reached; remaining coverage omitted',coverage_status(m)[0]['limitations']);source['items'][1]['provenance']['asset_start']=4;self.assertTrue(any('truncated' in l for l in coverage_status(m)[0]['limitations']))

 def test_exact_window_override_and_next_morning_event(self):
  from hermes_attention.dloa_report import _temporal
  window={'report_date':'2026-09-04','start':'2026-09-03T12:30:00+00:00','end':'2026-09-05T12:30:00+00:00','timezone':'America/New_York'}
  self.assertEqual(_temporal({'text':'DLOA - Thursday, 3 September 2026'},window)[0],'current')
  self.assertEqual(_temporal({'source':'zoom','occurred_at':'2026-09-05T11:30:00+00:00'},window)[0],'current')
  self.assertEqual(_temporal({'source':'zoom','occurred_at':'2026-09-05T12:30:00+00:00'},window)[0],'background')
  self.assertEqual(_temporal({'event_date':'2026-09-05'},window)[0],'overlapping-date-only')

 def test_section_names_come_from_trusted_skill_and_config(self):
  from hermes_attention.dloa_report import allowed_sections
  state,m=self.fixture();m['skill']['text']='Use _New Project_ and _Meetings_.'
  self.assertIn('New Project',allowed_sections(m));self.assertNotIn('LegalCurrentHQ Publishing',allowed_sections(m))

 def test_style_revision_prior_context_and_review_receipts(self):
  import tempfile
  from pathlib import Path
  from hermes_attention.dloa import DloaWorkspace
  from hermes_attention.dloa_report import selection_packet,review_rewrites
  from hermes_attention.dloa_synthesis import current_turn_usage
  state,m=self.fixture();facts=list(catalogue(state,m).values());identity=facts[1]['fact_id'];selection={'sections':[],'context_fact_ids':[identity],'rewrites':[{'fact_id':identity,'text':'Syed discussed the Project Brain concept.'}]}
  previous={'text':'Prior third bullet','selection_provenance':{'context_fact_ids':[identity]}}
  self.assertEqual(selection_packet(state,m,'Polish third bullet',previous)['previous_report'],previous)
  with tempfile.TemporaryDirectory() as tmp:
   w=DloaWorkspace(Path(tmp).resolve());calls=[]
   def reviewer(prompt):
    calls.append(prompt);return {'success':True,'text':json.dumps({'verdicts':[{'fact_id':identity,'approved':True}]}),'input_tokens':20,'output_tokens':5,'estimated_cost_usd':.01,'usage_known':True}
   approved,result=review_rewrites(w,'s:turn',selection,state,m,reviewer)
   text=render_selection(selection,state,m,approved);self.assertIn('Syed discussed the Project Brain concept.',text);self.assertIn('Contextual source statement',text)
   self.assertEqual(review_rewrites(w,'s:turn',selection,state,m,lambda p:self.fail('No replay'))[0],approved)
   usage=current_turn_usage(w,'s:turn',{'input_tokens':10,'output_tokens':2,'estimated_cost_usd':.02,'usage_known':True});self.assertEqual(usage['currentTurnModelCalls'],2);self.assertAlmostEqual(usage['totalCostUsd'],.03)
   rejected,_=review_rewrites(w,'s:reject',selection,state,m,lambda p:{'success':True,'text':json.dumps({'verdicts':[{'fact_id':identity,'approved':False}]})});self.assertEqual(rejected,{})
   self.assertIn('Syed discussed Project Brain',render_selection(selection,state,m,rejected))
   unknown,_=review_rewrites(w,'s:unknown',selection,state,m,lambda p:(_ for _ in ()).throw(TimeoutError()))
   self.assertEqual(unknown,{});self.assertFalse(current_turn_usage(w,'s:unknown',{'input_tokens':10,'output_tokens':2,'estimated_cost_usd':.02,'usage_known':True})['totalCostKnown'])
 def test_grouped_revision_shared_review_all_quotes_citations_and_fallback(self):
  import tempfile
  from pathlib import Path
  from hermes_attention.dloa import DloaWorkspace
  from hermes_attention.dloa_report import review_rewrites,selection_packet
  state,m=self.fixture();cache=list(state['extraction_cache'].values())[1]
  cache['facts'].append({'text':'Syed suggested a content test','quote':'speaker says hello','attribution':'uncertain'})
  facts=catalogue(state,m);ids=[i for i,f in facts.items() if f['temporal_role']=='current'];self.assertEqual(len(ids),2)
  selection={'sections':[],'context_fact_ids':ids,'groups':[{'fact_ids':ids,'text':'Syed discussed Project Brain and suggested a content test.'}]}
  original=render_selection(selection,state,m);self.assertEqual(original.count('Contextual source statement;'),2)
  packet=selection_packet(state,m,'Use two topics and preserve collective we',previous_report={'text':'Long prior report','selection_provenance':selection})
  self.assertIn('latest owner_request',' '.join(packet['rules']));self.assertNotIn('No generated factual prose',' '.join(packet['rules']))
  with tempfile.TemporaryDirectory() as t:
   w=DloaWorkspace(Path(t).resolve());calls=[]
   def review(prompt):
    data=json.loads(prompt.split('\n',1)[1]);calls.append(data);self.assertEqual(len(data[0]['supporting_facts']),2)
    return {'success':True,'text':json.dumps({'verdicts':[{'fact_id':data[0]['fact_id'],'approved':True}]}),'usage_known':True,'input_tokens':20,'output_tokens':5,'estimated_cost_usd':.01}
   approved,result=review_rewrites(w,'s:group',selection,state,m,review)
   text=render_selection(selection,state,m,approved);self.assertEqual(text.count('Contextual source statement;'),1)
   for identity in ids:self.assertIn('['+identity+']',text);self.assertIn('• '+identity+':',text)
   self.assertEqual(len(calls),1);self.assertEqual(result['approvedCount'],1)
   denied,_=review_rewrites(w,'s:deniedgroup',selection,state,m,lambda p:{'success':True,'text':json.dumps({'verdicts':[{'fact_id':calls[0][0]['fact_id'],'approved':False}]})})
   self.assertEqual(render_selection(selection,state,m,denied),original)
  prior=next(i for i in facts if i not in ids)
  for bad in [[ids[0],ids[0]],[ids[0],'invented'],[ids[0],prior]]:
   with self.assertRaises(ValueError):render_selection({'sections':[],'context_fact_ids':list(facts),'groups':[{'fact_ids':bad,'text':'Unsupported mix'}]},state,m)

 def test_reviewer_prioritizes_exact_quote_over_derived_pronoun(self):
  import tempfile
  from pathlib import Path
  from hermes_attention.dloa import DloaWorkspace
  from hermes_attention.dloa_report import review_rewrites
  state,m=self.fixture();fact=list(state['extraction_cache'].values())[1]['facts'][0]
  fact.update(text='They will be charged tomorrow',quote='we will be charged tomorrow')
  identity=next(i for i,f in catalogue(state,m).items() if f['temporal_role']=='current')
  selection={'sections':[],'context_fact_ids':[identity],'rewrites':[{'fact_id':identity,'text':'The message says we will be charged tomorrow.'}]}
  with tempfile.TemporaryDirectory() as t:
   workspace=DloaWorkspace(Path(t).resolve())
   def reviewer(prompt):
    self.assertIn('Exact source quotations take precedence',prompt);self.assertIn('Do not infer identities',prompt)
    row=json.loads(prompt.split('\n',1)[1])[0];self.assertEqual(row['original'],'They will be charged tomorrow');self.assertEqual(row['source_quote'],'we will be charged tomorrow')
    return {'success':True,'text':json.dumps({'verdicts':[{'fact_id':identity,'approved':True}]})}
   approved,result=review_rewrites(workspace,'s:pronoun',selection,state,m,reviewer)
   self.assertEqual(approved[identity],selection['rewrites'][0]['text']);self.assertEqual(result['status'],'model_checked')
 def test_selector_exact_quotes_compact_prior_and_current_instruction_last(self):
  from hermes_attention.dloa_report import selection_packet,selection_prompt
  state,m=self.fixture();cache=list(state['extraction_cache'].values())[1]
  cache['facts']=[{'text':'They will be charged','quote':'do this before Monday or we will be charged','attribution':'uncertain'},{'text':'Reminder repeated','quote':'do this before Monday or we will be charged','attribution':'uncertain'}]
  before=json.dumps(state,sort_keys=True);request='Keep the collective wording. Omit prior-period background from the displayed draft.'
  prior={'text':'Earlier report','selection_provenance':{'context_fact_ids':['old']},'usage':{'private_telemetry':True},'previous_report':{'text':'Nested old report'}}
  packet=selection_packet(state,m,request,prior);facts=catalogue(state,m)
  self.assertEqual(packet['previous_report'],{'text':'Earlier report','selection_provenance':prior['selection_provenance']})
  self.assertEqual(len(packet['source_quotes']),2)
  for fact in packet['facts']:
   self.assertEqual(packet['source_quotes'][fact['quote_ref']],facts[fact['fact_id']]['retained_quote'])
  prompt=selection_prompt(packet);self.assertTrue(prompt.endswith(request));self.assertNotIn('private_telemetry',prompt)
  self.assertIn('Select ONLY fact IDs present in the current facts catalogue',prompt);self.assertIn('never copy obsolete IDs',prompt);self.assertIn('Preserve speech acts as speech',prompt);self.assertIn('all unselected source evidence remains retained',prompt)
  self.assertEqual(json.dumps(state,sort_keys=True),before)
 def test_refresh_footer_counts_records_not_work(self):
  state,m=self.fixture();m.update(previous_id='older',delta={'added':['a'],'changed':['b','c'],'not_seen_on_refresh':['d']})
  text=render_selection({'sections':[],'context_fact_ids':[]},state,m)
  self.assertIn('1 added, 2 changed, 1 not seen',text);self.assertIn('not proven new work',text);self.assertIn('not freshly confirmed',text)
  del m['previous_id'];self.assertNotIn('Refresh source-record changes',render_selection({'sections':[],'context_fact_ids':[]},state,m))

class PresentationContractTest(unittest.TestCase):
 def test_counts_exclusions_and_lossless_packet(self):
  from hermes_attention.dloa_report import presentation_contract,validate_presentation,selection_packet
  for request in ['Keep five owner bullets and two focused meeting context items, no prior background.', 'Use exactly 5 main bullet points; use 2 meeting context groups without prior-period background.']:
   self.assertEqual(presentation_contract(request),{'owner_bullets':5,'context_bullets':2,'exclude_background':True})
  self.assertEqual(presentation_contract('After refresh change the count to three owner bullets')['owner_bullets'],3)
  self.assertEqual(presentation_contract('Keep five work-related communication bullets and two focused meeting context items'),{'owner_bullets':5,'context_bullets':2})
  self.assertEqual(presentation_contract('Use 5 verified work related communication facts')['owner_facts'],5)
  self.assertEqual(presentation_contract('Keep five verified communication facts and two focused meeting-context bullets; keep prior-period background out of the displayed report'),{'owner_facts':5,'context_bullets':2,'exclude_background':True})
  state,m=ReportGroundingTest().fixture();entries=catalogue(state,m);ids=list(entries)
  selected={'sections':[],'context_fact_ids':ids}
  check=validate_presentation(selected,state,m,{},'Keep five owner bullets and no prior background')
  self.assertEqual(check['status'],'not_met');self.assertEqual(len(check['issues']),2)
  packet=selection_packet(state,m,'Keep two meeting context items')
  for fact in packet['facts']:
   expanded={**fact,**packet['source_records'][fact['source_ref']],'retained_quote':packet['source_quotes'][fact['quote_ref']]}
   expanded.pop('source_ref');expanded.pop('quote_ref')
   self.assertEqual(expanded,entries[fact['fact_id']])

class RevisionHistoryHoldout(unittest.TestCase):
 def test_prior_versions_remain_context_without_cross_conversation_leak(self):
  from hermes_attention.dloa_report import selection_packet,presentation_contract
  state,m=ReportGroundingTest().fixture()
  m['conversation_id']='work-thread'
  state['reports']={'earlier':{'id':'earlier','conversation_id':'work-thread','created_at':'1','version':4,'text':'Retained work communication\nSource coverage and limitations\nOld status'},'latest':{'id':'latest','conversation_id':'work-thread','created_at':'2','version':5,'text':'Latest'},'private':{'id':'private','conversation_id':'personal-thread','created_at':'3','text':'PRIVATE-HOLDOUT'}}
  packet=selection_packet(state,m,'Restore five owner bullets; exclude prior-window background',state['reports']['latest'])
  self.assertEqual([r['version'] for r in packet['revision_history']],[4])
  self.assertNotIn('PRIVATE-HOLDOUT',json.dumps(packet))
  self.assertNotIn('Old status',json.dumps(packet['revision_history']))
  self.assertTrue(presentation_contract(packet['owner_request'])['exclude_background'])
