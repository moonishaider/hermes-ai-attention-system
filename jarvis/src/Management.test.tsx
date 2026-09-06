vi.mock('@tauri-apps/api/event',()=>({listen:vi.fn(async()=>()=>{})}));
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
const state = vi.hoisted(() => ({ resolved: false, conflict: false, runFailed: false }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn(async (_command: string, args: { operation: string; request: Record<string, unknown> }) => {
  switch (args.operation) {
    case 'learning.snapshot': return { native_pending: state.resolved ? [] : [{ id: 'native-exact-id', summary: 'Prefer prose for short explanations', origin: 'foreground', payload: { content: 'Prefer prose for short explanations' } }], native_confirmed: { memory: ['Existing durable fact'], user: [] }, preferences: [], skills: [{ name: 'review', content: '---\nname: review\ndescription: Review notes\n---\nRead notes.', hash: 'initial-hash', pinned: true, owner_editable: true }] };
    case 'learning.select-native': return { selection: 'trusted-selection-receipt', summary: 'Prefer prose for short explanations' };
    case 'learning.resolve-native': state.resolved = true; return { ok: true };
    case 'learning.skill-preview': return { before_hash: 'fresh-base-hash', allowed: true, diff: '+Updated procedure', issues: [] };
    case 'learning.skill-edit': if (state.conflict) throw new Error('skill changed; review the latest diff'); return { version_id: 'saved-version' };
    case 'capabilities.list': return { data: [{ capability_id: 'workflow-1', kind: 'workflow', status: 'draft', spec: { name: 'Monday review', description: 'Collect tasks and save the review.', context_id: 'personal', tools: ['list_tasks','save_output'], steps: [{ id: 'tasks', tool: 'list_tasks', args: {} }, { id: 'output', tool: 'save_output', args: { content: { from_step: 'tasks' } } }] } }] };
    case 'jobs.list': return { data: [], lifecycle: 'off' };
    case 'capabilities.run': return { run_id: 'execution-1', mode: args.request.mode, status: state.runFailed ? 'failed' : 'completed', evidence_class: args.request.mode === 'dry' ? 'fixture/simulation' : 'local source execution', error: state.runFailed ? 'Source query failed' : undefined, steps: [{ id: 'tasks', tool: 'list_tasks', status: state.runFailed ? 'failed' : 'completed', output: [{ title: 'Review task' }] }], outputs: { tasks: [{ title: 'Review task' }] } };
    case 'capabilities.create': return { capability_id: 'new-workflow' };
    default: return { ok: true };
  }
}) }));
import { invoke } from '@tauri-apps/api/core';
import { LearningWorkspace } from './LearningWorkspace';
import { AutomationWorkspace, makeWorkflow } from './AutomationWorkspace';
const calls = (operation: string) => vi.mocked(invoke).mock.calls.filter(([, args]) => (args as Record<string, unknown>)?.operation === operation);
afterEach(() => { cleanup(); vi.clearAllMocks(); state.resolved = false; state.conflict = false; state.runFailed = false; });

describe('owner-managed learning and execution', () => {
  it('lists native history without approval; resolves only a selected owner-reviewed item', async () => {
    render(<LearningWorkspace/>);
    await waitFor(() => expect(screen.getByText('1 pending suggestion')).toBeTruthy());
    expect(calls('learning.select-native')).toHaveLength(0); expect(calls('learning.resolve-native')).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: 'Review this suggestion' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Keep selected memory' })).toBeTruthy());
    expect(calls('learning.resolve-native')).toHaveLength(0);
    fireEvent.click(screen.getByRole('button', { name: 'Keep selected memory' }));
    await waitFor(() => expect(screen.getByText('0 pending suggestions')).toBeTruthy());
    expect(calls('learning.resolve-native')[0][1]).toEqual({ operation: 'learning.resolve-native', request: { selectionToken: 'trusted-selection-receipt', action: 'approve' } });
    expect(screen.queryByText('trusted-selection-receipt')).toBeNull();
  });
  it('invalidates the reviewed skill diff on edits and surfaces concurrent native changes', async () => {
    render(<LearningWorkspace/>);
    await waitFor(() => expect(screen.getByText('review').closest('button')!).toBeTruthy());
    fireEvent.click(screen.getByText('review').closest('button')!);
    fireEvent.click(screen.getByRole('button', { name: 'Review changes' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save this version' })).toBeTruthy());
    fireEvent.change(screen.getByLabelText('Instructions'), { target: { value: 'Edited again' } });
    expect(screen.queryByRole('button', { name: 'Save this version' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Review changes' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save this version' })).toBeTruthy());
    state.conflict = true; fireEvent.click(screen.getByRole('button', { name: 'Save this version' }));
    await waitFor(() => expect(screen.getByText(/skill changed; review the latest diff/)).toBeTruthy());
    expect(calls('learning.skill-edit')[0][1]).toEqual({ operation: 'learning.skill-edit', request: { name: 'review', content: 'Edited again', expectedHash: 'fresh-base-hash' } });
    expect(screen.queryByText(/Skill saved and native scan passed/)).toBeNull();
  });
  it('builds actual dependency references and rejects an empty operation plan', () => {
    const spec = makeWorkflow('Review', 'Find unsettled decisions', 'personal', 'planning decision', true);
    expect(spec.steps.map(step => step.tool)).toEqual(['list_tasks', 'search_evidence', 'save_output']);
    expect(spec.steps[2].args.content).toMatchObject({ tasks: { from_step: 'tasks' }, evidence: { from_step: 'evidence' } });
    expect(() => makeWorkflow('Empty','No sources','personal','',false)).toThrow('Choose tasks');
  });
  it('executes fixtures through the adapter and labels shadow failure as failure, not no-change', async () => {
    render(<AutomationWorkspace context="personal" view="Radars"/>);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Open procedure' })).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Open procedure' }));
    fireEvent.click(screen.getByRole('button', { name: 'Run synthetic fixtures' }));
    await waitFor(() => expect(screen.getByText('fixture/simulation · dry')).toBeTruthy());
    expect(calls('capabilities.run')[0][1]).toMatchObject({ request: { capabilityId: 'workflow-1', mode: 'dry', fixtures: { tasks: expect.any(Array) } } });
    state.runFailed = true; fireEvent.click(screen.getByRole('button', { name: 'Run read-only shadow' }));
    await waitFor(() => expect(screen.getByText('Execution failed')).toBeTruthy());
    expect(screen.getByRole('alert').textContent).toBe('Source query failed');
    expect(calls('capabilities.run')[1][1]).toEqual({ operation: 'capabilities.run', request: { capabilityId: 'workflow-1', mode: 'shadow' } });
    expect(screen.queryByText('no-change')).toBeNull();
  });
});
