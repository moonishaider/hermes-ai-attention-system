import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
const state=vi.hoisted(()=>({cancelled:false}));
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn(async(command)=>command==='permissions_operation'?{grants:[{grant_id:'grant',title:'Compare sources',account_id:'personal',profile:'Personal',operations:['browser.read'],status:'active',expired:false}]}:command==='browser_targets'?{data:[{targetId:'opaque-native-target',label:'Observed tab',accountLabel:'Account unverified',profileLabel:'Personal mapping',windowLabel:'Window 2'}]}:state.cancelled?{cancelled:true}:{selectionId:'opaque-selection',grantId:'grant',label:'Confirmed target',accountLabel:'Personal',profileLabel:'Personal',windowLabel:'Window 2',expiresAt:'2026-09-06T00:00:00Z',status:'selected'})}));
import {invoke} from '@tauri-apps/api/core';
import {BrowserContext} from './BrowserContext';
afterEach(()=>{cleanup();vi.clearAllMocks();state.cancelled=false;});
it('requires observed target selection and native confirmation before binding any authority',async()=>{
 const selected=vi.fn();render(<BrowserContext sessionId="session-a" ensureSession={vi.fn()} onSelect={selected}/>);
 fireEvent.click(screen.getByRole('button',{name:'Choose browser context'}));await screen.findByText('Compare sources · personal · Personal');
 expect(selected).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Show observed browser targets'}));await screen.findByLabelText('Observed target');
 expect((screen.getByRole('button',{name:'Select and review actual browser target'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('Observed target'),{target:{value:'opaque-native-target'}});
 state.cancelled=true;fireEvent.click(screen.getByRole('button',{name:'Select and review actual browser target'}));
 await waitFor(()=>expect(invoke).toHaveBeenCalledWith('select_browser_context',{sessionId:'session-a',grantId:'grant',targetId:'opaque-native-target'}));
 expect(selected).not.toHaveBeenCalled();
});
