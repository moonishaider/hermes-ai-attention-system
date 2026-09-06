#!/usr/bin/env python3
"""Fixed private desktop bridge. Never register this as an agent tool."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
# Hermes native memory/skill APIs live in the existing reviewed installation.
HERMES=Path.home()/'.hermes/hermes-agent'
sys.path.append(str(HERMES))
from hermes_attention.service import AttentionService
from hermes_attention.workspace import Workspace,encode

def main():
    service=None
    try:
        raw=sys.stdin.buffer.read(1048577)
        if len(raw)>1048576:raise ValueError('Workspace request too large')
        value=json.loads(raw)
        service=AttentionService()
        workspace=Workspace(service.store,Path.home()/'.hermes/skills',owner=True,contexts={x['id'] for x in service.context_config['contexts']})
        operation=value['operation'];request=value.get('request',{})
        if operation in {'awareness.refresh','awareness.meeting.analyze','awareness.meeting.commit'}:
            from hermes_attention.awareness_runtime import AwarenessRuntime
            if operation=='awareness.refresh':request={**request,'lifecycle':workspace.lifecycle()}
            runtime_operation=operation if operation=='awareness.refresh' else operation.removeprefix('awareness.')
            result=AwarenessRuntime(service).dispatch(runtime_operation,request)
        else:result=workspace.dispatch(operation,request)
        print(json.dumps({'ok':True,'result':result},default=encode,ensure_ascii=False));return 0
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error)[:400]}));return 2
    finally:
        if service:service.close()
if __name__=='__main__':raise SystemExit(main())
