import type { ContextId, RunEvent } from './types';

export type TurnPhase = 'submitting' | 'running' | 'cancelling' | 'completed' | 'cancelled' | 'failed' | 'interrupted' | 'unresolved' | 'waiting_action';
export interface ConversationRun {
  turnId: string;
  sessionId: string;
  runId: string | null;
  context: ContextId;
  phase: TurnPhase;
  answer: string;
  progress: string[];
  startedAt: number;
  route: string;
  speak: boolean;
  seenEvents: string[];
  lastSequence: number;
  persistencePending?: boolean;
  reportRecovery?: { kind: 'known-incomplete' | 'retained-response' | 'final-incomplete'; sourceRunId?: string; newTurnId?: string };
  pendingAction?: import("./PersonalIntentReview").PersonalIntent;
  actionReceipt?: import("./PersonalIntentReview").PersonalIntent;
  revisionPending?: boolean;
  previousDrafts?: string[];
}
export type RunLedger = Record<string, ConversationRun>;
export const runLedgerKey = (sessionId: string, turnId: string) => `${sessionId}:${turnId}`;
export const isRunActive = (run?: ConversationRun) => Boolean(run && (run.persistencePending || run.reportRecovery || ['submitting', 'running', 'cancelling', 'unresolved', 'waiting_action'].includes(run.phase)));
export function sessionRun(ledger: RunLedger, sessionId: string | null) {
  return Object.values(ledger).filter(run => run.sessionId === sessionId).sort((a, b) => b.startedAt - a.startedAt)[0];
}
export function eventOwner(ledger: RunLedger, event: RunEvent) {
  const candidates = Object.values(ledger).filter(run => event.turn_id ? run.turnId === event.turn_id && (!event.session_id || run.sessionId === event.session_id) : run.runId === event.run_id);
  const candidate = candidates.length === 1 ? candidates[0] : undefined;
  if (!candidate) return undefined;
  if (event.session_id && event.session_id !== candidate.sessionId) return undefined;
  if (event.turn_id && event.turn_id !== candidate.turnId) return undefined;
  // A child reviewer has a distinct provider run ID, while root_run_id stays stable.
  if (candidate.runId && (event.root_run_id ?? event.run_id) !== candidate.runId) return undefined;
  return candidate;
}
export function applyRunEvent(ledger: RunLedger, event: RunEvent): RunLedger {
  const owner = eventOwner(ledger, event);
  if (!owner || !isRunActive(owner)) return ledger;
  if (['completed','cancelled','failed','interrupted'].includes(owner.phase) && !['run.completed','run.cancelled','run.failed','run.interrupted'].includes(event.event)) return ledger;
  if (event.event_id && owner.seenEvents.includes(event.event_id)) return ledger;
  if (event.sequence !== undefined && event.sequence <= owner.lastSequence) return ledger;
  const next = { ...owner, progress: [...owner.progress], seenEvents: [...owner.seenEvents] };
  if (event.event_id) next.seenEvents = [...next.seenEvents.slice(-511), event.event_id];
  if (event.sequence !== undefined) next.lastSequence = event.sequence;
  if (!next.runId) next.runId = event.root_run_id ?? event.run_id ?? null;
  if (event.event === 'message.delta' && event.delta) {
    if (next.revisionPending) {
      next.previousDrafts = [...(next.previousDrafts ?? []), next.answer].filter(Boolean);
      next.answer = ''; next.revisionPending = false;
    }
    next.answer += event.delta;
  }
  if (event.event === 'governor.review_started' || event.event === 'governor.escalation_started') {
    next.route = event.route ?? next.route;
    next.revisionPending = true;
    next.progress.push(event.event === 'governor.review_started' ? 'Reviewing the result independently' : 'Taking a deeper look');
    // Keep the previous draft visible until the next pass provides text.
  }
  if (['run.completed', 'run.failed', 'run.cancelled', 'run.interrupted'].includes(event.event) && event.output !== undefined) next.answer = event.output;
  if (['run.completed', 'run.cancelled', 'run.failed', 'run.interrupted'].includes(event.event)) next.persistencePending = event.persistence_pending === true;
  if (event.event === 'action.preview') { next.phase = 'waiting_action'; next.pendingAction = event.action; }
  if (event.actionReceipt) next.actionReceipt = event.actionReceipt;
  if (['run.completed','run.failed','run.cancelled','run.interrupted','run.unresolved'].includes(event.event)) next.pendingAction = undefined;
  if (event.event === 'run.unresolved') { next.phase = 'unresolved'; next.progress.push('Earlier request needs recovery · do not repeat the action automatically'); }
  if (event.event === 'run.completed') {
    if (event.output !== undefined) next.answer = event.output;
    next.phase = 'completed';
    const tokens = event.usage?.total_tokens ?? (event.usage ? (event.usage.input_tokens ?? 0) + (event.usage.output_tokens ?? 0) : null);
    next.progress.push(`Completed · ${((Date.now() - owner.startedAt) / 1000).toFixed(1)}s${tokens === null ? ' · usage unavailable' : ` · ${tokens} tokens`}`);
  }
  if (event.event === 'run.cancelled') {
    next.phase = 'cancelled';
    next.progress.push('Cancelled · partial text is a recoverable draft; provider usage may be unknown');
  }
  if (event.event === 'run.failed' || event.event === 'run.interrupted') {
    next.phase = event.event === 'run.interrupted' ? 'interrupted' : 'failed';
    next.progress.push('Interrupted · any partial text is incomplete. Check the saved result before retrying actions.');
  }
  if (event.event === 'tool.started' || event.event === 'tool.completed') {
    const name = event.tool || event.name || 'approved source';
    const label = `${event.event === 'tool.completed' ? 'Checked' : 'Checking'} ${name.replace(/_/g, ' ')}`;
    next.progress = [...next.progress.filter(line => line !== label).slice(-11), label];
  }
  if (event.persistence_pending) next.persistencePending = true;
  if (event.persistence_pending) next.progress.push('Result retained · canonical save needs recovery; do not resubmit the action');
  if (event.error) next.progress.push(`Needs attention: ${event.error}`);
  const key = Object.keys(ledger).find(key => ledger[key] === owner)!;
  return { ...ledger, [key]: next };
}
