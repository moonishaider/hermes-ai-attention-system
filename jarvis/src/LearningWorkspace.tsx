import { useEffect, useState } from 'react';
import { invoke } from './transport';

interface Skill { name: string; content: string; hash: string; pinned: boolean; owner_editable: boolean; }
interface Snapshot {
  native_pending: Array<{ id: string; summary: string; origin?: string; payload?: { content?: string; action?: string; old_text?: string } }>;
  native_confirmed: { memory: string[]; user: string[] };
  preferences: Array<{ preference_id: string; text: string; status: string; created_at: string }>;
  skills: Skill[];
  project_memory?: Array<ProjectMemory & { review_hash?: string }>;
}
interface SkillPreview { before_hash: string; allowed: boolean; diff: string; issues: string[]; }
const workspace = <T,>(operation: string, request: Record<string, unknown> = {}) => invoke<T>('workspace_operation', { operation, request });
interface ProjectMemory { memory_id: string; statement: string; status: string; namespace: string; created_at: string; }
export function LearningWorkspace({ projectItems: legacyProjectItems = [], onProjectReview }: { projectItems?: ProjectMemory[]; onProjectReview?: (id: string, action: "confirmed" | "superseded" | "rejected") => Promise<void> }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [preference, setPreference] = useState('');
  const [selection, setSelection] = useState<{ token: string; summary: string } | null>(null);
  const [skillName, setSkillName] = useState('');
  const [skillContent, setSkillContent] = useState('');
  const [preview, setPreview] = useState<SkillPreview | null>(null);
  const [version, setVersion] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const projectItems = snapshot?.project_memory ?? legacyProjectItems;
  async function refresh() { setSnapshot(await workspace<Snapshot>('learning.snapshot')); }
  useEffect(() => { void refresh().catch(error => setNotice(`Learning unavailable: ${String(error)}`)); }, []);
  async function perform(work: () => Promise<void>) {
    if (busy) return;
    setBusy(true); setNotice('');
    try { await work(); } catch (error) { setNotice(String(error)); } finally { setBusy(false); }
  }
  async function selectPending(id: string) {
    await perform(async () => {
      const item = await workspace<{ selection?: string; selectionToken?: string; summary: string }>('learning.select-native', { pendingId: id });
      const token = item.selectionToken ?? item.selection;
      if (!token) throw new Error('No review selection was returned. Nothing was approved.');
      setSelection({ token, summary: item.summary });
    });
  }
  async function resolve(action: 'approve' | 'reject') {
    if (!selection) return;
    await perform(async () => {
      const result = await workspace<{ ok: boolean; result?: string }>('learning.resolve-native', { selectionToken: selection.token, action });
      if (!result.ok) throw new Error(result.result || 'The memory review did not complete.');
      setSelection(null); await refresh(); setNotice(action === 'approve' ? 'This selected memory was kept.' : 'This selected proposal was rejected.');
    });
  }
  return <section className="learning-workspace">
    <div className="workspace-intro"><h2>What Jarvis remembers</h2><p>Review suggestions, save your preferences, and edit the procedures Jarvis uses. Existing uncertain proposals stay pending until you choose one.</p><button className="quiet" disabled={busy} onClick={() => void perform(refresh)}>Refresh</button></div>
    {notice && <p className="workspace-notice" role="status">{notice}</p>}
    <div className="management-columns"><section className="card surface"><p className="eyebrow">Preferences</p><h3>Make it yours</h3><form className="local-create" onSubmit={event => { event.preventDefault(); void perform(async () => {
      const result = await workspace<{ status: string }>('learning.save-preference', { text: preference, provenance: { source: 'owner-ui', surface: 'learning' } });
      setPreference(''); await refresh(); setNotice(result.status === 'confirmed' ? 'Preference saved to native memory. Undo is available below.' : 'Saved for review. This could change authority or contains an uncertain fact.');
    }); }}><label>Your preference<textarea value={preference} maxLength={1000} onChange={event => setPreference(event.target.value)} placeholder="For example: keep ordinary answers concise."/></label><button disabled={busy || !preference.trim()}>Save preference</button></form>
      <div className="item-list">{snapshot?.preferences.map(item => <article key={item.preference_id}><strong>{item.text}</strong><p>{item.status} · {item.created_at.slice(0, 10)}</p>{item.status === 'confirmed' && <button className="quiet" disabled={busy} onClick={() => void perform(async () => { await workspace('learning.undo-preference', { preferenceId: item.preference_id }); await refresh(); setNotice('Preference undone in native memory.'); })}>Undo preference</button>}</article>)}</div>
      <details><summary>Current native memory</summary>{[...(snapshot?.native_confirmed.user ?? []), ...(snapshot?.native_confirmed.memory ?? [])].map((text, index) => <p className="native-memory" key={index}>{text}</p>)}</details>
    </section><section className="card surface"><p className="eyebrow">Needs your review</p><h3>{snapshot ? `${snapshot.native_pending.length} pending suggestion${snapshot.native_pending.length === 1 ? '' : 's'}` : 'Loading suggestions…'}</h3>
      {!snapshot?.native_pending.length && snapshot && <p>No native pending suggestions. Confirmed memories are shown separately.</p>}
      <div className="item-list">{snapshot?.native_pending.map(item => <article key={item.id}><strong>{item.summary || item.payload?.content || 'Memory proposal'}</strong><p>{item.origin ?? 'Native Hermes'} · pending</p>{item.payload?.content && <details><summary>Proposed content</summary><p>{item.payload.content}</p>{item.payload.old_text && <p>Replaces: {item.payload.old_text}</p>}</details>}<button className="quiet" disabled={busy} onClick={() => void selectPending(item.id)}>Review this suggestion</button></article>)}</div>
      {selection && <div className="review-selection" role="dialog" aria-label="Review selected memory"><h3>Keep this memory?</h3><p>{selection.summary}</p><div className="focus-controls"><button disabled={busy} onClick={() => void resolve('approve')}>Keep selected memory</button><button className="quiet" disabled={busy} onClick={() => void resolve('reject')}>Reject selected memory</button><button className="quiet" onClick={() => setSelection(null)}>Close review</button></div><small>This choice applies only to the selected content. If it changes, review it again.</small></div>}
    </section></div>
    {projectItems.length > 0 && <section className="card surface"><p className="eyebrow">Project learning</p><h3>Scoped proposals and facts</h3><div className="item-list">{projectItems.map(item => <article key={item.memory_id}><strong>{item.statement}</strong><p>{item.namespace} · {item.status} · {item.created_at.slice(0, 10)}</p><div className="focus-controls">{([['confirmed', 'Keep'], ['superseded', 'Archive'], ['rejected', 'Reject']] as const).map(([action, label]) => <button className="quiet" key={action} disabled={busy || !onProjectReview} onClick={() => void perform(async () => { if ('review_hash' in item && item.review_hash && item.status === 'proposed' && action !== 'superseded') {
        await workspace('learning.resolve-project', { memoryId: item.memory_id, action: action === 'confirmed' ? 'approve' : 'reject', expectedHash: item.review_hash }); await refresh();
      } else await onProjectReview?.(item.memory_id, action); setNotice(`Project memory updated: ${label.toLowerCase()}.`); })}>{label}</button>)}</div></article>)}</div></section>}
    <section className="card surface skill-workspace"><p className="eyebrow">Skills and specialists</p><h2>Teach a repeatable procedure</h2><p>Instructions are versioned and scanned before activation. Editing a skill cannot extend permissions, add credentials, or deploy code.</p><button className="quiet" onClick={() => { setEditing(true); setSkillName(''); setSkillContent('---\nname: my-procedure\ndescription: A personal procedure\n---\n\n# Procedure\n\n'); setPreview(null); setVersion(null); }}>New personal skill</button><div className="skill-list">{snapshot?.skills.map(skill => <button className="quiet" key={skill.name} onClick={() => { setEditing(true); setSkillName(skill.name); setSkillContent(skill.content); setPreview(null); setVersion(null); }}><strong>{skill.name.replaceAll('-', ' ')}</strong><small>{skill.pinned ? 'Pinned · owner editable' : 'Personal skill'}</small></button>)}</div>
      {editing && <form className="skill-editor" onSubmit={event => { event.preventDefault(); void perform(async () => setPreview(await workspace<SkillPreview>('learning.skill-preview', { name: skillName, content: skillContent }))); }}><label>Skill name<input value={skillName} onChange={event => { setSkillName(event.target.value); setPreview(null); }} pattern="[a-z0-9][a-z0-9_-]{0,79}" placeholder="weekly-review" required/></label><label>Instructions<textarea value={skillContent} onChange={event => { setSkillContent(event.target.value); setPreview(null); }} rows={14} maxLength={30000}/></label><div className="focus-controls"><button disabled={busy || !skillName.trim()}>Review changes</button><button type="button" className="quiet" onClick={() => setEditing(false)}>Close editor</button></div></form>}
      {preview && <section className="skill-diff"><h3>{preview.allowed ? 'Changes ready for your review' : 'This version needs correction'}</h3>{preview.issues.map(issue => <p key={issue}>{issue}</p>)}<pre>{preview.diff || 'No content changes.'}</pre>{preview.allowed && preview.diff && <button disabled={busy} onClick={() => void perform(async () => { const result = await workspace<{ version_id: string }>('learning.skill-edit', { name: skillName, content: skillContent, expectedHash: preview.before_hash }); setVersion(result.version_id); setPreview(null); await refresh(); setNotice('Skill saved and native scan passed. Future tasks can use this version.'); })}>Save this version</button>}</section>}
      {version && <button className="quiet" disabled={busy} onClick={() => void perform(async () => { await workspace('learning.skill-rollback', { versionId: version }); setVersion(null); await refresh(); setNotice('Previous skill version restored.'); })}>Restore previous version</button>}
    </section>
  </section>;
}
