"""Owned, tick-driven typed jobs. No daemon, subprocess, LLM or external delivery.

Hermes native cron's agent/script execution and platform delivery are deliberately
not exposed by this runner. Its gateway lifecycle can call tick; the same durable
store owns workflow receipts and local actions. Schedule times are UTC instants
with explicit IANA wall-clock recurrence, coalescing missed runs after sleep.
"""
from datetime import datetime,timedelta,UTC
from zoneinfo import ZoneInfo
import json
import re
from uuid import uuid4,uuid5,NAMESPACE_URL
from .domain import stable_hash
from .capabilities import ensure_schema as workflow_schema

def ensure_schema(connection):
    workflow_schema(connection)
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS owned_jobs(job_id TEXT PRIMARY KEY,capability_id TEXT NOT NULL,spec_json TEXT NOT NULL,spec_hash TEXT NOT NULL,schedule_json TEXT NOT NULL,timezone TEXT NOT NULL,mode TEXT NOT NULL,arguments_json TEXT NOT NULL,status TEXT NOT NULL,next_run TEXT,last_run TEXT,last_status TEXT,last_result_json TEXT,failure_count INTEGER NOT NULL DEFAULT 0,claim_token TEXT,claim_until TEXT,cancel_requested INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS owned_job_occurrences(job_id TEXT NOT NULL,due_at TEXT NOT NULL,run_id TEXT NOT NULL,status TEXT NOT NULL,result_json TEXT,PRIMARY KEY(job_id,due_at));
    ''')

def utc(value):
    if isinstance(value,str): value=datetime.fromisoformat(value.replace('Z','+00:00'))
    if value.tzinfo is None: raise ValueError('schedule requires timezone-aware timestamp')
    return value.astimezone(UTC)

def next_due(schedule,timezone,after):
    after=utc(after); zone=ZoneInfo(timezone); kind=schedule.get('kind')
    if kind=='once':
        at=utc(schedule['at']); return at.isoformat() if at>after else None
    if kind=='interval':
        seconds=int(schedule['seconds'])
        if seconds<30: raise ValueError('minimum interval is 30 seconds')
        return (after+timedelta(seconds=seconds)).isoformat()
    if kind not in {'daily','weekly'}: raise ValueError('supported schedules: once, interval, daily, weekly')
    hour,minute=[int(n) for n in schedule['time'].split(':')]
    if not (0<=hour<24 and 0<=minute<60): raise ValueError('invalid local time')
    weekday=int(schedule.get('weekday',0))
    if not 0<=weekday<=6: raise ValueError('weekday must be 0 to 6')
    local=after.astimezone(zone)
    for offset in range(9):
        day=local.date()+timedelta(days=offset)
        if kind=='weekly' and day.weekday()!=weekday: continue
        candidate=datetime(day.year,day.month,day.day,hour,minute,tzinfo=zone)
        # DST gaps normalize forward; folds execute once at the first occurrence.
        candidate=candidate.astimezone(UTC).astimezone(zone)
        if candidate.astimezone(UTC)>after:return candidate.astimezone(UTC).isoformat()
    raise ValueError('unable to determine next run')

class Jobs:
    def __init__(self,store,studio,permission_inventory,clock=None):
        self.store=store;self.studio=studio;self.permission_inventory=permission_inventory
        self.clock=clock or (lambda:datetime.now(UTC));ensure_schema(store.connection)

    def create(self,capability_id,*,schedule,timezone,mode='shadow',inputs=None,fixtures=None):
        if mode not in {'dry','shadow','active'}:raise ValueError('invalid mode')
        row=self.store.connection.execute('SELECT * FROM capabilities WHERE capability_id=?',(capability_id,)).fetchone()
        if not row:raise ValueError('unknown capability')
        spec=json.loads(row['spec_json'])
        if not spec.get('steps'):raise ValueError('workflow must contain executable steps')
        validation=self.studio.validate(spec)
        if not validation.allowed:raise PermissionError(validation.reason)
        if row['permission_hash']!=stable_hash(self.permission_inventory()):raise PermissionError('permission inventory changed')
        if mode=='active' and row['status']!='active':raise PermissionError('activate tested capability first')
        quiet=schedule.get('quiet_hours',[22,8])
        if not isinstance(quiet,list) or len(quiet)!=2 or any(type(hour) is not int or not 0<=hour<=23 for hour in quiet):
            raise ValueError('quiet_hours must contain two hours from 0 to 23')
        due=next_due(schedule,timezone,self.clock())
        if due is None:raise ValueError('one-shot is in the past')
        job_id=str(uuid4())
        with self.store.connection:
            self.store.connection.execute('INSERT INTO owned_jobs(job_id,capability_id,spec_json,spec_hash,schedule_json,timezone,mode,arguments_json,status,next_run) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (job_id,capability_id,row['spec_json'],stable_hash(spec),json.dumps(schedule),timezone,mode,json.dumps({'inputs':inputs or {},'fixtures':fixtures or {}}),'active',due))
        return self.get(job_id)

    def get(self,job_id):
        row=self.store.connection.execute('SELECT * FROM owned_jobs WHERE job_id=?',(job_id,)).fetchone()
        if not row:raise ValueError('unknown job')
        item=dict(row)
        for key in ('spec_json','schedule_json','arguments_json','last_result_json'):
            item[key.removesuffix('_json')]=json.loads(item.pop(key) or 'null')
        return item

    def list(self):return [self.get(row[0]) for row in self.store.connection.execute('SELECT job_id FROM owned_jobs ORDER BY next_run')]
    def pause(self,job_id):self._state(job_id,'paused')
    def resume(self,job_id):self._state(job_id,'active')
    def cancel(self,job_id):self._state(job_id,'cancelled',cancel=True)
    def _state(self,job_id,status,cancel=False):
        self.get(job_id)
        with self.store.connection:self.store.connection.execute('UPDATE owned_jobs SET status=?,cancel_requested=? WHERE job_id=?',(status,int(cancel),job_id))

    def _claim(self,job_id,token,now):
        conn=self.store.connection
        row=conn.execute('SELECT * FROM owned_jobs WHERE job_id=?',(job_id,)).fetchone()
        if not row:raise ValueError('unknown job')
        if row['claim_token'] and row['claim_until'] and utc(row['claim_until'])>now:
            raise RuntimeError('this job is already executing')
        conn.execute('UPDATE owned_jobs SET claim_token=?,claim_until=? WHERE job_id=?',
            (token,(now+timedelta(minutes=5)).isoformat(),job_id))
        return dict(row)

    def run_now(self,job_id,run_id=None):
        """Run the frozen job once, under the same lease as ticks.

        The optional request identity makes retries idempotent. Manual execution
        does not resume a paused schedule or move its next occurrence.
        """
        request_id=run_id or str(uuid4())
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,96}',request_id):raise ValueError('invalid manual run identity')
        execution_id=str(uuid5(NAMESPACE_URL,job_id+':manual:'+request_id))
        due='manual:'+request_id;now=utc(self.clock());token=str(uuid4());conn=self.store.connection
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            prior=conn.execute('SELECT * FROM owned_job_occurrences WHERE job_id=? AND due_at=?',(job_id,due)).fetchone()
            if prior and prior['status'] in {'completed','cancelled'}:return json.loads(prior['result_json'])
            job=self._claim(job_id,token,now)
            if job['status']=='cancelled':raise ValueError('cancelled job cannot execute')
        return self._execute_claimed(job,token,due,execution_id,manual=True)

    @staticmethod
    def _semantic_outputs(outputs,spec):
        # Generated local receipt identities differ for every occurrence. Source
        # record identities remain intact because changes in source membership matter.
        tools={step['id']:step['tool'] for step in spec.get('steps',[])}
        result={}
        for step_id,value in outputs.items():
            tool=tools.get(step_id)
            if isinstance(value,dict) and tool in {'save_output','create_task'}:
                value={key:content for key,content in value.items() if key not in {'artifact_id','task_id','run_id','created_at'}}
            result[step_id]=value
        return result

    def _execute_claimed(self,job,token,due,run_id,manual=False):
        now=utc(self.clock());conn=self.store.connection;args=json.loads(job['arguments_json']);spec=json.loads(job['spec_json'])
        with conn:conn.execute('INSERT OR IGNORE INTO owned_job_occurrences VALUES(?,?,?,?,?)',(job['job_id'],due,run_id,'running',None))
        def cancelled():
            row=conn.execute('SELECT cancel_requested,status,claim_token FROM owned_jobs WHERE job_id=?',(job['job_id'],)).fetchone()
            if not row or row[2]!=token:return True
            with conn:conn.execute('UPDATE owned_jobs SET claim_until=? WHERE job_id=? AND claim_token=?',((utc(self.clock())+timedelta(minutes=5)).isoformat(),job['job_id'],token))
            return bool(row[0]) or row[1]=='cancelled' or (not manual and row[1]=='paused')
        try:
            result=self.studio.run(job['capability_id'],mode=job['mode'],current_permission_inventory=self.permission_inventory(),run_id=run_id,spec_override=spec,cancelled=cancelled,**args)
        except Exception as exc:
            result={'run_id':run_id,'status':'failed','error':type(exc).__name__+': '+str(exc),'external_write':False}
        current=conn.execute('SELECT status,cancel_requested,claim_token FROM owned_jobs WHERE job_id=?',(job['job_id'],)).fetchone()
        if not current or current['claim_token']!=token:
            return {'job_id':job['job_id'],'run_id':run_id,'status':'ownership-lost','external_write':False}
        # A pause is resumable at a step boundary. Studio receipts retain already
        # completed local writes; reopening this same occurrence cannot repeat them.
        paused=not manual and result['status']=='cancelled' and current['status']=='paused' and not current['cancel_requested']
        if paused:
            result['status']='paused'
            with conn:
                conn.execute("UPDATE workflow_executions SET status='paused',result_json=? WHERE run_id=?",(json.dumps(result),run_id))
                conn.execute("UPDATE capability_runs SET result='paused',audit_json=? WHERE run_id=?",(json.dumps(result),run_id))
        succeeded=result['status']=='completed';failures=job['failure_count'] if manual else (0 if succeeded else job['failure_count']+(0 if paused else 1))
        previous=json.loads(job['last_result_json'] or '{}')
        changed=succeeded and stable_hash(self._semantic_outputs(result.get('outputs',{}),spec))!=stable_hash(self._semantic_outputs(previous.get('outputs',{}),spec))
        result['change_state']='paused' if paused else ('changed' if changed else ('no-change' if succeeded else 'check-failed'))
        schedule=json.loads(job['schedule_json']);local_hour=now.astimezone(ZoneInfo(job['timezone'])).hour
        start,end=schedule.get('quiet_hours',[22,8]);in_quiet=(start<=local_hour<end) if start<end else (local_hour>=start or local_hour<end) if start!=end else False
        result['notification_due']=bool(not paused and (changed or not succeeded) and not in_quiet)
        result['notification_reason']='quiet-hours' if in_quiet else result['change_state']
        result['external_notification_sent']=False
        if manual:next_run=job['next_run']
        elif paused:next_run=due
        elif result['status']=='cancelled':next_run=None
        elif succeeded:next_run=next_due(schedule,job['timezone'],now)
        else:next_run=(now+timedelta(seconds=min(3600,30*2**min(failures,7)))).isoformat()
        result['job_id']=job['job_id']
        with conn:
            conn.execute('UPDATE owned_job_occurrences SET status=?,result_json=? WHERE job_id=? AND due_at=?',(result['status'],json.dumps(result),job['job_id'],due))
            conn.execute("UPDATE owned_jobs SET next_run=?,last_run=?,last_status=?,last_result_json=?,failure_count=?,claim_token=NULL,claim_until=NULL,status=CASE WHEN status='active' AND ? IS NULL AND ?=0 THEN 'completed' ELSE status END WHERE job_id=? AND claim_token=?",(next_run,now.isoformat(),result['status'],json.dumps(result),failures,next_run,int(manual),job['job_id'],token))
        return result

    def tick(self,limit=1):
        now=utc(self.clock());token=str(uuid4());conn=self.store.connection;selected=[]
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            rows=conn.execute("SELECT job_id FROM owned_jobs WHERE status='active' AND next_run<=? AND (claim_token IS NULL OR claim_until<=?) ORDER BY next_run LIMIT ?",(now.isoformat(),now.isoformat(),max(1,min(limit,4)))).fetchall()
            for row in rows:selected.append(self._claim(row['job_id'],token,now))
        results=[]
        for job in selected:
            due=job['next_run'];run_id=str(uuid5(NAMESPACE_URL,job['job_id']+':'+due))
            if job['failure_count']:
                retry=conn.execute("SELECT run_id FROM owned_job_occurrences WHERE job_id=? AND status='failed' AND due_at NOT LIKE 'manual:%' ORDER BY due_at DESC LIMIT 1",(job['job_id'],)).fetchone()
                if retry:run_id=retry[0]
            results.append(self._execute_claimed(job,token,due,run_id))
        return results
