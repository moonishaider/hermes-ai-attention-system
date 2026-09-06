#!/usr/bin/env python3
"""Private native-launched bounded browser worker; never an agent tool."""
import asyncio,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'));sys.path.append(str(Path.home()/'.hermes/hermes-agent'))
from hermes_attention.scoped_browser import serve,scope_path,stop_scopes
if __name__=='__main__':
    if sys.argv[1:]==['--stop-all']:
        print(json.dumps({'scopes':stop_scopes(ROOT,wait=True)}));raise SystemExit(0)
    identity=sys.argv[1]
    try:asyncio.run(serve(ROOT,identity))
    except Exception as error:
        p=scope_path(ROOT,identity).parent/'failure.json';p.write_text(json.dumps({'error':str(error)[:400]}));p.chmod(0o600);raise
