import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
const state=vi.hoisted(()=>({callback:null as null|((event:{payload:{eventId:string;generation:string}})=>void)}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn(async(_command,args)=>({state:args.operation==='start'?'listening':'off',available:true,generation:args.operation==='start'?'generation-1':undefined,phrase:'Hey Hermes'}))}));
vi.mock('@tauri-apps/api/event',()=>({listen:vi.fn(async(_event,callback)=>{state.callback=callback;return()=>{};})}));
import {invoke} from '@tauri-apps/api/core';
import {WakeControl} from './WakeControl';
afterEach(()=>{cleanup();vi.clearAllMocks();state.callback=null;});
it('stays off until owner toggle and sends one voice trigger per owned wake signal',async()=>{
 const onWake=vi.fn(async()=>{});render(<WakeControl visible occupied={false} onWake={onWake}/>);
 await screen.findByText('Hey Hermes · off');expect(invoke).toHaveBeenCalledExactlyOnceWith('wake_control',{operation:'status'});expect(onWake).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Enable wake while Jarvis runs'}));await screen.findByText('Hey Hermes · listening');
 state.callback!({payload:{eventId:'wake-1',generation:'stale'}});expect(onWake).not.toHaveBeenCalled();
 state.callback!({payload:{eventId:'wake-1',generation:'generation-1'}});state.callback!({payload:{eventId:'wake-1',generation:'generation-1'}});
 await waitFor(()=>expect(onWake).toHaveBeenCalledTimes(1));
});
