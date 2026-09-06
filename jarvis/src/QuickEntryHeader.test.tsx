import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn(async()=>({ok:true}))}));
import {invoke} from '@tauri-apps/api/core';
import {QuickEntryHeader} from './QuickEntryHeader';
afterEach(()=>{cleanup();vi.clearAllMocks();});
it('identifies current conversation and only hides the fixed quick entry window',async()=>{
 const {rerender}=render(<QuickEntryHeader title="Amber follow-up" context="Personal"/>);
 expect(screen.getByText('Amber follow-up')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Close Quick Entry without cancelling requests'}));
 await waitFor(()=>expect(invoke).toHaveBeenCalledExactlyOnceWith('quick_entry_control',{visible:false}));
 rerender(<QuickEntryHeader title="New conversation" context="Auto context"/>);
 expect(screen.getByText('New conversation')).toBeTruthy();
});
