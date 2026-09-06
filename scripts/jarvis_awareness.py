#!/usr/bin/env python3
"""Trusted native-only awareness bridge; source reads and local owner review."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from hermes_attention.service import AttentionService
from hermes_attention.config import ProjectPaths
from hermes_attention.awareness_runtime import AwarenessRuntime

def main():
    service=None
    try:
        raw=sys.stdin.buffer.read(100001)
        if len(raw)>100000:raise ValueError('Request too large')
        value=json.loads(raw)
        if set(value)-{'operation','request'}:raise ValueError('Unsupported native fields')
        service=AttentionService(paths=ProjectPaths.discover(ROOT))
        result=AwarenessRuntime(service).dispatch(value['operation'],value.get('request',{}))
        print(json.dumps({'ok':True,'result':result},ensure_ascii=False));return 0
    except Exception as error:print(json.dumps({'ok':False,'error':type(error).__name__,'message':str(error)[:250]}));return 2
    finally:
        if service:service.close()
if __name__=='__main__':raise SystemExit(main())
