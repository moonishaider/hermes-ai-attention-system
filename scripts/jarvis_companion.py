#!/usr/bin/env python3
"""Local-native controlled private companion. Disabled without owner transport config.

This worker has no automatic startup, no public bind, and no provider write route.
Native stdin is the only pairing issuer; pairing codes must not be logged by caller.
"""
from contextlib import closing
import json,os,sqlite3,subprocess,sys,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from hermes_attention.companion import CompanionBoundary
from hermes_attention.conversation_turns import validate_id

class CompanionHost:
 def __init__(self,root=ROOT):self.root=root;self.server=None;self.thread=None;self.boundary=CompanionBoundary();self.lock=threading.RLock();self.origin=None
 def status(self):return {**self.boundary.status(),'listening':self.server is not None,'origin':self.origin,'mode':'private-read-companion','remote_chat':'not-enabled','activation':'Authorize a private HTTPS reverse proxy locally; no tunnel is installed or started by Jarvis.'}
 def _canonical(self):
  path=Path.home()/'.hermes/state.db';db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;return db
 def conversations(self,args):
  query=args.get('query','')
  if not isinstance(query,str) or len(query)>200:raise ValueError('Invalid search')
  with closing(self._canonical()) as db:
   rows=db.execute("SELECT s.id,s.title,s.source,s.started_at,s.message_count FROM sessions s WHERE s.source='desktop' AND substr(s.id,1,7)='jarvis_' AND (instr(lower(coalesce(s.title,'')),lower(?))>0 OR EXISTS(SELECT 1 FROM messages m WHERE m.session_id=s.id AND m.role IN ('user','assistant') AND instr(lower(coalesce(m.content,'')),lower(?))>0)) ORDER BY s.started_at DESC LIMIT 101",(query,query)).fetchall()
  return {'data':[dict(row) for row in rows[:100]],'truncated':len(rows)>100}
 def messages(self,args):
  identity=validate_id(args.get('sessionId'),session=True)
  with closing(self._canonical()) as db:
   owned=db.execute("SELECT id FROM sessions WHERE id=? AND source='desktop'",(identity,)).fetchone()
   if not owned:raise PermissionError('Conversation does not belong to Jarvis')
   rows=db.execute("SELECT id,session_id,role,content,timestamp,display_metadata FROM messages WHERE session_id=? AND role IN ('user','assistant') ORDER BY id DESC LIMIT 500",(identity,)).fetchall()
  data=[]
  for row in reversed(rows):
   item=dict(row)
   if item['display_metadata']:
    try:item['display_metadata']=json.loads(item['display_metadata'])
    except ValueError:item['display_metadata']=None
   data.append(item)
  return {'data':data,'truncated':len(rows)==500}
 def state(self,args):
  context=args.get('context','unknown')
  if context not in {'personal','inside-success','mitchell','unknown','mixed'}:raise ValueError('Invalid context')
  result=subprocess.run([sys.executable,str(self.root/'scripts/jarvis_local_state.py'),'state','--context',context],capture_output=True,text=True,timeout=20,check=True)
  return json.loads(result.stdout)
 def start(self,owner_authorized=False):
  if not owner_authorized:raise PermissionError('Native owner activation required')
  if self.server:return self.status()
  path=self.root/'runtime-data/companion.json'
  if not path.is_file():return self.status()
  if path.is_symlink() or path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077:raise PermissionError('Companion configuration must be owner-only')
  config=json.loads(path.read_text())
  if config.get('enabled') is not True or config.get('transport')!='owner-authorized-private-https' or config.get('ingress_verified') is not True:return self.status()
  origin=config.get('origin','');port=config.get('loopback_port',0)
  if not isinstance(port,int) or not 1024<=port<=65535:raise ValueError('Choose a fixed loopback port above 1023')
  handlers={'health':lambda _:{'state':'ready','backend':'authenticated saved-data companion','message':'Remote reads only; provider health not tested'},'list_conversations':self.conversations,'conversation_messages':self.messages,'jarvis_state':self.state,'list_active_runs':lambda _:{'data':[],'coverage':'Active local run streaming not exposed remotely'}}
  handlers['system_status']=handlers['health']
  boundary=CompanionBoundary(origin=origin,enabled=True,handlers=handlers);host=self
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*_args):pass
   def do_POST(self):
    try:length=int(self.headers.get('Content-Length','0'))
    except ValueError:length=65537
    if not 0<=length<=65536 or self.headers.get_content_type()!='application/json':self.send_error(400);return
    # Only a loopback private HTTPS terminator is trusted; no external socket exists.
    secure=self.client_address[0]=='127.0.0.1' and self.headers.get('X-Forwarded-Proto')=='https'
    with host.lock:response=boundary.request(method='POST',path=self.path,host=self.headers.get('Host',''),origin=self.headers.get('Origin',''),secure_transport=secure,cookie=self.headers.get('Cookie',''),csrf=self.headers.get('X-Jarvis-CSRF',''),body=self.rfile.read(length))
    raw=json.dumps(response.body).encode();self.send_response(response.status)
    for key,value in response.headers.items():self.send_header(key,value)
    self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
   def do_GET(self):
    if self.headers.get('Host')!=urlsplit(origin).netloc:self.send_error(403);return
    dist=(host.root/'companion-web' if (host.root/'companion-web').is_dir() else host.root/'jarvis/dist').resolve();name=unquote(urlsplit(self.path).path).lstrip('/') or 'index.html';path=(dist/name).resolve()
    if not path.is_relative_to(dist) or not path.is_file() or path.suffix not in {'.html','.js','.css','.svg','.png','.woff2','.ico'}:self.send_error(404);return
    import mimetypes
    raw=path.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(path.name)[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");self.end_headers();self.wfile.write(raw)
  server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.daemon_threads=True
  self.boundary=boundary;self.origin=origin;self.server=server;self.thread=threading.Thread(target=server.serve_forever,daemon=True);self.thread.start();return self.status()
 def stop(self):
  if self.server:self.server.shutdown();self.server.server_close();self.server=None
  self.boundary=CompanionBoundary();self.origin=None;return self.status()
 def pair(self,owner_authorized=False):
  with self.lock:code=self.boundary.pairing_code(owner_authorized=owner_authorized)
  return {'origin':self.origin,'pairingCode':code,'expiresInSeconds':600,'delivery':'Show only in local owner UI; never logs or URL parameters'}
def main():
 host=CompanionHost()
 try:
  for line in sys.stdin:
   value={}
   try:
    value=json.loads(line);op=value.get('operation')
    if op=='start':result=host.start(owner_authorized=value.get('ownerAuthorized') is True)
    elif op=='pair':result=host.pair(owner_authorized=value.get('ownerAuthorized') is True)
    elif op in {'stop','status'}:result=getattr(host,op)()
    else:raise ValueError('Unknown companion operation')
    print(json.dumps({'id':value.get('id'),'ok':True,'result':result}),flush=True)
   except Exception as error:print(json.dumps({'id':value.get('id'),'ok':False,'error':str(error)[:300]}),flush=True)
 finally:host.stop()
if __name__=='__main__':main()
