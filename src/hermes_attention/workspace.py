"""Trusted desktop workspace adapter; no model-exposed authority or shell operations."""
from dataclasses import asdict,is_dataclass
import json
from .capabilities import CapabilityStudio,READ_TOOLS,LOCAL_TOOLS,ensure_schema
from .domain import utc_now
from .jobs import Jobs
from .learning import Learning
from .awareness_workspace import AwarenessWorkspace

class Workspace:
    def __init__(self,store,skills_root,*,native=None,owner=False,clock=None,contexts=None):
        self.store=store;self.owner=owner
        self.contexts=set(contexts or {'personal','inside-success','mitchell','mixed','unknown'})
        self.inventory={t:('read' if t in READ_TOOLS else 'local') for t in sorted(READ_TOOLS|LOCAL_TOOLS)}
        ensure_schema(store.connection)
        self.studio=CapabilityStudio(store,set(self.inventory))
        self.jobs=Jobs(store,self.studio,lambda:self.inventory,clock)
        self.learning=Learning(store,skills_root,native=native,authorize_owner=lambda *_:self.owner)

    def _spec(self,spec):
        if not isinstance(spec,dict) or spec.get('context_id') not in self.contexts:
            raise ValueError('Choose a configured workflow context')
        if not isinstance(spec.get('name'),str) or not 1<=len(spec['name'].strip())<=200:
            raise ValueError('A workflow name is required')
        if not isinstance(spec.get('steps'),list) or not 1<=len(spec['steps'])<=30:
            raise ValueError('Add between one and thirty workflow steps')
        return spec

    def dispatch(self,operation,value):
        if not isinstance(value,dict):raise ValueError('Workspace request must be an object')
        if not self.owner:raise PermissionError('Workspace commands require the local owner interface')
        if operation.startswith('awareness.'):
            return AwarenessWorkspace(self.store).dispatch(operation.removeprefix('awareness.'),value)
        if operation=='learning.snapshot':return self.learning.snapshot()
        if operation=='learning.select-native':return self.learning.select_native(value['pendingId'])
        if operation=='learning.resolve-native':return self.learning.resolve_native(value['selectionToken'],value['action'])
        if operation=='learning.resolve-project':return self.learning.resolve_project(value['memoryId'],value['action'],expected_hash=value['expectedHash'])
        if operation=='learning.save-preference':
            return self.learning.save_preference(value['text'],provenance={'source':'owner-desktop','explicit':True},replaces_id=value.get('replacesId'),uncertain=bool(value.get('uncertain',False)))
        if operation=='learning.undo-preference':return self.learning.undo_preference(value['preferenceId'])
        if operation=='learning.skill-preview':return self.learning.skill_preview(value['name'],value['content'])
        if operation=='learning.skill-edit':return self.learning.skill_edit(value['name'],value['content'],expected_hash=value['expectedHash'])
        if operation=='learning.skill-rollback':return self.learning.skill_rollback(value['versionId'])
        if operation=='learning.community-stage':return self.learning.community_stage(name=value['name'],content=value['content'],source=value['source'],requested_tools=value.get('requestedTools',[]))
        if operation=='capabilities.list':
            rows=[]
            for row in self.store.connection.execute('SELECT * FROM capabilities ORDER BY updated_at DESC'):
                item=dict(row);item['spec']=json.loads(item.pop('spec_json'));rows.append(item)
            return {'data':rows,'tools':self.inventory}
        if operation=='capabilities.create':return self.studio.create(self._spec(value['spec']),permission_inventory=self.inventory)
        if operation=='capabilities.revise':return self.studio.revise(value['capabilityId'],self._spec(value['spec']),permission_inventory=self.inventory)
        if operation=='capabilities.run':return self.studio.run(value['capabilityId'],mode=value.get('mode','dry'),current_permission_inventory=self.inventory,fixtures=value.get('fixtures'),inputs=value.get('inputs'),run_id=value.get('runId'))
        if operation=='capabilities.activate':
            self.studio.set_status(value['capabilityId'],'active');return {'status':'active'}
        if operation=='capabilities.output':
            row=self.store.connection.execute('SELECT * FROM workflow_outputs WHERE artifact_id=?',(value['artifactId'],)).fetchone()
            if row is None:raise ValueError('Workflow output not found')
            return dict(row)
        if operation=='jobs.list':return {'data':self.jobs.list(),'lifecycle':self.lifecycle(),'external_delivery':False}
        if operation=='jobs.lifecycle':
            mode=value.get('mode')
            if mode not in {'off','while-jarvis-runs'}:raise ValueError('Choose Off or While Jarvis runs')
            with self.store.connection:self.store.connection.execute('INSERT OR REPLACE INTO runtime_settings VALUES(?,?,?)',('owned_jobs_lifecycle',json.dumps(mode),utc_now()))
            return {'lifecycle':mode}

        if operation=='jobs.run':return self.jobs.run_now(value['jobId'],run_id=value.get('runId'))
        if operation=='jobs.create':return self.jobs.create(value['capabilityId'],schedule=value['schedule'],timezone=value['timezone'],mode=value.get('mode','shadow'),inputs=value.get('inputs'),fixtures=value.get('fixtures'))
        if operation in {'jobs.pause','jobs.resume','jobs.cancel'}:
            getattr(self.jobs,operation.split('.')[1])(value['jobId']);return self.jobs.get(value['jobId'])
        if operation=='jobs.tick':return {'data':self.jobs.tick(limit=1) if self.lifecycle()=='while-jarvis-runs' else [],'lifecycle':self.lifecycle()}
        raise ValueError('Unsupported workspace operation')

    def lifecycle(self):
        row=self.store.connection.execute('SELECT value_json FROM runtime_settings WHERE key=?',('owned_jobs_lifecycle',)).fetchone()
        return json.loads(row[0]) if row else 'while-jarvis-runs'

def encode(value):
    if is_dataclass(value):return asdict(value)
    raise TypeError('Unsupported result type')
