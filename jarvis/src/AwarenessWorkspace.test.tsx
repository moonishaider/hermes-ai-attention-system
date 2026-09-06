vi.mock('@tauri-apps/api/event',()=>({listen:vi.fn(async()=>()=>{})}));
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn(async(_command,args)=>args.operation==='awareness.snapshot'?{tasks:[{task_id:'t1',title:'Review proposal',owner:'Sid',context_id:'personal',status:'triage',reason:'Needs confirmation',version:'review-version',sources:[],review:{}}],sources:[],collections:[],coverage:'Saved evidence'}:{})}));
import {invoke} from '@tauri-apps/api/core';
import {AwarenessWorkspace} from './AwarenessWorkspace';
afterEach(()=>{cleanup();vi.clearAllMocks();});
it('requires a current reviewed task version and labels completion as an owner claim',async()=>{
 render(<AwarenessWorkspace context="personal" view="Inbox" onAsk={vi.fn()} onOpen={vi.fn()}/>);
 await screen.findByText('Review proposal');
 expect(vi.mocked(invoke).mock.calls.filter(([,args])=>(args as {operation:string}).operation==='awareness.task.transition')).toHaveLength(0);
 fireEvent.click(screen.getByRole('button',{name:'I completed this'}));
 await waitFor(()=>expect(screen.getByRole('status').textContent).toContain('not automatically classified as independently evidenced'));
 expect(invoke).toHaveBeenCalledWith('workspace_operation',{operation:'awareness.task.transition',request:{taskId:'t1',expectedVersion:'review-version',action:'done'}});
});

it('labels upload time and restricts meeting review to source contexts',async()=>{
 vi.mocked(invoke).mockImplementation(async(_command,args)=> (args as {operation:string}).operation==='awareness.snapshot'?{tasks:[],sources:[],collections:[]}: {analysisId:'analysis-fixture',source:{evidence_id:'e1',title:'Synthetic transcript',source_system:'uploaded-transcript',source_timestamp:'2026-09-05T12:00:00Z',contexts:[{context_id:'unknown'}]},candidates:[],summary:[]});
 render(<AwarenessWorkspace context="unknown" view="Projects" onAsk={vi.fn()} onOpen={vi.fn()} uploadedTranscript={{attachmentId:'attachment-fixture',sessionId:'session-fixture',context:'unknown'}}/>);
 await screen.findByText('Synthetic transcript');
 expect(screen.getByText(/Uploaded:.*Meeting date unknown/)).toBeTruthy();
 const select=screen.getByLabelText('Reviewed meeting context') as HTMLSelectElement;
 expect([...select.options].map(option=>option.value)).toEqual(['unknown']);
});
it('creates an explicitly scoped project and reuses its request ID after setup failure',async()=>{
 let creates=0;
 vi.mocked(invoke).mockImplementation(async(_command,args)=>{
  const value=args as {operation:string;request:Record<string,unknown>};
  if(value.operation==='awareness.project.create'){creates++;if(creates===1)throw new Error('temporary failure');return {project:{project_id:'new-project',name:'Amber review'},projectId:'new-project',created:true};}
  return {tasks:[],sources:[],collections:[]};
 });
 render(<AwarenessWorkspace context="unknown" view="Projects" onAsk={vi.fn()} onOpen={vi.fn()}/>);
 fireEvent.change(screen.getByLabelText('Project name'),{target:{value:'Amber review'}});
 fireEvent.change(screen.getByLabelText('Project objective'),{target:{value:'Review the synthetic evidence'}});
 const button=screen.getByRole('button',{name:'Create project'});
 expect((button as HTMLButtonElement).disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('Project context'),{target:{value:'personal'}});
 fireEvent.click(button);await screen.findByText(/temporary failure/);
 fireEvent.click(button);await screen.findByText(/Project saved in personal/);
 const requests=vi.mocked(invoke).mock.calls.filter(([,args])=>(args as {operation:string}).operation==='awareness.project.create').map(([,args])=>(args as {request:Record<string,unknown>}).request);
 expect(requests).toHaveLength(2);expect(requests[0].requestId).toBe(requests[1].requestId);expect(requests[0].context).toBe('personal');
 expect((screen.getByLabelText('Active project') as HTMLSelectElement).value).toBe('new-project');
});
