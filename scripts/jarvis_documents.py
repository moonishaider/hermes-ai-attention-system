#!/usr/bin/env python3
"""Native-only document IPC. Canonical session ownership is checked per request."""
from pathlib import Path
import base64
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hermes_attention.documents_bridge import dispatch

def handle(value):
    from jarvis_local_state import _canonical_session_db, _jarvis_session
    session_id=value.get('sessionId')
    db=_canonical_session_db()
    try: _jarvis_session(db,session_id)
    finally: db.close()
    operation=value.get('operation')
    if operation in {'issue-turn','revoke-turn','freeze-turn'}:
        from hermes_attention.document_runtime import DocumentRuntime
        runtime=DocumentRuntime(ROOT/'runtime-data/documents')
        stage=value.get('stageSessionId')
        if operation=='revoke-turn':return {'ok':True,**runtime.revoke(stage)}
        turn=value.get('turnId')
        frozen=runtime.freeze(session_id,turn)
        if operation=='freeze-turn':return {'ok':True,'attachmentIds':frozen['attachment_ids']}
        runtime.issue(stage,session_id,turn)
        identities=set(frozen['attachment_ids']+frozen['generated_ids'])
        records=[r for r in runtime.documents.list(session_id) if r['id'] in identities]
        return {'ok':True,'attachments':[{'id':r['id'],'name':r['display_name'],'status':r['extraction_status'],'version':r['version']} for r in records]}
    request={**value,'conversation_id':session_id,'attachment_id':value.get('id','')}
    if operation=='list': request['include_forgotten']=True  # owner metadata view only; model runtime list stays active-only
    if operation=='ingest_file': request['operation']='ingest_path'
    if operation=='ingest_bytes':
        raw=value.get('bytes',[])
        if not isinstance(raw,list) or len(raw)>20*1024*1024: raise ValueError('File exceeds the attachment limit')
        request['base64']=base64.b64encode(bytes(raw)).decode()
        request.pop('bytes',None)
    if operation=='retry': request['operation']='ocr'
    if operation=='artifact_path': request['operation']='resolve_path'
    result=dispatch(ROOT/'runtime-data/documents',request)
    if operation=='artifact_path':
        # The native artifact handler needs the validated path as well as metadata.
        # Do not flatten attachment metadata and accidentally discard the path.
        return {'ok':True,**result}
    if operation=='forget':
        from hermes_attention.service import AttentionService
        service=AttentionService()
        try:
            for row in service.store.connection.execute('SELECT evidence_id,provenance_json FROM evidence WHERE tombstoned_at IS NULL').fetchall():
                provenance=json.loads(row['provenance_json']);metadata=provenance.get('metadata') or {}
                if provenance.get('connection_id')=='owner-selected-attachment' and metadata.get('attachment_id')==value.get('id') and metadata.get('conversation_id')==session_id:
                    service.store.tombstone_evidence(row['evidence_id'],reason='Owner forgot the original conversation attachment')
        finally:service.close()

    if operation=='list':
        records=result['attachments']
        for record in records:
            if record.get('retention_state')!='active':
                record['preview']='';record['citations']=[]
        generated=[r for r in records if r.get('source')=='generated-fixed-operation' and r.get('retention_state')=='active']
        return {'ok':True,'data':records,'artifacts':[{'artifact_id':r['attachment_id'],'display_name':r['display_name'],'mime_type':r['mime_type'],'version':r['version'],'status':r['status']} for r in generated]}
    return {'ok':True,**result.get('attachment',result)}

def main():
    try:
        raw=sys.stdin.buffer.read(90*1024*1024+1)
        if len(raw)>90*1024*1024: raise ValueError('Attachment request too large')
        result=handle(json.loads(raw));print(json.dumps(result,ensure_ascii=False));return 0
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error)[:300]}));return 2
if __name__=='__main__':raise SystemExit(main())
