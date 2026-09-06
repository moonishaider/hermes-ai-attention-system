import asyncio,json,copy,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone,timedelta
from hermes_attention.storage import Store
from hermes_attention.domain import EvidenceItem,Provenance,ContextLabel
from hermes_attention.work_ledger import WorkLedger
from hermes_attention.awareness_runtime import AwarenessRuntime
from hermes_attention.dloa import SourcePlan,SourcePage

class AwarenessRuntimeTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
  self.store=Store(':memory:');self.addCleanup(self.store.close);self.now=datetime(2026,9,5,18,tzinfo=timezone.utc)
  self.content='[00:10] Tyler: Sid, please review the workbook tomorrow.\n[00:20] Sid: Yes, I will check the formulas.\n[00:30] Tyler: We agreed to retain the existing report boundary.'
  self.store.add_evidence(EvidenceItem('meeting','Synthetic meeting',self.content,Provenance('uploaded-transcript','owner-upload','fixture','2026-09-04T15:00:00Z','2026-09-05T18:00:00Z',account_id='owner'),(ContextLabel('inside-success',1,'fixture','1'),)))
  self.ingests=[]
  def ingest(**kwargs):self.ingests.append(kwargs);return {'evidence_id':'saved-fixture'}
  self.service=SimpleNamespace(store=self.store,paths=SimpleNamespace(runtime_dir=self.root,config_dir=self.root),ledger=WorkLedger(self.store),ingest_evidence=ingest)
  self.output={'summary':[{'text':'The report boundary was retained.','quote':'[00:30] Tyler: We agreed to retain the existing report boundary.'}],'items':[{'kind':'task','title':'Review workbook formulas','quote':'[00:20] Sid: Yes, I will check the formulas.','speaker':'Sid','speakerQuote':'[00:20] Sid: Yes, I will check the formulas.','assignee':'Sid','assigneeQuote':'[00:10] Tyler: Sid, please review the workbook tomorrow.'},{'kind':'decision','title':'Retain report boundary','quote':'[00:30] Tyler: We agreed to retain the existing report boundary.','speaker':'Tyler','speakerQuote':'[00:30] Tyler: We agreed to retain the existing report boundary.','assignee':'unknown'}]}
  self.calls=[]
  self.runtime=AwarenessRuntime(self.service,clock=lambda:self.now,model=lambda prompt:self.calls.append(prompt) or copy.deepcopy(self.output))
  self.hash=self.runtime.workspace.source('meeting')['content_hash']
 def test_semantic_quotes_offsets_and_explicit_review_dedupe(self):
  out=self.runtime.meeting_analyze('meeting',self.hash);self.assertEqual(len(out['candidates']),2)
  for x in out['candidates']:
   c=x['citation'];self.assertEqual(self.content[c['start']:c['end']],c['quote'])
  self.assertTrue(self.runtime.meeting_analyze('meeting',self.hash)['cacheHit']);self.assertEqual(len(self.calls),1)
  request={'analysisId':out['analysisId'],'context':'inside-success','confirmed':True,'selected':[{'candidateId':x['candidate_id'],'owner':'Sid' if x['kind']=='task' else 'Tyler'} for x in out['candidates']]}
  result=self.runtime.meeting_commit(request);self.assertEqual(result,self.runtime.meeting_commit(request));self.assertFalse(result['completionClaimed'])
  self.assertEqual(self.store.connection.execute('SELECT status FROM tasks').fetchone()[0],'open')
  with self.assertRaises(PermissionError):self.runtime.meeting_commit({**request,'confirmed':False})
  with self.assertRaises(PermissionError):self.runtime.meeting_commit({**request,'context':'personal'})
 def test_source_linked_project_checkpoint_resume_and_followup(self):
  analysis=self.runtime.meeting_analyze('meeting',self.hash)
  project=self.runtime.workspace.project_create({'requestId':'source-linked-project','context':'inside-success','name':'Synthetic workbook','objective':'Review source-linked formulas','evidenceIds':['meeting']})['projectId']
  request={'analysisId':analysis['analysisId'],'context':'inside-success','projectId':project,'confirmed':True,'selected':[{'candidateId':x['candidate_id'],'owner':'Sid' if x['kind']=='task' else 'Tyler'} for x in analysis['candidates']]}
  self.runtime.meeting_commit(request);self.runtime.meeting_commit(request)
  resumed=self.runtime.workspace.resume(project)
  checkpoint=resumed['checkpoint']['state'];self.assertEqual(checkpoint['state'],'source-linked meeting checkpoint')
  self.assertEqual(checkpoint['source']['source_timestamp'],'2026-09-04T15:00:00Z')
  self.assertFalse(checkpoint['completed']);task=resumed['linked_tasks'][0]
  self.assertEqual(task['owner'],'Sid');self.assertEqual(task['evidence_ids'],['meeting'])
  self.runtime.workspace.transition({'taskId':task['task_id'],'expectedVersion':task['version'],'action':'done'})
  current=self.runtime.workspace.resume(project)['linked_tasks'][0]
  self.assertEqual(current['status'],'done');self.assertEqual(current['review']['completion'],'owner-confirmed')
  self.assertEqual(self.runtime.workspace.resume(project)['checkpoint']['state'],checkpoint)
  self.assertEqual(self.store.connection.execute("SELECT count(*) FROM project_snapshots WHERE snapshot_id LIKE 'meeting-checkpoint:%'").fetchone()[0],1)

 def test_unknown_source_project_lifecycle_preserves_context_owner_and_evidence(self):
  self.store.add_evidence(EvidenceItem('unknown-meeting','Unclassified synthetic transcript',self.content,Provenance('uploaded-transcript','owner-upload','unknown-fixture','2026-09-04T15:00:00Z','2026-09-05T18:00:00Z',account_id='owner'),(ContextLabel('unknown',1,'fixture','1'),)))
  original=self.runtime.workspace.source('unknown-meeting')
  analysis=self.runtime.meeting_analyze('unknown-meeting',original['content_hash'])
  creation={'requestId':'unknown-source-project','context':'unknown','name':'Unclassified follow-ups','objective':'Review source without guessing company','evidenceIds':['unknown-meeting']}
  project=self.runtime.workspace.project_create(creation)['projectId']
  self.assertFalse(self.runtime.workspace.project_create(creation)['created'])
  task_candidate=next(x for x in analysis['candidates'] if x['kind']=='task')
  request={'analysisId':analysis['analysisId'],'context':'unknown','projectId':project,'confirmed':True,'selected':[{'candidateId':task_candidate['candidate_id'],'owner':'Sid'}]}
  with self.assertRaises(PermissionError):self.runtime.meeting_commit({**request,'context':'inside-success'})
  with self.assertRaisesRegex(ValueError,'context mismatch'):self.runtime.workspace.project_create({**creation,'requestId':'wrong-source-context','context':'personal'})
  self.runtime.meeting_commit(request);self.runtime.meeting_commit(request)
  resumed=self.runtime.workspace.resume(project);task=resumed['linked_tasks'][0];checkpoint=resumed['checkpoint']['state']
  self.assertEqual(resumed['project']['context_id'],'unknown');self.assertEqual(task['context_id'],'unknown');self.assertEqual(task['owner'],'Sid');self.assertEqual(task['evidence_ids'],['unknown-meeting'])
  self.assertEqual(checkpoint['source'],original);self.assertFalse(checkpoint['completed'])
  self.runtime.workspace.transition({'taskId':task['task_id'],'expectedVersion':task['version'],'action':'done'})
  reopened=AwarenessRuntime(self.service,clock=lambda:self.now).workspace.resume(project)
  self.assertEqual(reopened['linked_tasks'][0]['status'],'done');self.assertEqual(reopened['linked_tasks'][0]['review']['completion'],'owner-confirmed')
  self.assertEqual(reopened['checkpoint']['state'],checkpoint);self.assertEqual(self.runtime.workspace.source('unknown-meeting'),original)
  self.assertEqual(self.store.connection.execute("SELECT count(*) FROM project_snapshots WHERE snapshot_id LIKE 'meeting-checkpoint:%'").fetchone()[0],1)

 def test_role_quote_contract_preserves_strict_attribution_guard(self):
  out=self.runtime.meeting_analyze('meeting',self.hash)
  self.assertIn('full transcript line including the speaker name',self.calls[0])
  self.assertIn('never in decision items',self.calls[0])
  # A first-person pronoun without its identifying speaker is still rejected.
  self.store.connection.execute('DELETE FROM awareness_semantic_meetings');self.store.connection.commit()
  self.output['items'][0]['assigneeQuote']='Yes, I will check the formulas.'
  with self.assertRaisesRegex(ValueError,'literal identifying source'):
   self.runtime.meeting_analyze('meeting',self.hash)

 def test_injection_hallucinated_quotes_attribution_stale_removed_denied(self):
  self.output['items'][0]['quote']='No such source sentence'
  with self.assertRaises(ValueError):self.runtime.meeting_analyze('meeting',self.hash)
  self.output['items'][0]['quote']='[00:20] Sid: Yes, I will check the formulas.';self.output['items'][0]['assignee']='Other person'
  with self.assertRaises(ValueError):self.runtime.meeting_analyze('meeting',self.hash)
  with self.assertRaises(ValueError):self.runtime.meeting_analyze('meeting','stale')
  self.store.tombstone_evidence('meeting',reason='fixture removal')
  with self.assertRaises(ValueError):self.runtime.meeting_analyze('meeting',self.hash)
 def test_uploaded_transcript_current_conversation_and_retention(self):
  from hermes_attention.documents import DocumentWorkspace
  docs=DocumentWorkspace(self.root/'documents');attachment=docs.ingest_bytes(self.content.encode(),name='transcript.txt',conversation_id='jarvis_fixture')
  docs.extract(attachment['id'],'jarvis_fixture')
  def ingest(**kw):
   p=Provenance(**kw['provenance']);eid=p.source_system+':'+p.connection_id+':'+p.source_id
   self.store.add_evidence(EvidenceItem(eid,kw['title'],kw['content'],p,(ContextLabel(kw['context_hints'][0],1,'owner selected','1'),)))
   return {'evidence_id':eid}
  self.service.ingest_evidence=ingest
  source=self.runtime.import_transcript(attachment['id'],'jarvis_fixture','inside-success',session_validator=lambda sid:None)
  again=self.runtime.import_transcript(attachment['id'],'jarvis_fixture','inside-success',session_validator=lambda sid:None);self.assertEqual(again['evidence_id'],source['evidence_id'])
  out=self.runtime.meeting_analyze(source['evidence_id'],source['content_hash']);self.assertEqual(len(out['candidates']),2)
  self.assertEqual(source['source_system'],'uploaded-transcript')
  docs.forget(attachment['id'],'jarvis_fixture')
  with self.assertRaises(ValueError):self.runtime.meeting_analyze(source['evidence_id'],source['content_hash'])
  with self.assertRaises(ValueError):self.runtime.import_transcript(attachment['id'],'different','inside-success',session_validator=lambda sid:None)

 def test_long_transcript_all_sections_keep_global_quote_offsets(self):
  text='\n'.join(f'[{i:05}] Sid: Synthetic informational sentence number {i}; no commitment is implied.' for i in range(900))
  self.store.add_evidence(EvidenceItem('long','Long fixture',text,Provenance('uploaded','fixture','long','2026-09-04T15:00:00Z','2026-09-05T18:00:00Z'),(ContextLabel('inside-success',1,'fixture','1'),)))
  calls=[]
  def model(prompt):
   calls.append(prompt);return {'summary':[{'text':'Section covered','quote':prompt.splitlines()[-1]}],'items':[]}
  self.runtime.model=model;source=self.runtime.workspace.source('long')
  result=self.runtime.meeting_analyze('long',source['content_hash'])
  self.assertGreater(result['sectionsAnalyzed'],1);self.assertEqual(len(calls),result['sectionsAnalyzed'])
  for summary in result['summary']:
   c=summary['citation'];self.assertEqual(text[c['start']:c['end']],c['quote']);self.assertEqual(c['evidence_id'],'long')
  self.assertTrue(self.runtime.meeting_analyze('long',source['content_hash'])['cacheHit']);self.assertEqual(len(calls),result['sectionsAnalyzed'])

 def test_incremental_cursor_cadence_account_provenance_no_completion(self):
  plan=SourcePlan('fixture','google_personal_calendar_readonly','personal','fixture',max_pages=1)
  self.runtime._registry=lambda:({'fixture':(plan,'personal')},{},{})
  seen=[]
  async def collector(p,w,c):
   seen.append((w.start,w.end,c));return SourcePage([{'id':'stable','text':'Mentioned work is done, but not owner confirmation','occurred_at':'2026-09-05T17:00:00Z','actor_id':'other'}],next_cursor='next' if c is None else None,exhausted=c is not None,coverage='full_declared_scope')
  self.runtime.collector_factory=lambda *args:collector
  first=asyncio.run(self.runtime.refresh());self.assertEqual(first['status'],'partial')
  self.assertEqual(asyncio.run(self.runtime.refresh())['status'],'not-due');self.assertEqual(len(seen),1)
  self.now+=timedelta(minutes=16);second=asyncio.run(self.runtime.refresh())
  self.assertEqual(second['status'],'complete');self.assertEqual(seen[1][:2],seen[0][:2]);self.assertEqual(seen[1][2],'next')
  self.assertFalse(self.ingests[0]['extract_tasks']);self.assertEqual(self.ingests[0]['provenance']['account_id'],'personal')
  self.assertEqual(self.ingests[0]['context_hints'],('personal',));self.assertEqual(self.store.connection.execute('SELECT count(*) FROM tasks').fetchone()[0],0)
  self.assertEqual(asyncio.run(self.runtime.refresh(lifecycle='off'))['status'],'off')
  with self.assertRaises(PermissionError):asyncio.run(self.runtime.refresh(source='slack_mitchell_readonly'))
 def test_concurrent_claim_and_expired_read_lease_recovery(self):
  plan=SourcePlan('fixture','source','account','fixture',max_pages=1)
  self.runtime._registry=lambda:({'fixture':(plan,'inside-success')},{},{})
  old=self.service.ledger.start_collection('awareness:fixture')
  state={'active_run':old,'lease_until':(self.now+timedelta(seconds=90)).isoformat(),'next_at':(self.now+timedelta(minutes=15)).isoformat()}
  with self.store.connection:self.store.connection.execute('INSERT INTO awareness_refresh_state VALUES(?,?,?)',('fixture',json.dumps(state),self.now.isoformat()))
  self.assertEqual(asyncio.run(self.runtime.refresh(force=True))['status'],'already-running')
  async def empty(*args):return SourcePage([],exhausted=True,coverage='full_declared_scope')
  self.runtime.collector_factory=lambda *a:empty;self.now+=timedelta(seconds=91)
  self.assertEqual(asyncio.run(self.runtime.refresh())['status'],'complete')
  self.assertEqual(self.store.connection.execute('SELECT result FROM collection_runs WHERE run_id=?',(old,)).fetchone()[0],'interrupted')

 def test_refresh_keeps_immutable_provenance_and_versions_changed_entities(self):
  plan=SourcePlan('fixture','source','account','fixture',max_pages=1)
  self.runtime._registry=lambda:({'fixture':(plan,'inside-success')},{},{})
  body=['Version one']
  async def collector(*args):return SourcePage([{'id':'same-provider-id','text':body[0],'occurred_at':'2026-09-05T17:00:00Z'}],exhausted=True,coverage='full_declared_scope')
  self.runtime.collector_factory=lambda *a:collector
  def ingest(**kw):
   p=Provenance(**kw['provenance']);eid=p.source_system+':'+p.connection_id+':'+p.source_id
   self.store.add_evidence(EvidenceItem(eid,kw['title'],kw['content'],p,(ContextLabel('inside-success',1,'fixture','1'),)))
   return {'evidence_id':eid}
  self.service.ingest_evidence=ingest
  first=asyncio.run(self.runtime.refresh());self.now+=timedelta(minutes=16)
  # Resume a same-window explicit read to exercise stable entity/retrieval clocks.
  with self.store.connection:self.store.connection.execute('DELETE FROM awareness_refresh_state')
  second=asyncio.run(self.runtime.refresh());self.assertEqual(first['evidenceIds'],second['evidenceIds'])
  body[0]='Version two';self.now+=timedelta(minutes=16)
  with self.store.connection:self.store.connection.execute('DELETE FROM awareness_refresh_state')
  third=asyncio.run(self.runtime.refresh());self.assertNotEqual(first['evidenceIds'],third['evidenceIds'])
  self.assertEqual(self.store.connection.execute("SELECT count(*) FROM evidence WHERE evidence_id LIKE 'fixture:%'").fetchone()[0],2)

 def test_provider_failure_is_not_no_change_and_backoff(self):
  plan=SourcePlan('fixture','source','account','fixture',max_pages=1)
  self.runtime._registry=lambda:({'fixture':(plan,'inside-success')},{},{})
  async def broken(*args):raise RuntimeError('provider unavailable')
  self.runtime.collector_factory=lambda *a:broken
  result=asyncio.run(self.runtime.refresh());self.assertEqual(result['status'],'failed');self.assertFalse(result['evidenceIds'])
  self.assertEqual(self.store.connection.execute('SELECT result FROM collection_runs').fetchone()[0],'failed')
  self.assertEqual(asyncio.run(self.runtime.refresh())['status'],'not-due')
if __name__=='__main__':unittest.main()
