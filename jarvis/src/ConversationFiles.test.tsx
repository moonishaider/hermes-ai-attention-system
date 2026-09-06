import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
const state = vi.hoisted(() => ({ files: [] as unknown[], error: false }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn(async (command: string) => {
  if (command === 'list_attachments') return { data: state.files, artifacts: [{ artifact_id: 'output-1', display_name: 'Reconciliation.xlsx', mime_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', version: 2 }] };
  if (command === 'attach_bytes') {
    if (state.error) throw new Error('Document is encrypted');
    state.files = [{ attachment_id: 'file-1', display_name: 'sample.csv', mime_type: 'text/csv', size_bytes: 8, status: 'ready', retention: 'conversation', preview: '<script>steal()</script>\n1,2' }];
    return { data: state.files };
  }
  if (command === 'attach_files') return { data: [], errors: [{ name: 'damaged.pdf', error: 'Invalid PDF structure' }] };
  return { ok: true };
}) }));
import { invoke } from '@tauri-apps/api/core';
import { ConversationFiles, validateSelectedFile } from './ConversationFiles';
afterEach(() => { cleanup(); vi.clearAllMocks(); state.files = []; state.error = false; });
const selected = () => {
  const file = new File(['a,b\n1,2'], 'sample.csv', { type: 'text/csv' });
  Object.defineProperty(file, 'arrayBuffer', { value: async () => new TextEncoder().encode('a,b\n1,2').buffer });
  return file;
};
describe('file lifecycle holdouts', () => {
  it('marks pending upload synchronously and transfers the lock to a newly created conversation', async () => {
    let resolve!: (id: string) => void;
    const creating = new Promise<string>(done => { resolve = done; });
    const busy = vi.fn();
    render(<ConversationFiles sessionId={null} ensureSession={() => creating} onBusyChange={busy}/>);
    fireEvent.click(screen.getByRole('button', { name: '＋ Attach' }));
    expect(busy).toHaveBeenCalledExactlyOnceWith(null, true);
    resolve('new-session');
    await waitFor(() => expect(busy).toHaveBeenLastCalledWith('new-session', false));
    expect(busy.mock.calls).toEqual([[null,true],['new-session',true],[null,false],['new-session',false]]);
  });
  it('restores owner metadata using retention_state while extraction status remains complete', async () => {
    state.files = [{ attachment_id: 'forgotten-1', display_name: 'old.txt', size_bytes: 40, status: 'complete', retention_state: 'forgotten', preview: '' }];
    const busy = vi.fn();
    render(<ConversationFiles sessionId="session-A" ensureSession={async () => 'session-A'} onBusyChange={busy}/>);
    fireEvent.click(await screen.findByRole('button', { name: 'Restore' }));
    expect(busy).toHaveBeenCalledWith('session-A', true);
    await waitFor(() => expect(busy).toHaveBeenLastCalledWith('session-A', false));
    expect(invoke).toHaveBeenCalledWith('attachment_control', { id: 'forgotten-1', action: 'restore', sessionId: 'session-A' });
    expect(screen.queryByRole('button', { name: 'Forget old.txt' })).toBeNull();
  });
  it('rejects unsupported, empty and oversized inputs before transport', () => {
    expect(validateSelectedFile({ name: 'invoice.exe', size: 100, type: 'text/plain' })).toContain('Supported formats');
    expect(validateSelectedFile({ name: 'invoice.pdf', size: 0, type: 'application/pdf' })).toContain('empty');
    expect(validateSelectedFile({ name: 'invoice.pdf', size: 21 * 1024 * 1024, type: 'application/pdf' })).toContain('20 MiB');
    expect(validateSelectedFile({ name: 'BOOK.XLSX', size: 200, type: '' })).toBeNull();
  });
  it('ties pasted content, reversible forgetting and artifact opening to the selected conversation', async () => {
    render(<ConversationFiles sessionId="session-A" ensureSession={async () => 'session-A'}/>);
    fireEvent.paste(window, { clipboardData: { files: [selected()] } });
    await waitFor(() => expect(screen.getByText('sample.csv')).toBeTruthy());
    expect(vi.mocked(invoke).mock.calls.find(([command]) => command === 'attach_bytes')?.[1]).toMatchObject({ sessionId: 'session-A', name: 'sample.csv', bytes: expect.any(Array), retention: 'conversation' });
    fireEvent.click(screen.getByText('sample.csv'));
    expect(screen.getByText(/<script>steal\(\)<\/script>/)).toBeTruthy();
    expect(document.querySelector('script')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Close preview' }));
    fireEvent.click(screen.getByRole('button', { name: 'Forget sample.csv' }));
    await waitFor(() => expect(vi.mocked(invoke).mock.calls.find(([command]) => command === 'attachment_control')?.[1]).toEqual({ id: 'file-1', action: 'forget', sessionId: 'session-A' }));
    fireEvent.click(screen.getByRole('button', { name: 'Open' }));
    expect(vi.mocked(invoke).mock.calls.find(([command]) => command === 'artifact_control')?.[1]).toEqual({ id: 'output-1', action: 'open', sessionId: 'session-A' });
  });
  it('reports chooser failures and dropped-file extraction failures without claiming availability', async () => {
    render(<ConversationFiles sessionId="session-A" ensureSession={async () => 'session-A'}/>);
    fireEvent.click(screen.getByRole('button', { name: '＋ Attach' }));
    await waitFor(() => expect(screen.getByText(/damaged.pdf: Invalid PDF structure/)).toBeTruthy());
    state.error = true;
    fireEvent.drop(window, { dataTransfer: { files: [selected()] } });
    await waitFor(() => expect(screen.getByText(/sample.csv: Error: Document is encrypted/)).toBeTruthy());
    expect(screen.queryByText('sample.csv')).toBeNull();
  });
});
