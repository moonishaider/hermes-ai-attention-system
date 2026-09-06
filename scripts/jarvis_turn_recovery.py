#!/usr/bin/env python3
"""Read-only native personal-turn outcome reconciliation; never replay actions."""
from pathlib import Path
import hashlib,json,sqlite3,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from hermes_attention.config import ProjectPaths
from hermes_attention.conversation_turns import validate_id

def validate_session(sid):
    import jarvis_local_state as local
    source=Path.home()/'.hermes/hermes-agent'
    sys.path.insert(0,str(source))
    from hermes_state import SessionDB
    db=SessionDB(db_path=Path.home()/'.hermes/state.db',read_only=True)
    try:local._jarvis_session(db,sid)
    finally:db.close()

def reconcile(request,*,database=None,session_validator=validate_session):
    if not isinstance(request,dict) or set(request)-{'sessionId','turnId','nativeNonce'}:raise ValueError('unsupported native recovery request')
    sid=validate_id(request.get('sessionId'),session=True);tid=validate_id(request.get('turnId'))
    session_validator(sid)
    path=Path(database) if database else ProjectPaths.discover(ROOT).database
    if not path.exists():return {'status':'none','action_repeated':False}
    if path.is_symlink():raise PermissionError('recovery database must not be a symbolic link')
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as conn:
        conn.row_factory=sqlite3.Row
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        row=conn.execute('SELECT * FROM native_personal_turns WHERE session_id=? AND turn_id=?',(sid,tid)).fetchone() if 'native_personal_turns' in tables else None
        cancelled=bool(conn.execute('SELECT 1 FROM native_cancelled_turns WHERE session_id=? AND turn_id=?',(sid,tid)).fetchone()) if 'native_cancelled_turns' in tables else False
    if row and request.get('nativeNonce') and hashlib.sha256(request['nativeNonce'].encode()).hexdigest()!=row['nonce_hash']:raise PermissionError('native recovery nonce differs')
    if not row:return {'status':'cancelled' if cancelled else 'none','action_repeated':False}
    state=row['state'];result=json.loads(row['result_json']) if row['result_json'] else None
    # A committed provider receipt outranks a later cancellation request. An
    # execution claim is uncertain even when cancellation was requested later.
    if state=='completed':status='completed'
    elif state in {'executing','uncertain'}:status='unresolved'
    elif cancelled:status='cancelled'
    elif state=='prepared':status='waiting_action'
    elif state in {'interpreting'}:status='interrupted'
    elif state in {'none','clarify','failed','rejected','cancelled'}:status=state
    else:status='unresolved'
    return {'status':status,'nativeState':state,'result':result,'preparationId':row['preparation_id'],
            'cancelRequested':cancelled,'action_repeated':False,
            'message':'Provider outcome is unknown; no action was repeated.' if status=='unresolved' else None}

def main():
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError('recovery request exceeds size limit')
        print(json.dumps({'ok':True,**reconcile(json.loads(raw))},ensure_ascii=False));return 0
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error)[:240]}));return 2
if __name__=='__main__':raise SystemExit(main())
