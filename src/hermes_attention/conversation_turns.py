"""Transactional owner-visible turns over Hermes' canonical SessionDB.

Model stages use isolated sessions. Only this adapter appends owner-visible
messages; cancelled output is a labelled draft, never a successful answer.
"""
from __future__ import annotations
from contextlib import contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable

CONTEXTS = {'personal', 'inside-success', 'mitchell', 'mixed', 'unknown'}


def validate_id(value: Any, *, session: bool = False) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', value):
        raise ValueError('invalid conversation identity')
    if session and not value.startswith('jarvis_'):
        raise PermissionError('conversation is not Jarvis-owned')
    return value


@contextmanager
def session_lock(root: Path, session_id: str):
    directory = root / 'runtime-data' / 'conversation-locks'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (hashlib.sha256(session_id.encode()).hexdigest() + '.lock')
    with path.open('a') as lock:
        path.chmod(0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def transition(factory: Callable[[], Any], root: Path, request: dict[str, Any], *, finish: bool) -> dict[str, Any]:
    session_id = validate_id(request.get('sessionId'), session=True)
    turn_id = validate_id(request.get('turnId'))
    context = request.get('context')
    if context not in CONTEXTS:
        raise ValueError('invalid conversation context')
    # The original context in a legacy ID is provenance, not an immutable
    # retrieval filter for every subsequent owner turn.
    status = request.get('status', 'completed') if finish else 'submitted'
    if status not in {'submitted', 'completed', 'cancelled', 'failed', 'interrupted'}:
        raise ValueError('invalid turn state')
    role = 'assistant' if finish else 'user'
    content = request.get('assistantMessage' if finish else 'ownerRequest', '')
    if not isinstance(content, str) or len(content) > 100_000:
        raise ValueError('turn content exceeds supported size')
    if not content.strip():
        if status in {'cancelled', 'failed', 'interrupted'}:
            content = {'cancelled': 'Cancelled before a final answer.', 'failed': 'This turn failed before a final answer.', 'interrupted': 'This turn was interrupted before a final answer.'}[status]
        else:
            raise ValueError('turn content is empty')
    progress = request.get('progress', [])
    if not isinstance(progress, list) or len(progress) > 40 or any(not isinstance(x, str) or len(x) > 400 for x in progress):
        raise ValueError('invalid turn progress')
    receipt=request.get('actionReceipt')
    if receipt is not None:
        if not isinstance(receipt,dict) or len(json.dumps(receipt))>200000:raise ValueError('invalid action receipt')
        # Keep identifiers and explicit result state; draft MIME/attachment bytes
        # remain in their private provider adapter, never duplicated in history.
        result=receipt.get('result') or {}
        receipt={'status':receipt.get('status'),'preparationId':receipt.get('preparationId'),'undoAvailable':receipt.get('undoAvailable',False),'result':{k:result[k] for k in ('provider_id','resource_kind','change_id','status','undo_available','sent','external_write') if k in result}}
    attachments=request.get('attachmentIds',[])
    if not isinstance(attachments,list) or len(attachments)>20 or any(not isinstance(x,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}',x) for x in attachments):
        raise ValueError('invalid turn attachment references')
    with session_lock(root, session_id):
        db = factory()
        try:
            session = db.get_session(session_id)
            if not session or session.get('source') != 'desktop':
                raise PermissionError('canonical session is absent or owned by another client')
            rows = db.get_messages(session_id)
            matches = [row for row in rows if (row.get('display_metadata') or {}).get('jarvis_turn_id') == turn_id]
            existing = next((row for row in matches if row.get('role') == role), None)
            if existing:
                if role == 'user' and existing.get('content') != content:
                    raise ValueError('turn identity was reused for different input')
                canonical_status=(existing.get('display_metadata') or {}).get('status', status)
                canonical_content=existing.get('content','')
                return {'ok': True, 'persisted': True, 'idempotent': True, 'turnId': turn_id,
                        'status':canonical_status,'assistantMessage':canonical_content if finish else None,
                        'terminalConflict':bool(finish and (canonical_status!=status or canonical_content!=content))}
            if finish and not any(row.get('role') == 'user' for row in matches):
                raise ValueError('cannot finish an unsubmitted turn')
            metadata = {'jarvis_turn_id': turn_id, 'context': context, 'status': status, 'stage': status,
                        'route': str(request.get('route', ''))[:40], 'progress': progress,
                        'review_harness_isolated': True, 'run_id': str(request.get('runId', ''))[:96],
                        'partial': status in {'cancelled', 'failed', 'interrupted'},
                        'attachment_ids': attachments,'action_receipt':receipt}
            db.append_messages_batch(session_id, [{'role': role, 'content': content,
                'finish_reason': ('governed_final' if status == 'completed' else status) if finish else None,
                'display_kind': ('jarvis_answer' if status == 'completed' else 'jarvis_partial') if finish else 'jarvis_user',
                'display_metadata': metadata}])
            return {'ok': True, 'persisted': True, 'idempotent': False, 'turnId': turn_id, 'status': status, 'assistantMessage':content if finish else None, 'terminalConflict':False}
        finally:
            db.close()
