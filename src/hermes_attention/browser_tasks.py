"""Scoped public research/download and maintained native CUA adapters.

Native navigation checks destinations and observed redirects; browser subresource
isolation is not claimed. Backend HTTP reads/downloads pin public IPs. This module never
exposes shell, eval, arbitrary keypress, submit, send or checkout operations.
"""
from pathlib import Path
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
from urllib.parse import urlsplit,urljoin,unquote,parse_qsl
from uuid import uuid4
from .security import SECRET_PATTERNS,detect_prompt_injection
from .google_offline_oauth import _ssl_context

DENIED_QUERY={'token','access_token','refresh_token','api_key','key','password','secret','authorization','cookie'}
CONSEQUENTIAL=re.compile(r'(?i)\b(?:send|submit|pay|purchase|checkout|delete|remove|invite|publish|approve|authorize|transfer|unsubscribe|logout|signout)\b')

def public_url(url,resolver=socket.getaddrinfo):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in {None,443}:raise PermissionError('only ordinary public HTTPS URLs are allowed')
    if parsed.fragment:raise PermissionError('remove URL fragment before navigation')
    if any(k.casefold() in DENIED_QUERY for k,v in parse_qsl(parsed.query)) or any(p.search(unquote(url)) for p in SECRET_PATTERNS):raise PermissionError('URL contains credential-like data')
    host=parsed.hostname.encode('idna').decode('ascii')
    addresses={row[4][0] for row in resolver(host,443,type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):raise PermissionError('private, loopback or non-public address refused')
    if CONSEquential_path(parsed.path):raise PermissionError('URL may perform a consequential action')
    return host,sorted(addresses)

def CONSEquential_path(path):return any(CONSEQUENTIAL.fullmatch(segment) for segment in unquote(path).strip('/').split('/'))

class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,address):super().__init__(host,timeout=20,context=_ssl_context());self.address=address
    def connect(self):
        raw=socket.create_connection((self.address,443),self.timeout)
        self.sock=self._context.wrap_socket(raw,server_hostname=self.host)

class PublicFetcher:
    """No cookies/auth, verified TLS, pinned public DNS IP, bounded manual redirects."""
    def __init__(self,*,resolver=socket.getaddrinfo,connection_factory=_PinnedHTTPS):self.resolver=resolver;self.connection_factory=connection_factory
    def get(self,url,*,check_destination,max_bytes=10_000_000):
        visited=[]
        for _ in range(6):
            host,addresses=public_url(url,self.resolver);check_destination(host);parts=urlsplit(url)
            connection=self.connection_factory(host,addresses[0])
            try:
                connection.request('GET',(parts.path or '/') + ('?'+parts.query if parts.query else ''),headers={'Host':host,'User-Agent':'Jarvis-Personal-Research/1.0','Accept-Encoding':'identity'})
                response=connection.getresponse()
                if response.status in {301,302,303,307,308}:
                    location=response.getheader('Location')
                    if not location:raise RuntimeError('redirect destination missing')
                    visited.append(url);url=urljoin(url,location);continue
                if response.status!=200:raise RuntimeError(f'public source returned HTTP {response.status}')
                data=response.read(max_bytes+1)
                if len(data)>max_bytes:raise ValueError('download exceeds bounded size')
                return {'url':url,'redirects':visited,'content_type':response.getheader('Content-Type') or 'application/octet-stream','content':data}
            finally:connection.close()
        raise PermissionError('too many redirects')

class NativeCUAAdapter:
    """Actual installed Hermes namespaced computer-use API; no daemon mode changes."""
    def __init__(self,*,session_id,network_guard=None):self.session_id=session_id;self.network_guard=network_guard
    def _call(self,action,**args):
        from tools.computer_use.tool import handle_computer_use
        value=handle_computer_use({'action':action,**args},session_id=self.session_id)
        value=json.loads(value) if isinstance(value,str) else value
        if value.get('success') is False or value.get('error') or value.get('isError'):raise RuntimeError('native computer capability refused: '+str(value.get('error','driver error')))
        return value
    def state(self,*,pid,window_id,tab_id=None):
        bound=self._call('cua_browser_state',pid=pid,window_id=window_id)
        if tab_id is None:return bound
        snapshot=self._call('cua_browser_state',tab_id=tab_id)
        # Retain native exact-bind metadata alongside fresh semantic page refs.
        return {**bound,**snapshot,'tabs':bound.get('tabs',snapshot.get('tabs',[]))}

    def prepare(self,*,pid,window_id):return self._call('cua_browser_prepare',pid=pid,window_id=window_id,profile_mode='existing_profile',allow_launch=False)
    def navigate(self,*,tab_id,url):return self._call('cua_browser_navigate',tab_id=tab_id,url=url)
    def type_field(self,*,tab_id,ref,text):return self._call('cua_browser_type',tab_id=tab_id,ref=ref,text=text,browser_type_mode='insert_text')
    def open_app(self,app):return self._call('focus_app',app=app,raise_window=False)
    def protected_network(self,target):return bool(self.network_guard and self.network_guard(target) is True)

class NativeBrowserAdapter:
    """Maintained Hermes browser toolset for current releases and installed legacy.

    Backend CDP/profile selection remains configured outside this actor. The
    trusted identity probe must attest that session before every action.
    """
    def __init__(self,*,session_id):self.session_id=session_id
    def _call(self,name,**args):
        from tools import browser_tool
        value=getattr(browser_tool,name)(task_id=self.session_id,**args)
        value=json.loads(value) if isinstance(value,str) else value
        if value.get('success') is False or value.get('error'):raise RuntimeError('native browser operation refused: '+str(value.get('error','unavailable')))
        return value
    def state(self,**target):return self._call('browser_snapshot',full=False)
    def navigate(self,*,tab_id,url):return self._call('browser_navigate',url=url)
    def type_field(self,*,tab_id,ref,text):return self._call('browser_type',ref=ref,text=text)
    def open_app(self,app):return NativeCUAAdapter(session_id=self.session_id).open_app(app)
    def protected_network(self,target):return False

class BrowserTasks:
    def __init__(self,permissions,*,download_root,fetcher=None,native=None,identity_probe=None,field_probe=None,fixture_urls=()):
        self.permissions=permissions;self.download_root=Path(download_root).absolute();self.fetcher=fetcher or PublicFetcher();self.native=native
        self.identity_probe=identity_probe;self.field_probe=field_probe
        self.fixture_urls=frozenset(fixture_urls)
        for url in self.fixture_urls:
            parsed=urlsplit(url)
            if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('fixture URLs must be exact trusted loopback form routes')
    def _destination(self,url):
        # This list is supplied only by the trusted test harness, never IPC/model.
        if url in self.fixture_urls:return '127.0.0.1', ['127.0.0.1']
        return public_url(url)
    def _check(self,grant_id,operation,*,domain=None,app=None):
        grant=self.permissions.get(grant_id)
        return self.permissions.check(grant_id,operation,context_id=grant['context_id'],account_id=grant['account_id'],profile=grant['profile'],domain=domain,app=app)
    def research(self,grant_id,url):
        grant=self._check(grant_id,'browser.read')
        if grant['account_id']!='public' or grant['profile']!='public-unauthed':raise PermissionError('cookie-free research requires public identity grant')
        value=self.fetcher.get(url,check_destination=lambda host:self._check(grant_id,'browser.read',domain=host),max_bytes=2_000_000)
        if not any(t in value['content_type'] for t in ('text/','json','xml')):raise ValueError('source is a file; use selected download')
        text=value['content'].decode('utf-8',errors='replace')
        self.permissions.audit(grant_id,'browser.read','completed',{'url':value['url'],'bytes':len(value['content'])})
        return {'url':value['url'],'text':text,'source_is_untrusted':True,'injection_signals':detect_prompt_injection(text),'redirects':value['redirects'],'evidence_class':'live public HTTP'}
    def download(self,grant_id,url,filename):
        self._check(grant_id,'browser.download')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._-]{0,149}',filename) or filename.casefold().endswith(('.app','.command','.sh','.exe','.dmg','.pkg')):raise PermissionError('ordinary non-executable filename required')
        for p in (self.download_root,*self.download_root.parents):
            if p.is_symlink():raise PermissionError('download root symlink refused')
        value=self.fetcher.get(url,check_destination=lambda host:self._check(grant_id,'browser.download',domain=host))
        if value['content'].startswith((b'MZ',b'\x7fELF',b'#!',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf')):raise PermissionError('executable download content refused')
        self.download_root.mkdir(parents=True,exist_ok=True)
        path=self.download_root/(str(uuid4())+'-'+filename)
        with path.open('xb') as stream:stream.write(value['content'])
        path.chmod(0o600)
        result={'path':str(path),'bytes':len(value['content']),'sha256':hashlib.sha256(value['content']).hexdigest(),'url':value['url'],'opened_or_executed':False}
        self.permissions.audit(grant_id,'browser.download','completed',result);return result
    def _native_target(self,grant_id,operation,target):
        grant=self._check(grant_id,operation)
        if self.native is None or self.identity_probe is None:raise RuntimeError('native browser identity adapter unavailable')
        actual=self.identity_probe(target)
        if (actual.get('account_id'),actual.get('profile'))!=(grant['account_id'],grant['profile']):raise PermissionError('browser account/profile is unverified or changed')
        if actual.get('app') not in grant['apps']:raise PermissionError('browser application is outside grant')
        if actual.get('sensitive'):raise PermissionError('credential/security surface is outside browser task')
        resource=f"native:{target.get('pid')}:{target.get('window_id')}"
        if grant['resources'] and resource not in grant['resources']:raise PermissionError('native window is outside task grant')
        if not isinstance(target.get('pid'),int) or not isinstance(target.get('window_id'),int):raise ValueError('exact native pid/window required')
        return grant
    def native_read(self,grant_id,target):
        self._native_target(grant_id,'browser.read',target)
        result=self.native.state(**target)
        self.permissions.audit(grant_id,'browser.read','native-state',{'pid':target['pid'],'window_id':target['window_id']})
        return {'native':result,'source_is_untrusted':True}
    def navigate(self,grant_id,target,url):
        self._native_target(grant_id,'browser.navigate',target)
        host,_=self._destination(url);self._check(grant_id,'browser.navigate',domain=host)
        result=self.native.navigate(tab_id=target['tab_id'],url=url)
        actual=self.identity_probe(target)
        observed=actual.get('url')
        try:
            self._native_target(grant_id,'browser.navigate',target)
            if not observed:raise PermissionError('observed browser destination unavailable')
            final_host,_=self._destination(observed);self._check(grant_id,'browser.navigate',domain=final_host)
        except PermissionError:
            self.permissions.audit(grant_id,'browser.navigate','stopped-after-navigation',{'requested_url':url,'observed_url':observed})
            raise
        self.permissions.audit(grant_id,'browser.navigate','native-operation',{'url':url,'observed_url':observed})
        return {'result':result,'observed_url':observed,'browser_network_containment_verified':self.native.protected_network(target),
                'boundary':'Proposed and observed destination checked; browser redirects/subresources are not backend HTTP SSRF isolation.'}
    def prepare_field(self,grant_id,target,*,ref,text):
        self._native_target(grant_id,'browser.form',target)
        if self.field_probe is None:raise RuntimeError('trusted native field inspector unavailable')
        field=self.field_probe(target,ref)
        if field.get('type') not in {'text','textarea','search','email','tel'} or field.get('role') not in {'textbox','searchbox'}:raise PermissionError('only current ordinary text fields can be prepared')
        if field.get('sensitive') or CONSEQUENTIAL.search(str(field.get('label',''))) or any(p.search(text) for p in SECRET_PATTERNS):raise PermissionError('credential/consequential field blocked')
        if len(text)>10000 or '\n' in text and field.get('type')!='textarea':raise ValueError('bounded text insertion required')
        host,_=self._destination(field['url']);self._check(grant_id,'browser.form',domain=host)
        result=self.native.type_field(tab_id=target['tab_id'],ref=ref,text=text)
        self.permissions.audit(grant_id,'browser.form','prepared',{'ref':ref,'characters':len(text),'possible_autosave':True})
        return {'result':result,'submitted':False,'possible_autosave':True,'browser_network_containment_verified':self.native.protected_network(target)}
    def open_app(self,grant_id,app):
        self._check(grant_id,'apps.open',app=app)
        if not self.native:raise RuntimeError('native app capability unavailable')
        return self.native.open_app(app)
