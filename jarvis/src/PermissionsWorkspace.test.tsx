import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn(async (_command, args) => (args as {operation?:string})?.operation === 'snapshot' ? { grants: [], stops: [], profiles: [{id:'public',label:'Public research',account_id:'public',profile:'public-unauthed',context_id:'personal'},{id:'company',label:'Company browser',account_id:'work-account',profile:'Work',context_id:'inside-success'}] } : {}) }));
import { invoke } from '@tauri-apps/api/core';
import { PermissionsWorkspace } from './PermissionsWorkspace';
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it('loads configuration without issuing authority and scopes owner submission to selected identity', async () => {
 render(<PermissionsWorkspace/>);
 await screen.findByText('Public research');
 expect(vi.mocked(invoke).mock.calls.every(([,args]) => (args as {operation?:string})?.operation === 'snapshot')).toBe(true);
 fireEvent.change(screen.getByLabelText('What may Jarvis do?'), {target:{value:'Read vendor comparison'}});
 fireEvent.change(screen.getByLabelText('Account and browser context'), {target:{value:'company'}});
 expect((screen.getByLabelText('Create personal events') as HTMLInputElement).disabled).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Save scoped grant'}));
 await waitFor(() => expect(vi.mocked(invoke).mock.calls.find(([,args])=>(args as {operation?:string})?.operation === 'issue')?.[1]).toEqual({operation:'issue',request:{title:'Read vendor comparison',context_id:'inside-success',account_id:'work-account',profile:'Work',operations:['browser.read'],domains:[],apps:[],resources:[],standing:false,hours:12}}));
 expect(screen.getByText(/Configured mapping/)).toBeTruthy();
});
