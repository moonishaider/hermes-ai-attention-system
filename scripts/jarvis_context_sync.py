#!/usr/bin/env python3
"""Native-only local export folder bridge; never a model tool."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from hermes_attention.service import AttentionService
from hermes_attention.context_sync import ContextSync

def main():
 service=None
 try:
  value=json.loads(sys.stdin.buffer.read(65537));service=AttentionService();sync=ContextSync(service);op=value['operation']
  if op=='register':result=sync.register(value['path'],value['source'],value['startDate'],owner_authorized=value.get('ownerAuthorized') is True)
  elif op=='status':result=sync.status()
  elif op=='enable':result=sync.enable(value['folderId'],value['enabled'])
  elif op=='remove':result=sync.remove(value['folderId'])
  elif op=='scan':result=sync.scan(value.get('folderId'),force=value.get('force') is True)
  else:raise ValueError('Unknown context sync operation')
  print(json.dumps({'ok':True,'result':result}));return 0
 except Exception as error:print(json.dumps({'ok':False,'error':str(error)[:300]}));return 2
 finally:
  if service:service.close()
if __name__=='__main__':raise SystemExit(main())
