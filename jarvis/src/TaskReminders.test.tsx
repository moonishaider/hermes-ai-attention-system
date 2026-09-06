import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
const state=vi.hoisted(()=>({delivered:false}));
vi.mock('./transport',()=>({isCompanion:()=>false,invoke:vi.fn(async (_:string,args:{operation:string;request:Record<string,unknown>})=>{
 if(args.operation==='awareness.reminders.pending') return {data:state.delivered || args.request.query==='cooking' ? [] : [{taskId:'t1',title:'Review proposal',occurrence:'due1',version:'v1',context:'personal'}]};
 if(args.operation==='awareness.reminders.ack'){state.delivered=true;return {acknowledged:true,task:{taskId:'t1',title:'Review proposal',occurrence:'due1',version:'v2',context:'personal'}};}
 return {};
})}));
import { invoke } from './transport';
import { TaskReminders } from './TaskReminders';
afterEach(()=>{cleanup();state.delivered=false;vi.clearAllMocks();});
it('shows pending due work and snoozes without prematurely consuming it',async()=>{
 render(<TaskReminders context="personal" duringChat={false} query=""/>);
 await screen.findByText('Due reminder: Review proposal');
 fireEvent.click(screen.getByRole('button',{name:'Snooze 10 minutes'}));
 await waitFor(()=>expect(screen.queryByText('Due reminder: Review proposal')).toBeNull());
 expect(vi.mocked(invoke).mock.calls.find(([,args])=>(args as {operation:string}).operation==='awareness.task.transition')?.[1]).toMatchObject({request:{taskId:'t1',expectedVersion:'v1',action:'snooze'}});
});
it('does not consume unrelated reminders',async()=>{
 render(<TaskReminders context="personal" duringChat query="cooking"/>);
 await waitFor(()=>expect(invoke).toHaveBeenCalled());
 expect(vi.mocked(invoke).mock.calls.some(([,args])=>(args as {operation:string}).operation==='awareness.reminders.ack')).toBe(false);
});

it('keeps an undisposed reminder through context switches and remounts',async()=>{
 const first=render(<TaskReminders context="personal" duringChat query="proposal"/>);
 await screen.findByText('Due reminder: Review proposal');
 first.rerender(<TaskReminders context="personal" duringChat query="cooking"/>);
 await waitFor(()=>expect(screen.queryByText('Due reminder: Review proposal')).toBeNull());
 expect(state.delivered).toBe(false);
 first.unmount();render(<TaskReminders context="personal" duringChat query="proposal"/>);
 await screen.findByText('Due reminder: Review proposal');
 fireEvent.click(screen.getByRole('button',{name:'Dismiss reminder'}));
 await waitFor(()=>expect(state.delivered).toBe(true));
});

it('ignores a delayed pending response after context switch without consuming it',async()=>{
 let resolvePending!:(value:unknown)=>void;
 vi.mocked(invoke).mockImplementationOnce(()=>new Promise(resolve=>{resolvePending=resolve;}));
 const view=render(<TaskReminders context="personal" duringChat query="proposal"/>);
 await waitFor(()=>expect(resolvePending).toBeDefined());
 view.rerender(<TaskReminders context="inside-success" duringChat query="cooking"/>);
 await act(async()=>{resolvePending({data:[{taskId:'t1',title:'Review proposal',occurrence:'due1',version:'v1',context:'personal'}]});});
 expect(screen.queryByText('Due reminder: Review proposal')).toBeNull();
 expect(state.delivered).toBe(false);
 expect(vi.mocked(invoke).mock.calls.some(([,args])=>(args as {operation:string}).operation==='awareness.reminders.ack')).toBe(false);
 view.rerender(<TaskReminders context="personal" duringChat query="proposal"/>);
 await screen.findByText('Due reminder: Review proposal');
});
