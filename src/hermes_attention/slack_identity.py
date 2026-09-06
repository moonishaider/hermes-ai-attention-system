"""Exact authenticated Slack thread-envelope identity; never infers fact subjects."""
import hashlib
import json
import re

_CHANNEL=re.compile(r'[CGD][A-Z0-9]{8,}')
_TS=re.compile(r'\d{10,}\.\d{6}')
_AUTHOR=re.compile(r'[^\r\n]+ \(([UW][A-Z0-9]{8,})\)')


def thread_author_receipt(payload, *, channel_id, message_ts, connection_id):
    """Call only with a response from the configured exact-resource read client.

    Resource arguments are trusted client inputs, never inferred from message text.
    Only the fixed leading parent envelope is parsed. Body headers are untrusted.
    """
    if connection_id!='slack_inside_success_readonly' or not isinstance(channel_id,str) or not _CHANNEL.fullmatch(channel_id) or not isinstance(message_ts,str) or not _TS.fullmatch(message_ts):
        raise ValueError('Exact reviewed Slack resource required')
    if not isinstance(payload,dict) or not isinstance(payload.get('messages'),str):raise ValueError('Slack thread envelope unavailable')
    text=payload['messages'];lines=text.splitlines()
    if len(lines)<4 or lines[0]!='=== THREAD PARENT MESSAGE ===' or not lines[1].startswith('From: ') or not lines[2].startswith('Time: ') or not lines[2][6:].strip() or lines[3]!='Message TS: '+message_ts:
        raise ValueError('Exact leading Slack parent envelope differs')
    author=_AUTHOR.fullmatch(lines[1][6:])
    if not author:raise ValueError('Slack author is not one exact server-envelope ID')
    return {'schema':1,'connection_id':connection_id,'channel_id':channel_id,'message_ts':message_ts,'author_id':author.group(1),'identity_basis':'authenticated exact thread leading parent envelope','response_sha256':hashlib.sha256(text.encode()).hexdigest(),'envelope_sha256':hashlib.sha256('\n'.join(lines[:4]).encode()).hexdigest(),'fact_subject_verified':False}


def exact_parent_body(payload):
    """Return only an unambiguous single-parent read body, never search text.

    Callers request limit=1. Additional server-style record boundaries fail closed
    because message text and additional rendered replies cannot be distinguished.
    """
    if not isinstance(payload,dict) or not isinstance(payload.get('messages'),str):raise ValueError('Slack thread envelope unavailable')
    lines=payload['messages'].splitlines()
    if len(lines)<4 or lines[0]!='=== THREAD PARENT MESSAGE ===' or not lines[1].startswith('From: ') or not _AUTHOR.fullmatch(lines[1][6:]) or not lines[2].startswith('Time: ') or not lines[3].startswith('Message TS: ') or not _TS.fullmatch(lines[3][12:]):
        raise ValueError('Exact leading parent envelope required')
    if any(re.fullmatch(r'=== .* ===',line) for line in lines[4:]):raise ValueError('Ambiguous extra rendered record; parent body not isolated')
    return ''.join(payload['messages'].splitlines(keepends=True)[4:])


def verified_author(item, receipt, *, channel_id, message_ts):
    """Attach author provenance only; cached fact attribution is never upgraded."""
    if receipt.get('connection_id')!='slack_inside_success_readonly' or receipt.get('channel_id')!=channel_id or receipt.get('message_ts')!=message_ts or item.get('connection_id')!=receipt['connection_id'] or item.get('provenance',{}).get('message_ts')!=message_ts:
        raise ValueError('Author receipt and retained message differ')
    author=receipt.get('author_id')
    if not isinstance(author,str) or not re.fullmatch(r'[UW][A-Z0-9]{8,}',author) or receipt.get('fact_subject_verified') is not False:
        raise ValueError('Author receipt cannot grant fact attribution')
    from urllib.parse import urlsplit
    raw=item.get('source_ref','');wrapped=re.fullmatch(r'\[[^\]]*\]\((https://[^()\s]+)\)',raw)
    if wrapped:raw=wrapped.group(1)
    path=urlsplit(raw).path.split('/')
    if len(path)!=4 or path[1:3]!=['archives',channel_id] or path[3]!='p'+message_ts.replace('.',''):raise ValueError('Retained message resource differs')
    result=json.loads(json.dumps(item))
    result.setdefault('provenance',{})['verified_author_receipt']=dict(receipt)
    # This field describes authorship only; actor_state and fact attribution remain
    # unchanged until an explicit source-bound fact-subject assessment occurs.
    result['provenance']['verified_author_id']=author
    return result
