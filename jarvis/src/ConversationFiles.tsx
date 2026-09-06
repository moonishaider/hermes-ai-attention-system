import { useEffect, useRef, useState } from 'react';
import { invoke } from './transport';

export interface Attachment {
  attachment_id: string;
  display_name: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  retention: string;
  retention_state?: string;
  warning?: string;
  preview?: string;
  sha256?: string;
}
export interface Artifact {
  artifact_id: string;
  display_name: string;
  mime_type: string;
  version: number;
  status?: string;
  parent_id?: string | null;
  artifact_root_id?: string;
  is_latest?: boolean;
  review_status?: string;
}
interface Props {
  sessionId: string | null;
  ensureSession: () => Promise<string>;
  refreshKey?: string;
  compact?: boolean;
  onAnalyzeTranscript?: (attachmentId: string, sessionId: string) => void;
  onBusyChange?: (owner: string | null, busy: boolean) => void;
}
const MAX_FILE_BYTES = 20 * 1024 * 1024;
const EXTENSIONS = /\.(txt|md|pdf|png|jpe?g|webp|csv|xlsx|docx)$/i;
export function validateSelectedFile(file: Pick<File, 'name' | 'size' | 'type'>) {
  if (!EXTENSIONS.test(file.name)) return 'Supported formats: text, Markdown, PDF, PNG, JPEG, WebP, CSV, XLSX and DOCX.';
  if (!file.size) return 'This file is empty.';
  if (file.size > MAX_FILE_BYTES) return 'This file exceeds the 20 MiB per-file limit.';
  return null;
}
export function ConversationFiles({ sessionId, ensureSession, refreshKey, compact = false, onBusyChange, onAnalyzeTranscript }: Props) {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [notice, setNotice] = useState('');
  const [processing, setProcessing] = useState(false);
  const [preview, setPreview] = useState<Attachment | null>(null);
  const [dragging, setDragging] = useState(false);
  const ownerRef = useRef(sessionId);
  const operationRef = useRef(false);
  ownerRef.current = sessionId;
  async function refresh(owner: string) {
    const value = await invoke<{ data?: Attachment[]; artifacts?: Artifact[] }>('list_attachments', { sessionId: owner });
    if (ownerRef.current !== owner) return;
    setAttachments(value.data ?? []); setArtifacts(value.artifacts ?? []);
  }
  useEffect(() => {
    setAttachments([]); setArtifacts([]); setPreview(null); setNotice('');
    if (sessionId) void refresh(sessionId).catch(error => {
      if (ownerRef.current === sessionId) setNotice(`Files unavailable: ${String(error)}`);
    });
  }, [sessionId, refreshKey]);

  async function ingest(files?: File[]) {
    if (operationRef.current) return;
    operationRef.current = true; setProcessing(true);
    const initialOwner = ownerRef.current; onBusyChange?.(initialOwner, true);
    let owner: string | undefined;
    try {
      owner = await ensureSession();
      if (owner !== initialOwner) { onBusyChange?.(owner, true); onBusyChange?.(initialOwner, false); }
      const failures: string[] = [];
      if (!files) {
        const result = await invoke<{ errors?: Array<{ name: string; error: string }> }>('attach_files', { sessionId: owner, retention: 'conversation' });
        failures.push(...(result.errors ?? []).map(item => `${item.name}: ${item.error}`));
      } else {
        if (files.length > 20) throw new Error('Attach up to twenty files at a time.');
        for (const file of files) {
          const error = validateSelectedFile(file);
          if (error) { failures.push(`${file.name}: ${error}`); continue; }
          try {
            const bytes = Array.from(new Uint8Array(await file.arrayBuffer()));
            await invoke('attach_bytes', { sessionId: owner, name: file.name, mimeType: file.type, bytes, retention: 'conversation' });
          } catch (error) { failures.push(`${file.name}: ${String(error)}`); }
        }
      }
      await refresh(owner);
      if (ownerRef.current === owner) setNotice(failures.join('\n'));
    } catch (error) {
      if (!owner || ownerRef.current === owner) setNotice(`Attachment not added: ${String(error)}`);
    } finally { operationRef.current = false; setProcessing(false); onBusyChange?.(owner ?? initialOwner, false); }
  }

  useEffect(() => {
    const paste = (event: ClipboardEvent) => {
      const files = Array.from(event.clipboardData?.files ?? []);
      if (!files.length) return;
      event.preventDefault(); void ingest(files);
    };
    const drop = (event: DragEvent) => {
      const files = Array.from(event.dataTransfer?.files ?? []);
      setDragging(false);
      if (!files.length) return;
      event.preventDefault(); void ingest(files);
    };
    const drag = (event: DragEvent) => {
      if (event.dataTransfer?.types.includes('Files')) { event.preventDefault(); setDragging(true); }
    };
    const leave = (event: DragEvent) => { if (!event.relatedTarget) setDragging(false); };
    window.addEventListener('paste', paste); window.addEventListener('drop', drop);
    window.addEventListener('dragover', drag); window.addEventListener('dragleave', leave);
    return () => {
      window.removeEventListener('paste', paste); window.removeEventListener('drop', drop);
      window.removeEventListener('dragover', drag); window.removeEventListener('dragleave', leave);
    };
  }, [sessionId, ensureSession]);

  async function control(attachment: Attachment, action: 'forget' | 'restore' | 'retry') {
    if (operationRef.current) return;
    const owner = sessionId;operationRef.current=true;setProcessing(true);onBusyChange?.(owner,true);
    try {
      await invoke('attachment_control', { id: attachment.attachment_id, action, sessionId: owner });
      if (owner) await refresh(owner);
      if (ownerRef.current === owner) { setPreview(null); setNotice(action === 'forget' ? 'Removed from retrieval. The original file is unchanged; you can restore this attachment.' : action === 'restore' ? 'Attachment restored for this conversation.' : 'Extraction retried. Check its status before relying on it.'); }
    } catch (error) { if (ownerRef.current === owner) setNotice(`File operation failed: ${String(error)}`); }
    finally {operationRef.current=false;setProcessing(false);onBusyChange?.(owner,false);}
  }
  async function artifactAction(artifact: Artifact, action: 'open' | 'reveal' | 'save-as') {
    try { await invoke('artifact_control', { id: artifact.artifact_id, action, sessionId }); }
    catch (error) { setNotice(`Could not ${action.replace('-', ' ')} file: ${String(error)}`); }
  }

  return <section className={`conversation-files ${compact ? 'compact' : ''}`} aria-label="Conversation files">
    {dragging && <div className="file-drop-overlay">Drop files into this conversation</div>}
    <div className="file-toolbar"><button type="button" className="quiet" disabled={processing} onClick={() => void ingest()}>{processing ? 'Processing files…' : '＋ Attach'}</button><details className="file-policy"><summary>File privacy</summary><p>Selected files stay privately with this conversation. Your requests authorize necessary analysis through configured providers. Originals are unchanged. Forget removes a file from retrieval and can be undone. Screen captures remain temporary.</p></details></div>
    {attachments.length > 0 && <div className="attachment-list">{attachments.map(file => <div className={`attachment-chip ${file.status}`} key={file.attachment_id}><button type="button" className="quiet" onClick={() => setPreview(file)}><strong>{file.display_name}</strong><small>{file.retention_state === 'forgotten' ? 'forgotten' : file.status} · {(file.size_bytes / 1024).toFixed(0)} KB</small></button>{file.retention_state === 'forgotten' || file.retention_state === 'archived' || file.status === 'forgotten' || file.status === 'archived' ? <button type="button" className="quiet" onClick={() => void control(file, 'restore')}>Restore</button> : <button type="button" className="quiet" aria-label={`Forget ${file.display_name}`} onClick={() => void control(file, 'forget')}>×</button>}</div>)}</div>}
    {artifacts.length > 0 && <div className="artifact-list" aria-label="Generated files">{[...artifacts].sort((a,b) => Number(a.is_latest === false)-Number(b.is_latest === false) || b.version-a.version).map(file => <article className="artifact-card" key={file.artifact_id}><span><strong>{file.display_name}</strong><small>{file.is_latest === false ? 'Earlier version' : 'Latest version'} {file.version} · {file.review_status === 'reviewer_output' ? 'Reviewer output' : file.status ?? 'generated'}</small>{file.parent_id && <small>Revises version {artifacts.find(parent => parent.artifact_id === file.parent_id)?.version ?? 'retained'}</small>}</span><div className="focus-controls"><button type="button" onClick={() => void artifactAction(file, 'open')}>Open</button><button type="button" className="quiet" onClick={() => void artifactAction(file, 'reveal')}>Reveal</button><button type="button" className="quiet" onClick={() => void artifactAction(file, 'save-as')}>Save As</button></div></article>)}</div>}
    {notice && <p className="file-notice" role="status">{notice}</p>}
    {preview && <div className="file-preview" role="dialog" aria-label={`Preview ${preview.display_name}`}><header><strong>{preview.display_name}</strong><button type="button" className="quiet" onClick={() => setPreview(null)}>Close preview</button></header><p>{preview.status} · {preview.mime_type} · retained with conversation</p>{preview.warning && <p role="alert">{preview.warning}</p>}<pre>{preview.preview || 'No text preview is available. The extraction status above determines whether this file can be used.'}</pre><small>A preview may be shorter than the complete document. Answers should cite original pages, rows or cells.</small>{preview.retention_state !== 'forgotten' && !compact && onAnalyzeTranscript && sessionId && ['ready','partial','complete','complete_with_warnings'].includes(preview.status) && <button type="button" onClick={() => onAnalyzeTranscript(preview.attachment_id, sessionId)}>Analyze as meeting transcript</button>}{preview.status === 'failed' && <button type="button" onClick={() => void control(preview, 'retry')}>Retry extraction</button>}</div>}
  </section>;
}
