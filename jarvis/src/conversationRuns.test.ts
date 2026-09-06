import { describe, expect, it } from 'vitest';
import { applyRunEvent, isRunActive, sessionRun, type ConversationRun } from './conversationRuns';
const turn = (id: string, sessionId: string): ConversationRun => ({
  turnId: id, sessionId, runId: `run-${id}`, context: 'unknown', phase: 'running',
  answer: '', progress: [], startedAt: 1000, route: 'routine', speak: false,
  seenEvents: [], lastSequence: -1,
});
describe('transactional event reducer holdouts', () => {
  it('rejects unowned, mismatched session, mismatched root, duplicate and late terminal events', () => {
    const original = { a: turn('a', 'A'), b: turn('b', 'B') };
    for (const event of [
      { event: 'message.delta', run_id: 'foreign', delta: 'bad' },
      { event: 'message.delta', run_id: 'run-a', session_id: 'B', delta: 'bad' },
      { event: 'message.delta', run_id: 'run-b', turn_id: 'a', delta: 'bad' },
    ]) expect(applyRunEvent(original, event)).toBe(original);
    const event = { event: 'message.delta', run_id: 'run-a', session_id: 'A', turn_id: 'a', sequence: 3, event_id: 'delta3', delta: 'part' };
    const added = applyRunEvent(original, event);
    expect(added.a.answer).toBe('part'); expect(added.b).toBe(original.b);
    expect(applyRunEvent(added, event)).toBe(added);
    const cancelled = applyRunEvent(added, { ...event, event: 'run.cancelled', sequence: 4, event_id: 'cancel4' });
    expect(cancelled.a.answer).toBe('part'); expect(cancelled.a.phase).toBe('cancelled');
    expect(applyRunEvent(cancelled, { ...event, event: 'run.completed', output: 'late complete', sequence: 5, event_id: 'late5' })).toBe(cancelled);
    expect(isRunActive(cancelled.b)).toBe(true);
  });
  it('binds an early event to the submitting turn before IPC submission returns', () => {
    const pending = { ...turn('a', 'A'), runId: null, phase: 'submitting' as const };
    const ledger = applyRunEvent({ a: pending }, { event: 'run.completed', run_id: 'actual', session_id: 'A', turn_id: 'a', sequence: 1, output: 'Fast result' });
    expect(ledger.a).toMatchObject({ runId: 'actual', phase: 'completed', answer: 'Fast result' });
  });
  it('keeps original text visible while independent review is running and accepts empty final output explicitly', () => {
    const original = { a: { ...turn('a', 'A'), answer: 'Original draft' } };
    const reviewing = applyRunEvent(original, { event: 'governor.review_started', run_id: 'run-a', sequence: 1 });
    expect(reviewing.a.answer).toBe('Original draft');
    const final = applyRunEvent(reviewing, { event: 'run.completed', run_id: 'run-a', sequence: 2, output: '' });
    expect(final.a.answer).toBe(''); expect(final.a.phase).toBe('completed');
  });
  it('selects the latest originating turn without changing a different conversation', () => {
    const ledger = { a: turn('a', 'A'), b: turn('b', 'B'), c: { ...turn('c', 'A'), startedAt: 2000 } };
    expect(sessionRun(ledger, 'A')?.turnId).toBe('c');
    expect(sessionRun(ledger, null)).toBeUndefined();
  });
});

describe('unresolved outcomes and cross-window identity holdouts', () => {
  it('keeps unknown provider outcomes and pending persistence active until exact recovery', () => {
    const base = { a: turn('a', 'A') };
    const unknown = applyRunEvent(base, { event: 'run.unresolved', run_id: 'run-a', session_id: 'A', turn_id: 'a', sequence: 1 });
    expect(unknown.a.phase).toBe('unresolved'); expect(isRunActive(unknown.a)).toBe(true);
    const failedSave = applyRunEvent(unknown, { event: 'run.failed', run_id: 'run-a', session_id: 'A', turn_id: 'a', sequence: 2, output: 'Retained answer', persistence_pending: true });
    expect(failedSave.a.answer).toBe('Retained answer'); expect(isRunActive(failedSave.a)).toBe(true);
    const saved = applyRunEvent(failedSave, { event: 'run.completed', run_id: 'run-a', session_id: 'A', turn_id: 'a', sequence: 3, output: 'Retained answer' });
    expect(isRunActive(saved.a)).toBe(false); expect(saved.a.persistencePending).toBe(false);
  });
  it('distinguishes the same client turn token in two sessions and rejects ambiguous ownership', () => {
    const a = { ...turn('shared', 'A'), runId: 'run-A' };
    const b = { ...turn('shared', 'B'), runId: 'run-B' };
    const base = { 'A:shared': a, 'B:shared': b };
    const changed = applyRunEvent(base, { event: 'message.delta', run_id: 'run-A', session_id: 'A', turn_id: 'shared', sequence: 1, delta: 'Only A' });
    expect(changed['A:shared'].answer).toBe('Only A'); expect(changed['B:shared']).toBe(b);
    expect(applyRunEvent(base, { event: 'message.delta', run_id: 'run-A', turn_id: 'shared', delta: 'Ambiguous' })).toBe(base);
  });
});
