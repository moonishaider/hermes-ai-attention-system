#!/usr/bin/env python3
"""Authenticated-native DLOA evidence bridge; bounded tool-free synthesis, no publishing."""
from __future__ import annotations
import asyncio
import json
import sqlite3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hermes_attention.config import ProjectPaths
from hermes_attention.dloa_runtime import DloaCoordinator
from hermes_attention.documents import _identifier
import jarvis_local_state as local


def cancellation_requested(session_id,turn_id,database,db_factory):
    """Read only trusted exact native turn markers; model/source text has no effect."""
    path=Path(database)
    if path.exists():
        if path.is_symlink():raise PermissionError('Cancellation database must not be a symlink')
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as conn:
            exists=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='native_cancelled_turns'").fetchone()
            if exists and conn.execute('SELECT 1 FROM native_cancelled_turns WHERE session_id=? AND turn_id=?',(session_id,turn_id)).fetchone():return True
    db=db_factory()
    try:
        local._jarvis_session(db,session_id)
        return any((r.get('display_metadata') or {}).get('jarvis_turn_id')==turn_id and (r.get('display_metadata') or {}).get('status')=='cancelled' for r in db.get_messages(session_id))
    finally:db.close()


def handle(value, *, coordinator=None,db_factory=None):
    if not isinstance(value,dict):raise ValueError('Native DLOA request must be an object')
    if set(value)-{'operation','sessionId','turnId','ownerRequest','reportDate','through','startOverride','refresh','manifestId','usage','timings','maxBatches','failedTurnId','batchId','modelAttemptId','attemptDigest','finalAttemptDigest','usageEventId'}:raise ValueError('Unsupported native DLOA fields')
    operation=value.get('operation','prepare')
    session_id=value.get('sessionId');db=(db_factory or local._canonical_session_db)()
    try:
        local._jarvis_session(db,session_id)
        if operation in {'acknowledge-extraction-failure','recovery-prepare','final-recovery-prepare'}:
            new_turn=_identifier(value.get('turnId'));failed_turn=_identifier(value.get('failedTurnId'))
            if new_turn==failed_turn:raise PermissionError('Recovery cannot replay the old turn')
            rows=[r for r in db.get_messages(session_id) if r.get('role')=='user' and (r.get('display_metadata') or {}).get('jarvis_turn_id')==new_turn]
            if len(rows)!=1:raise PermissionError('New canonical owner user turn is required for recovery')
            canonical_recovery_text=rows[0].get('content','')
            if not isinstance(canonical_recovery_text,str) or not canonical_recovery_text.strip():raise PermissionError('Canonical recovery request text is required')
        if operation=='finish':
            turn_id=_identifier(value.get('turnId'))
            rows=[r for r in db.get_messages(session_id) if (r.get('display_metadata') or {}).get('jarvis_turn_id')==turn_id and r.get('role')=='assistant']
            if len(rows)!=1:raise PermissionError('Exact canonical assistant turn is unavailable')
            row=rows[0];metadata=row.get('display_metadata') or {}
            canonical={'text':row.get('content',''),'status':metadata.get('status'),'run_id':metadata.get('run_id','')}
    finally:db.close()
    coordinator=coordinator or DloaCoordinator(ProjectPaths.discover(ROOT))
    if operation=='final-recovery-diagnose':
        from hermes_attention.dloa_final_recovery import diagnose_final
        return diagnose_final(coordinator.workspace,coordinator.paths.database,session_id,_identifier(value.get('turnId')))
    if operation=='final-recovery-prepare':
        from hermes_attention.dloa_final_recovery import prepare_final
        return prepare_final(coordinator.workspace,coordinator.paths.database,session_id,value['failedTurnId'],value['turnId'],value.get('finalAttemptDigest'),value.get('modelAttemptId'),value.get('usageEventId'),canonical_recovery_text)
    if operation=='recovery-prepare':
        from hermes_attention.documents import _locked
        from hermes_attention.dloa_synthesis import diagnose_extraction
        diagnosis=diagnose_extraction(coordinator.workspace,coordinator.paths.database,session_id,value['failedTurnId'])
        key=session_id+':'+value['turnId'];oldkey=session_id+':'+value['failedTurnId']
        with _locked(coordinator.workspace.root):
            state=coordinator.workspace._read();old=state.get('native_turns',{}).get(oldkey)
            if not old:raise PermissionError('Failed canonical turn has no retained manifest')
            if any(r['sessionId']==session_id and r['failedTurnId']==value['failedTurnId'] and r['newTurnId']!=value['turnId'] for r in state.get('extraction_recoveries',{}).values()):raise PermissionError('Resume the existing acknowledged recovery turn')
            if any(edge.get('parent')==oldkey and child!=key for child,edge in state.get('extraction_local_edges',{}).items()):raise PermissionError('Resume existing local recovery turn')
            local_batches={b['batchId']:b['attemptDigest'] for b in diagnosis['batches'] if b.get('localRevalidation')}
            if local_batches:
                if not diagnosis['eligible']:raise PermissionError('Unknown recovery lineage outcome')
                state.setdefault('extraction_local_edges',{})[key]={'parent':oldkey,'batches':local_batches}
            binding={'manifest_id':old['manifest_id'],'owner_request':old['owner_request']+'\nCurrent owner recovery request: '+canonical_recovery_text,'recovery_of':oldkey}
            existing=state.get('native_turns',{}).get(key)
            if existing and existing!=binding:raise PermissionError('New turn already has a conflicting evidence binding')
            state['native_turns'][key]=binding;coordinator.workspace._save(state)
        packet=coordinator.workspace.synthesis_input(old['manifest_id'],session_id)
        return {'status':'prepared','manifestId':old['manifest_id'],'sourceStatus':packet['source_status'],'cacheHit':True,'providerWrite':False,'modelCalled':False}
    if operation in {'revalidation-diagnose','revalidate-extraction'}:
        from hermes_attention.dloa_synthesis import revalidate_extraction
        return revalidate_extraction(coordinator.workspace,session_id,_identifier(value.get('turnId')),value.get('batchId'),value.get('attemptDigest'),diagnose=operation=='revalidation-diagnose',database=coordinator.paths.database)
    if operation=='recovery-diagnose':
        from hermes_attention.dloa_synthesis import diagnose_extraction
        return diagnose_extraction(coordinator.workspace,coordinator.paths.database,session_id,_identifier(value.get('turnId')))
    if operation=='acknowledge-extraction-failure':
        from hermes_attention.dloa_synthesis import acknowledge_extraction
        return acknowledge_extraction(coordinator.workspace,coordinator.paths.database,session_id,value['failedTurnId'],value['turnId'],value.get('batchId'),value.get('modelAttemptId'))
    if operation=='latest':
        manifest=coordinator.latest(session_id)
        return {'available':manifest is not None,'manifestId':manifest['id'] if manifest else None,'window':manifest['window'] if manifest else None}
    if operation=='prepare':
        return asyncio.run(coordinator.prepare(conversation_id=session_id,turn_id=value.get('turnId'),owner_request=value.get('ownerRequest',''),report_date=value.get('reportDate'),through=value.get('through'),start_override=value.get('startOverride'),refresh=value.get('refresh') is True))
    if operation=='continue-sources':
        return asyncio.run(coordinator.continue_sources(conversation_id=session_id,turn_id=value.get('turnId'),manifest_id=value.get('manifestId'),owner_request=value.get('ownerRequest',''),max_batches=value.get('maxBatches',2)))
    if operation=='synthesize':
        return coordinator.synthesize(conversation_id=session_id,turn_id=value.get('turnId'),manifest_id=value.get('manifestId'),cancelled=lambda:cancellation_requested(session_id,value.get('turnId'),coordinator.paths.database,db_factory or local._canonical_session_db))
    if operation=='finish':
        return coordinator.finish(conversation_id=session_id,turn_id=value['turnId'],manifest_id=value.get('manifestId'),canonical_text=canonical['text'],status=canonical['status'],run_id=canonical['run_id'],usage=value.get('usage'),timings=value.get('timings'))
    raise ValueError('Unsupported DLOA operation')


def main():
    try:
        raw=sys.stdin.buffer.read(100000)
        if len(raw)>=100000:raise ValueError('Native DLOA request too large')
        result=handle(json.loads(raw));print(json.dumps({'ok':True,**result},ensure_ascii=False,default=str));return 0
    except Exception as error:
        print(json.dumps({'ok':False,'error':type(error).__name__,'message':str(error)[:300]}));return 2
if __name__=='__main__':raise SystemExit(main())
