import { useEffect, useState } from 'react';
import { invoke } from './transport';
interface Profile { id: string; label: string; account_id: string; profile: string; app?: string; context_id?: string; configured_only?: boolean; }
interface Grant { grant_id: string; title: string; context_id: string; account_id: string; profile: string; operations: string[]; domains: string[]; apps: string[]; resources: string[]; standing: boolean; expires_at: string; status: string; last_used?: string; expired: boolean; last_audit?: { result: string; created_at: string; operation?: string }; }
interface Snapshot { grants: Grant[]; stops: Array<{ capability: string; stopped: boolean | number }>; profiles: Profile[]; }
const operations = [
  ['browser.read', 'Read web pages'], ['browser.navigate', 'Navigate public pages'], ['browser.form', 'Prepare a personal form'], ['browser.download', 'Download selected files'], ['apps.open', 'Open selected apps'],
  ['calendar.create', 'Create personal events'], ['calendar.update', 'Edit personal events'], ['calendar.undo', 'Undo owned event changes'], ['draft.create', 'Create unsent drafts'], ['draft.read', 'Read personal drafts'], ['draft.update', 'Edit unsent drafts'],
  ['files.analyze', 'Analyze selected files'], ['artifacts.create', 'Generate private documents'], ['memory.preference', 'Save ordinary preferences'], ['skills.edit', 'Edit personal skills'], ['jobs.local', 'Run local workflows'], ['finance.prepare', 'Prepare financial records'],
] as const;
const label = (operation: string) => operations.find(([id]) => id === operation)?.[1] ?? operation;
async function permissions<T>(operation: string, request: Record<string, unknown> = {}): Promise<T> {
  const value = await invoke<T | { ok: boolean; result: T; error?: string }>('permissions_operation', { operation, request });
  if (value && typeof value === 'object' && 'ok' in value && 'result' in value) {
    if (!value.ok) throw new Error(value.error || 'Permission operation did not complete.');
    return value.result;
  }
  return value as T;
}
export function PermissionsWorkspace() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState('');
  const [profileId, setProfileId] = useState('');
  const [selected, setSelected] = useState<string[]>(['browser.read']);
  const [domains, setDomains] = useState('');
  const [apps, setApps] = useState('');
  const [folder, setFolder] = useState<{ path: string; displayName: string } | null>(null);
  const [standing, setStanding] = useState(false);
  const [hours, setHours] = useState('12');
  const profile = snapshot?.profiles.find(item => item.id === profileId);
  const profileContext = profile?.context_id ?? (profile?.account_id === 'public' ? 'personal' : 'unknown');
  const allStopped = Boolean(snapshot?.stops.find(item => item.capability === 'all')?.stopped);
  async function refresh() {
    const value = await permissions<Snapshot>('snapshot');
    if (!Array.isArray(value?.profiles) || !Array.isArray(value?.grants) || !Array.isArray(value?.stops)) throw new Error('Permission service returned an incomplete snapshot.');
    setSnapshot(value);
    setProfileId(old => value.profiles.some(item => item.id === old) ? old : value.profiles[0]?.id ?? '');
  }
  useEffect(() => { void refresh().catch(error => setNotice(`Permission state unavailable: ${String(error)}`)); }, []);
  async function perform(work: () => Promise<void>) {
    if (busy) return; setBusy(true); setNotice('');
    try { await work(); } catch (error) { setNotice(String(error)); } finally { setBusy(false); }
  }
  return <section className="permissions-workspace"><div className="workspace-intro"><p className="eyebrow">Permissions Centre</p><h2>Useful authority, clearly scoped</h2><p>Give Jarvis a task or a standing grant for specific accounts, apps and resources. Each action still verifies its real target. Grants cannot authorize messages, payments, final filing or company writes.</p><div className="focus-controls"><button className="quiet" disabled={busy} onClick={() => void perform(refresh)}>Refresh permissions</button><button className={allStopped ? 'quiet' : 'danger'} disabled={busy} onClick={() => void perform(async () => { await permissions('stop', { capability: 'all', stopped: !allStopped }); await refresh(); setNotice(allStopped ? 'Emergency stop lifted. Individual grants still apply.' : 'Emergency stop enabled for these personal capabilities. Your conversations and saved evidence remain available.'); })}>{allStopped ? 'Lift emergency stop' : 'Stop personal actions'}</button></div></div>
    {notice && <p className="workspace-notice" role="status">{notice}</p>}
    <div className="management-columns"><section className="card surface"><h3>Task and standing grants</h3>{snapshot && !snapshot.grants.length && <p>No grants are saved here yet. Start with the task you want Jarvis to complete. Provider credentials and existing Calendar/draft settings are shown separately below.</p>}<div className="item-list">{snapshot?.grants.map(grant => <article key={grant.grant_id}><strong>{grant.title}</strong><p>{grant.expired ? 'Expired' : grant.status} · {grant.standing ? 'Standing grant' : 'Task grant'}<br/>{grant.account_id} · {grant.profile} · {grant.context_id}</p><p>{grant.operations.map(label).join(' · ')}</p><small>Expires {new Date(grant.expires_at).toLocaleString()}</small><p>{grant.last_audit ? `Last executor result: ${grant.last_audit.result} · ${new Date(grant.last_audit.created_at).toLocaleString()}` : 'No executed outcome is recorded for this grant.'}{grant.last_used && <><br/>Last authorization check: {new Date(grant.last_used).toLocaleString()}</>}</p><details><summary>Exact task scope</summary><p>Domains: {grant.domains.length ? grant.domains.join(', ') : 'Public hosts subject to runtime checks'}</p><p>Apps: {grant.apps.length ? grant.apps.join(', ') : 'None selected'}</p><p>Resources: {grant.resources.length ? grant.resources.join(', ') : 'None selected'}</p></details>{grant.status === 'active' && !grant.expired && <button className="quiet" disabled={busy} onClick={() => void perform(async () => { await permissions('revoke', { grant_id: grant.grant_id }); await refresh(); setNotice('Grant revoked. Completed actions are not undone by revocation.'); })}>Revoke this grant</button>}</article>)}</div></section>
    <section className="card surface"><h3>Authorize a useful task</h3><form className="local-create" onSubmit={event => { event.preventDefault(); if (!profile) return; void perform(async () => {
      await permissions('issue', { title, context_id: profileContext, account_id: profile.account_id, profile: profile.profile, operations: selected, domains: domains.split(/[\s,]+/).filter(Boolean), apps: apps.split(',').map(item => item.trim()).filter(Boolean), resources: folder ? [folder.path] : [], standing, hours: Number(hours) });
      await refresh(); setTitle(''); setNotice('Grant saved. This confirms policy configuration; actual targets and provider results are checked during execution.');
    }); }}><label>What may Jarvis do?<input value={title} onChange={event => setTitle(event.target.value)} placeholder="Compare laptops and prepare a shortlist" required maxLength={200}/></label><label>Account and browser context<select value={profileId} onChange={event => { setProfileId(event.target.value); setSelected(['browser.read']); setFolder(null); }}>{snapshot?.profiles.map(item => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>{profile ? <p className="permission-target">{profile.account_id}<br/>{profile.profile} · {profileContext}<br/><small>Configured mapping · actual signed-in identity must be checked when used.</small></p> : <p>No configured target is available. Public research or a verified account mapping must be configured before issuing a grant.</p>}
      <fieldset className="operation-choices"><legend>Allowed operations</legend>{operations.map(([id, text]) => <label className="checkbox-row" key={id}><input type="checkbox" checked={selected.includes(id)} disabled={profile?.account_id === 'public' ? !['browser.read','browser.download'].includes(id) : profileContext !== 'personal' && id !== 'browser.read'} onChange={event => setSelected(old => event.target.checked ? [...old, id] : old.filter(item => item !== id))}/>{text}</label>)}</fieldset><label>Specific domains, if needed<input value={domains} onChange={event => setDomains(event.target.value)} placeholder="example.com, manufacturer.com"/></label><small>Leave empty for ordinary public research under runtime host checks. New accounts and consequential destinations require separate authority.</small><label>Apps for this task<input value={apps} onChange={event => setApps(event.target.value)} placeholder="Exact app names, separated by commas"/></label>
      <div><button type="button" className="quiet" disabled={busy} onClick={() => void perform(async () => { const selection = await invoke<{ path?: string; displayName?: string; cancelled?: boolean }>('permissions_select_folder'); if (selection.path) setFolder({ path: selection.path, displayName: selection.displayName ?? selection.path.split('/').pop() ?? 'Selected folder' }); })}>Select a folder for this task</button>{folder && <p>{folder.displayName} <button type="button" className="quiet" onClick={() => setFolder(null)}>Remove folder</button></p>}</div><label className="checkbox-row"><input type="checkbox" checked={standing} onChange={event => { setStanding(event.target.checked); setHours(event.target.checked ? '168' : '12'); }}/>Keep a standing grant</label><label>Expires after<select value={hours} onChange={event => setHours(event.target.value)}>{(standing ? [['24','1 day'],['168','7 days'],['720','30 days'],['2160','90 days']] : [['1','1 hour'],['4','4 hours'],['12','12 hours'],['24','24 hours']]).map(([value,text]) => <option value={value} key={value}>{text}</option>)}</select></label><button disabled={busy || !profile || !selected.length || !title.trim()}>Save scoped grant</button></form></section></div>
    <section className="card surface"><h3>Pause individual capabilities</h3><p>A capability stop blocks that operation across these grants. It does not revoke unrelated read or analysis permissions.</p><div className="capability-stop-list">{operations.map(([id,text]) => { const stopped = Boolean(snapshot?.stops.find(item => item.capability === id)?.stopped); return <div className="setting" key={id}><span>{text}<small>{stopped ? 'Stopped' : 'Available only within an active grant'}</small></span><button className="quiet" disabled={busy || !snapshot} onClick={() => void perform(async () => { await permissions('stop', { capability: id, stopped: !stopped }); await refresh(); })}>{stopped ? 'Resume' : 'Stop'}</button></div>; })}</div></section>
  </section>;
}
