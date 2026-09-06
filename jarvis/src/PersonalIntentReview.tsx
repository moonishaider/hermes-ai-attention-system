import { useRef, useState } from 'react';
import { invoke } from './transport';
import type { ConversationRun } from './conversationRuns';
export interface PersonalIntent {
 action_type?: string; account?: string; conflicts?: unknown[]; undoAvailable?: boolean;
 preview?: { operation?: string; timezone?: string; event?: {summary?: string; description?: string; location?: string; start?: {dateTime?: string}; end?: {dateTime?: string}}; subject?: string; recipient?: string; body?: string; attachment_ids?: string[] };
 result?: { provider_id?: string; resource_kind?: string; change_id?: string };
}
export function PersonalIntentReview({run, refresh, undo}: {run?: ConversationRun; refresh:()=>Promise<void>; undo:(receipt:PersonalIntent)=>Promise<void>}) {
 const [busy,setBusy]=useState(false); const [error,setError]=useState(''); const lock=useRef(false);
 const action=run?.pendingAction; const receipt=run?.actionReceipt;
 if (!run || (!action && !receipt?.undoAvailable)) return null;
 async function confirm(confirmed:boolean) {
  if (!run?.runId || lock.current) return; lock.current=true;setBusy(true);setError('');
  try {await invoke('confirm_personal_intent',{runId:run.runId,confirm:confirmed}); await refresh();}
  catch(e){setError(`Action needs attention: ${String(e)}`);} finally{lock.current=false;setBusy(false);}
 }
 const preview=action?.preview; const event=preview?.event;
 return <section className="run-recovery personal-intent-review" role="status">{action ? <><strong>Review this personal action</strong><p>{(action.action_type ?? preview?.operation ?? 'Personal action').replaceAll('.',' · ')} · {action.account || 'Personal account'}</p>{event && <dl>{event.summary && <><dt>Event</dt><dd>{event.summary}</dd></>}{event.start?.dateTime && <><dt>Starts</dt><dd>{event.start.dateTime} · {preview?.timezone}</dd></>}{event.end?.dateTime && <><dt>Ends</dt><dd>{event.end.dateTime}</dd></>}{event.location && <><dt>Location</dt><dd>{event.location}</dd></>}{event.description && <><dt>Description</dt><dd>{event.description}</dd></>}</dl>}{preview?.subject !== undefined && <dl><dt>Unsent draft subject</dt><dd>{preview.subject}</dd><dt>Recipient</dt><dd>{preview.recipient || 'No recipient'}</dd><dt>Body</dt><dd className="preserve-whitespace">{preview.body}</dd></dl>}{Boolean(action.conflicts?.length) && <p className="notice">{action.conflicts!.length} calendar conflict(s) overlap this event.</p>}<p>Confirmation applies only to this prepared action. Drafts remain unsent.</p><button type="button" disabled={busy} onClick={()=>void confirm(true)}>Confirm this action</button><button type="button" className="quiet" disabled={busy} onClick={()=>void confirm(false)}>Cancel this action</button></> : receipt?.result?.provider_id && <><strong>Personal action saved</strong><button type="button" className="quiet" disabled={busy || run.persistencePending || run.phase !== 'completed'} onClick={()=>void undo(receipt)}>Undo this exact event</button></>}{error && <p role="alert">{error}</p>}</section>;
}
