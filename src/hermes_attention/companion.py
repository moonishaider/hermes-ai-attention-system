"""Default-disabled private companion authentication boundary; no listener/tunnel.

A trusted HTTPS private ingress supplies the scheme/host; renderer input cannot
choose handlers or obtain native IPC authority. Callback map is fixed by host.
"""
from dataclasses import dataclass
from hashlib import sha256
from http.cookies import SimpleCookie
import hmac,json,secrets,time
from urllib.parse import urlsplit

READ_COMMANDS=frozenset({'health','system_status','jarvis_state','list_conversations','conversation_messages','list_active_runs'})
@dataclass
class Response:
 status:int
 body:dict
 headers:dict

class CompanionBoundary:
 def __init__(self,*,origin='',handlers=None,enabled=False,clock=None):
  parsed=urlsplit(origin)
  if enabled and (parsed.scheme!='https' or not parsed.netloc or parsed.path not in ('','/') or parsed.username or parsed.password or parsed.query or parsed.fragment):raise ValueError('An exact private HTTPS origin is required')
  self.origin=origin.rstrip('/');self.host=parsed.netloc;self.enabled=enabled;self.clock=clock or time.time;self.handlers={k:v for k,v in (handlers or {}).items() if k in READ_COMMANDS};self.sessions={};self.pairing=None;self.attempts=[]
 def status(self):return {'state':'ready-for-private-transport' if self.enabled else 'transport-blocked','remote_actions':False,'active_sessions':len(self.sessions),'public_exposure':False}
 def pairing_code(self,*,owner_authorized=False):
  if not self.enabled or not owner_authorized:raise PermissionError('Choose and authorize a private HTTPS transport locally first')
  code=secrets.token_urlsafe(24);self.pairing=(sha256(code.encode()).digest(),self.clock()+600);return code
 def _response(self,status,body,**headers):return Response(status,body,{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',**headers})
 def request(self,*,method,path,host,origin,cookie='',csrf='',body=b'',secure_transport=False):
  if not self.enabled:return self._response(503,{'error':'transport-blocked'})
  if not secure_transport or host!=self.host or origin!=self.origin:return self._response(403,{'error':'Remote origin is not authorized'})
  if method!='POST' or len(body)>65536:return self._response(400,{'error':'Unsupported request'})
  try:value=json.loads(body or b'{}')
  except (ValueError,UnicodeDecodeError):return self._response(400,{'error':'Invalid JSON'})
  if not isinstance(value,dict):return self._response(400,{'error':'Expected object'})
  now=self.clock();self.sessions={k:v for k,v in self.sessions.items() if v['expires']>now}
  if path=='/api/login':
   self.attempts=[t for t in self.attempts if t>now-60]
   if len(self.attempts)>=5:return self._response(429,{'error':'Wait before another pairing attempt'})
   self.attempts.append(now);code=value.get('code','')
   if not isinstance(code,str) or len(code)>200 or not self.pairing or self.pairing[1]<=now or not hmac.compare_digest(sha256(code.encode()).digest(),self.pairing[0]):return self._response(401,{'error':'Pairing code unavailable or expired'})
   self.pairing=None
   if len(self.sessions)>=5:self.sessions.pop(next(iter(self.sessions)))
   sid=secrets.token_urlsafe(32);token=secrets.token_urlsafe(32);self.sessions[sha256(sid.encode()).hexdigest()]={'csrf':token,'expires':now+43200}
   return self._response(200,{'csrf':token,'mode':'private-read-companion'},**{'Set-Cookie':f'__Host-Jarvis={sid}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=43200'})
  try:parsed=SimpleCookie();parsed.load(cookie);sid=parsed['__Host-Jarvis'].value
  except Exception:return self._response(401,{'error':'Pair this device locally first'})
  key=sha256(sid.encode()).hexdigest();session=self.sessions.get(key)
  if not session:return self._response(401,{'error':'Remote session expired'})
  if path=='/api/session':return self._response(200,{'csrf':session['csrf'],'mode':'private-read-companion'})
  if not isinstance(csrf,str) or not hmac.compare_digest(csrf,session['csrf']):return self._response(403,{'error':'CSRF token required'})
  if path=='/api/logout':
   self.sessions.pop(key,None);return self._response(200,{'status':'signed-out'},**{'Set-Cookie':'__Host-Jarvis=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0'})
  command=value.get('command');args=value.get('args',{})
  if path!='/api/invoke' or command not in READ_COMMANDS or command not in self.handlers:return self._response(403,{'error':'This operation requires the local Jarvis interface'})
  if not isinstance(args,dict):return self._response(400,{'error':'Invalid arguments'})
  try:result=self.handlers[command](args)
  except Exception:return self._response(502,{'error':'The requested local read could not complete'})
  return self._response(200,{'result':result})
