import unittest
from datetime import datetime,timedelta,UTC
from hermes_attention.storage import Store
from hermes_attention.capabilities import CapabilityStudio
from hermes_attention.jobs import Jobs,next_due

class WorkflowJobsTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:');self.inv={'list_tasks':'read','create_task':'local','save_output':'local'}
        self.studio=CapabilityStudio(self.store,set(self.inv));self.now=datetime(2026,9,5,tzinfo=UTC)
        self.jobs=Jobs(self.store,self.studio,lambda:self.inv,lambda:self.now)
    def tearDown(self):self.store.close()
    def create(self):
        spec={'kind':'workflow','context_id':'personal','tools':list(self.inv),'steps':[
            {'id':'tasks','tool':'list_tasks'},
            {'id':'note','tool':'save_output','depends_on':['tasks'],'args':{'title':'Review','content':{'from_step':'tasks'}}},
            {'id':'follow','tool':'create_task','args':{'title':'Review synthetic results'}}]}
        return self.studio.create(spec,permission_inventory=self.inv)['capability_id']
    def test_dry_shadow_active_and_replay(self):
        cid=self.create()
        dry=self.studio.dry_run(cid,current_permission_inventory=self.inv,fixtures={'tasks':[{'title':'fixture'}]})
        self.assertEqual(dry['status'],'completed');self.assertTrue(dry['steps'][1]['output']['preview'])
        shadow=self.studio.run(cid,mode='shadow',current_permission_inventory=self.inv)
        self.assertEqual(shadow['outputs']['tasks'],[]);self.assertEqual(self.store.list_tasks(),[])
        self.studio.set_status(cid,'active')
        result=self.studio.run(cid,mode='active',current_permission_inventory=self.inv,run_id='repeat')
        again=self.studio.run(cid,mode='active',current_permission_inventory=self.inv,run_id='repeat')
        self.assertEqual(result,again);self.assertEqual(len(self.store.list_tasks()),1)
    def test_due_pause_resume_sleep_and_no_duplicate(self):
        cid=self.create();self.studio.dry_run(cid,current_permission_inventory=self.inv,fixtures={'tasks':[]});self.studio.set_status(cid,'active')
        job=self.jobs.create(cid,schedule={'kind':'interval','seconds':60},timezone='Asia/Karachi',mode='active')
        self.now+=timedelta(hours=10)
        result=self.jobs.tick();self.assertEqual(result[0]['status'],'completed');self.assertEqual(len(self.store.list_tasks()),1)
        self.assertEqual(self.jobs.tick(),[])
        self.jobs.pause(job['job_id']);self.now+=timedelta(hours=1);self.assertEqual(self.jobs.tick(),[])
        self.jobs.resume(job['job_id']);self.assertEqual(len(self.jobs.tick()),1)
        self.jobs.cancel(job['job_id']);self.now+=timedelta(days=1);self.assertEqual(self.jobs.tick(),[])
    def test_failed_connector_is_not_no_change(self):
        cid=self.create();job=self.jobs.create(cid,schedule={'kind':'interval','seconds':60},timezone='UTC',mode='dry',fixtures={'tasks':{'error':'source unavailable'}})
        self.now+=timedelta(minutes=1);result=self.jobs.tick()[0]
        self.assertEqual(result['change_state'],'check-failed');self.assertEqual(self.jobs.get(job['job_id'])['failure_count'],1)
    def test_timezone_and_frozen_spec(self):
        self.assertEqual(next_due({'kind':'daily','time':'09:00'},'Asia/Karachi',self.now),'2026-09-05T04:00:00+00:00')
        with self.assertRaises(ValueError):next_due({'kind':'interval','seconds':1},'UTC',self.now)
    def test_partial_failure_retry_does_not_duplicate_local_action(self):
        spec={'kind':'mission','context_id':'personal','tools':list(self.inv),'steps':[
          {'id':'task','tool':'create_task','args':{'title':'Only once'}},
          {'id':'output','tool':'save_output','args':{'content':{'input':'document'}}}]}
        cid=self.studio.create(spec,permission_inventory=self.inv)['capability_id']
        self.studio.dry_run(cid,current_permission_inventory=self.inv,inputs={'document':'fixture'})
        self.studio.set_status(cid,'active')
        first=self.studio.run(cid,mode='active',current_permission_inventory=self.inv,run_id='partial')
        self.assertEqual(first['status'],'failed');self.assertEqual(len(self.store.list_tasks()),1)
        second=self.studio.run(cid,mode='active',current_permission_inventory=self.inv,run_id='partial',inputs={'document':'recovered'})
        self.assertEqual(second['status'],'completed');self.assertEqual(len(self.store.list_tasks()),1)
    def test_permission_and_context_negatives(self):
        cid=self.create()
        with self.assertRaises(PermissionError):self.studio.run(cid,mode='shadow',current_permission_inventory={})
        spec={'kind':'workflow','context_id':'personal','tools':['list_tasks'],'steps':[{'id':'x','tool':'list_tasks','args':{'context_id':'inside-success'}}]}
        cid=self.studio.create(spec,permission_inventory=self.inv)['capability_id']
        result=self.studio.run(cid,mode='shadow',current_permission_inventory=self.inv)
        self.assertEqual(result['status'],'failed');self.assertIn('context',result['error'])
    def test_revised_job_runs_frozen_version(self):
        cid=self.create();self.studio.dry_run(cid,current_permission_inventory=self.inv,fixtures={'tasks':[]});self.studio.set_status(cid,'active')
        self.jobs.create(cid,schedule={'kind':'interval','seconds':60},timezone='UTC',mode='active')
        self.studio.revise(cid,{'kind':'workflow','context_id':'personal','tools':['list_tasks'],'steps':[{'id':'new','tool':'list_tasks'}]},permission_inventory=self.inv)
        self.now+=timedelta(minutes=1);result=self.jobs.tick()[0]
        self.assertEqual(result['status'],'completed');self.assertIn('follow',result['outputs'])
    def test_missing_steps_honest_failure(self):
        cid=self.studio.create({'kind':'workflow','context_id':'personal','tools':[]},permission_inventory=self.inv)['capability_id']
        self.assertEqual(self.studio.dry_run(cid,current_permission_inventory=self.inv)['status'],'failed')
    def review_only(self):
        spec={'name':'Holdout review','kind':'workflow','context_id':'personal','tools':['list_tasks','save_output'],'steps':[
            {'id':'tasks','tool':'list_tasks'},
            {'id':'save','tool':'save_output','args':{'title':'Review','content':{'from_step':'tasks'}}}]}
        cid=self.studio.create(spec,permission_inventory=self.inv)['capability_id']
        self.studio.dry_run(cid,current_permission_inventory=self.inv,fixtures={'tasks':[]})
        self.studio.set_status(cid,'active')
        return cid
    def test_unchanged_source_with_new_output_receipt_is_no_change(self):
        cid=self.review_only();self.jobs.create(cid,schedule={'kind':'interval','seconds':30},timezone='UTC',mode='active')
        self.now+=timedelta(seconds=31);first=self.jobs.tick()[0]
        self.now+=timedelta(seconds=31);second=self.jobs.tick()[0]
        self.assertEqual(first['outputs']['tasks'],second['outputs']['tasks'])
        self.assertNotEqual(first['outputs']['save']['artifact_id'],second['outputs']['save']['artifact_id'])
        self.assertEqual(first['change_state'],'changed');self.assertEqual(second['change_state'],'no-change')
        self.assertFalse(second['notification_due'])
    def test_pause_mid_execution_resumes_same_occurrence_without_repeating_write(self):
        cid=self.create();self.studio.dry_run(cid,current_permission_inventory=self.inv,fixtures={'tasks':[]});self.studio.set_status(cid,'active')
        job=self.jobs.create(cid,schedule={'kind':'interval','seconds':30},timezone='UTC',mode='active')
        original=self.studio._execute;calls=[]
        def execute(tool,*args,**kwargs):
            result=original(tool,*args,**kwargs);calls.append(tool)
            if tool=='save_output':self.jobs.pause(job['job_id'])
            return result
        self.studio._execute=execute;self.now+=timedelta(seconds=31)
        paused=self.jobs.tick()[0];self.assertEqual(paused['status'],'paused')
        self.assertIsNotNone(self.jobs.get(job['job_id'])['next_run']);self.assertEqual(self.jobs.tick(),[])
        self.jobs.resume(job['job_id']);self.now+=timedelta(hours=1)
        resumed=self.jobs.tick()[0]
        self.assertEqual(resumed['status'],'completed');self.assertEqual(resumed['run_id'],paused['run_id'])
        self.assertEqual(calls.count('save_output'),1);self.assertEqual(calls.count('create_task'),1)
        self.assertEqual(len(self.store.list_tasks()),1)
    def test_manual_run_preserves_paused_schedule_and_replays_frozen_revision(self):
        cid=self.review_only();job=self.jobs.create(cid,schedule={'kind':'interval','seconds':60},timezone='UTC',mode='active')
        self.jobs.pause(job['job_id'])
        changed={'name':'New version','kind':'workflow','context_id':'personal','tools':['list_tasks'],'steps':[{'id':'different','tool':'list_tasks'}]}
        self.studio.revise(cid,changed,permission_inventory=self.inv)
        first=self.jobs.run_now(job['job_id'],run_id='owner-click')
        replay=self.jobs.run_now(job['job_id'],run_id='owner-click')
        self.assertEqual(first,replay);self.assertIn('save',first['outputs'])
        current=self.jobs.get(job['job_id']);self.assertEqual(current['status'],'paused');self.assertEqual(current['next_run'],job['next_run'])
        self.assertEqual(self.store.connection.execute('SELECT count(*) FROM workflow_outputs').fetchone()[0],1)
    def test_manual_and_scheduled_runs_share_a_claim(self):
        cid=self.review_only();job=self.jobs.create(cid,schedule={'kind':'interval','seconds':30},timezone='UTC',mode='active')
        original=self.studio._execute;checks=[]
        def execute(*args,**kwargs):
            with self.assertRaisesRegex(RuntimeError,'already executing'):self.jobs.run_now(job['job_id'],run_id='overlap')
            self.assertEqual(self.jobs.tick(),[]);checks.append(True)
            return original(*args,**kwargs)
        self.studio._execute=execute;self.now+=timedelta(seconds=31)
        result=self.jobs.tick()[0];self.assertEqual(result['status'],'completed');self.assertTrue(checks)
    def test_invalid_quiet_hours_rejected_before_a_job_is_created(self):
        cid=self.review_only()
        for quiet in [[22],[99,8],['22',8]]:
            with self.assertRaises(ValueError):self.jobs.create(cid,schedule={'kind':'interval','seconds':30,'quiet_hours':quiet},timezone='UTC')

if __name__=='__main__':unittest.main()
