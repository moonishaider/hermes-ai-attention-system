import unittest
from datetime import datetime,UTC,timedelta
from hermes_attention.storage import Store
from hermes_attention.domain import EvidenceItem,Provenance,ContextLabel,TaskRecord
from hermes_attention.awareness_workspace import AwarenessWorkspace

class AwarenessTests(unittest.TestCase):
 def setUp(self):
  self.store=Store(':memory:');self.now=datetime(2026,9,5,12,tzinfo=UTC);self.workspace=AwarenessWorkspace(self.store,clock=lambda:self.now)
  for context in ('personal','inside-success','mitchell'):
   self.store.add_evidence(EvidenceItem(evidence_id=context,title='Meeting '+context,content='Tyler: I will send the department notes.\nSid: I will review the proposal.\nDecision: Keep the current delivery date.',provenance=Provenance('uploaded-transcript','owner-upload',context,'2026-09-01T10:00:00+00:00','2026-09-05T10:00:00+00:00',account_id=context),contexts=(ContextLabel(context,1,'fixture','v1'),)))
   self.store.upsert_task(TaskRecord(task_id=context,title='Review '+context+' proposal',context_id=context,task_type='commitment',status='open',due_at=(self.now-timedelta(hours=1)).isoformat(),evidence_ids=(context,)))
 def tearDown(self):self.store.close()
 def test_cross_context_due_relevance_and_source_clocks(self):
  value=self.workspace.snapshot();self.assertEqual({x['context_id'] for x in value['tasks']},{'personal','inside-success'})
  self.assertEqual(self.workspace.snapshot(during_chat=True,query='unrelated cooking')['tasks'],[])
  relevant=self.workspace.snapshot(during_chat=True,query='personal proposal');self.assertTrue(relevant['tasks'][0]['due'])
  source=relevant['tasks'][0]['sources'][0];self.assertEqual(source['source_timestamp'],'2026-09-01T10:00:00+00:00');self.assertNotEqual(source['source_timestamp'],source['indexed_at'])
 def test_done_is_owner_confirmed_not_evidenced_and_stale_review_rejected(self):
  task=self.workspace._task('personal');request={'taskId':'personal','expectedVersion':task['version'],'action':'done'}
  result=self.workspace.transition(request);self.assertEqual(result['review']['completion'],'owner-confirmed')
  self.assertNotIn('personal',[x['task_id'] for x in self.workspace.snapshot()['tasks']])
  with self.assertRaisesRegex(ValueError,'changed'):self.workspace.transition(request)
 def test_snooze_due_clock(self):
  task=self.workspace._task('personal');self.workspace.transition({'taskId':'personal','expectedVersion':task['version'],'action':'snooze','until':(self.now+timedelta(hours=1)).isoformat()})
  self.assertEqual(self.workspace.snapshot('personal')['tasks'],[]);self.now+=timedelta(hours=2);self.assertEqual(len(self.workspace.snapshot('personal')['tasks']),1)
 def test_meeting_owner_and_idempotent_decisions_tasks(self):
  preview=self.workspace.meeting_preview('inside-success');self.assertEqual(len(preview['candidates']),3)
  self.assertEqual(preview['candidates'][0]['owner'],'Unconfirmed assignee');self.assertEqual(preview['candidates'][1]['owner'],'Sid')
  request={'evidenceId':'inside-success','expectedHash':preview['source']['content_hash'],'context':'inside-success','selected':[{'candidateId':c['candidate_id'],'owner':c['speaker']} for c in preview['candidates']]}
  first=self.workspace.meeting_process(request);self.assertEqual(first,self.workspace.meeting_process(request));self.assertFalse(first['completion_claimed'])
  self.assertEqual(self.store.connection.execute('SELECT count(*) FROM decisions').fetchone()[0],1)
  self.assertTrue(all(x.get('line') for x in first['items']))
 def test_reject_stale_source_wrong_context_and_dormant_processing(self):
  preview=self.workspace.meeting_preview('inside-success');request={'evidenceId':'inside-success','expectedHash':preview['source']['content_hash'],'context':'personal','selected':[]}
  with self.assertRaisesRegex(ValueError,'context'):self.workspace.meeting_process(request)
  request['context']='mitchell'
  with self.assertRaisesRegex(ValueError,'dormant'):self.workspace.meeting_process(request)
  request['expectedHash']='stale'
  with self.assertRaisesRegex(ValueError,'changed'):self.workspace.meeting_process(request)

class ProjectCreationTests(unittest.TestCase):
 def test_owner_project_optional_evidence_replay_and_context(self):
  store=Store(':memory:');self.addCleanup(store.close);aw=AwarenessWorkspace(store)
  request={'requestId':'create-project-1','context':'personal','name':'Synthetic new project','objective':'Review the test workbook'}
  created=aw.dispatch('project.create',request);self.assertTrue(created['created']);self.assertIsNone(created['snapshotId'])
  reopened=AwarenessWorkspace(store).dispatch('project.create',request);self.assertFalse(reopened['created']);self.assertEqual(created['projectId'],reopened['projectId'])
  self.assertEqual(store.connection.execute('SELECT count(*) FROM projects').fetchone()[0],1)
  with self.assertRaisesRegex(ValueError,'different input'):aw.project_create({**request,'objective':'Changed'})
  for context in ['mitchell','auto','unknown']:
   with self.assertRaises(ValueError):aw.project_create({**request,'requestId':'other-request','context':context})
 def test_empty_checkpoint_is_explicit_unverified_owner_report(self):
  store=Store(':memory:');self.addCleanup(store.close);aw=AwarenessWorkspace(store)
  project=aw.project_create({'requestId':'empty-checkpoint-project','context':'personal','name':'Synthetic project','objective':'Review work'})
  request={'projectId':project['projectId'],'summary':'Owner says the workbook is ready','nextStep':'Inspect formulas','evidenceIds':[]}
  result=aw.checkpoint(request);self.assertEqual(result['evidence_count'],0);self.assertFalse(result['completion_claimed'])
  state=aw.resume(project['projectId'])['checkpoint']['state'];self.assertEqual(state['verification'],'unverified owner report');self.assertFalse(state['completed'])
  for invalid in ['source',[1],['x']*21]:
   with self.assertRaises(ValueError):aw.checkpoint({**request,'evidenceIds':invalid})

 def test_supported_evidence_creation_and_cross_context_rollback(self):
  store=Store(':memory:');self.addCleanup(store.close);aw=AwarenessWorkspace(store)
  store.add_evidence(EvidenceItem('source','Synthetic source','Evidence',Provenance('fixture','fixture','source','2026-09-01T10:00:00Z','2026-09-05T10:00:00Z'),(ContextLabel('inside-success',1,'fixture','1'),)))
  request={'requestId':'evidence-project','context':'personal','name':'Synthetic project','objective':'Review evidence','evidenceIds':['source']}
  with self.assertRaisesRegex(ValueError,'context mismatch'):aw.project_create(request)
  self.assertEqual(store.connection.execute('SELECT count(*) FROM projects').fetchone()[0],0)
  created=aw.project_create({**request,'context':'inside-success'});self.assertIsNotNone(created['snapshotId'])
  self.assertFalse(aw.resume(created['projectId'])['checkpoint']['state']['completed'])
  store.tombstone_evidence('source',reason='fixture')
  with self.assertRaisesRegex(ValueError,'removed'):aw.project_create({**request,'requestId':'new-evidence-project','context':'inside-success'})
  self.assertEqual(store.connection.execute('SELECT count(*) FROM projects').fetchone()[0],1)
