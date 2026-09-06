#!/usr/bin/env python3
"""Owned native stdio worker. No listener starts before explicit start request."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.append(str(Path.home()/'.hermes/hermes-agent'))
os.environ['HERMES_DISABLE_LAZY_INSTALLS']='1'
from hermes_attention.wake import WakeController

def emit(value):print(json.dumps(value),flush=True)
def main():
    wake=WakeController(emit)
    try:
        for line in sys.stdin:
            value={}
            try:
                value=json.loads(line);op=value.get('operation')
                if op=='start':result=wake.start(authorized=value.get('ownerEnabled') is True)
                elif op in {'status','pause','resume','stop'}:result=getattr(wake,op)()
                else:raise ValueError('Unknown wake operation')
                emit({'id':value.get('id'),'ok':True,'result':result})
            except Exception as error:emit({'id':value.get('id'),'ok':False,'error':str(error)[:300]})
    finally:wake.stop()
if __name__=='__main__':main()
