import json,unittest
from hermes_attention.companion import CompanionBoundary
class CompanionTests(unittest.TestCase):
 def setUp(self):
  self.now=1.;self.calls=[];self.boundary=CompanionBoundary(origin='https://jarvis.private.test',enabled=True,clock=lambda:self.now,handlers={'health':lambda args:self.calls.append(args) or {'state':'ready'},'start_run':lambda _:self.fail('native write exposed')})
 def request(self,path,**kw):return self.boundary.request(method='POST',path=path,host='jarvis.private.test',origin='https://jarvis.private.test',secure_transport=True,**kw)
 def login(self):
  code=self.boundary.pairing_code(owner_authorized=True);result=self.request('/api/login',body=json.dumps({'code':code}).encode());return result.headers['Set-Cookie'].split(';')[0],result.body['csrf']
 def test_default_disabled_and_no_pairing_authority(self):
  self.assertEqual(CompanionBoundary().status()['state'],'transport-blocked')
  with self.assertRaises(PermissionError):CompanionBoundary().pairing_code(owner_authorized=True)
 def test_cookie_csrf_and_native_operation_boundary(self):
  cookie,csrf=self.login();self.assertNotIn('Jarvis=',csrf)
  self.assertEqual(self.request('/api/invoke',cookie=cookie,body=b'{"command":"health"}').status,403)
  self.assertEqual(self.request('/api/invoke',cookie=cookie,csrf=csrf,body=b'{"command":"health"}').status,200)
  self.assertEqual(self.request('/api/invoke',cookie=cookie,csrf=csrf,body=b'{"command":"start_run"}').status,403)
  self.assertEqual(len(self.calls),1)
 def test_cross_origin_tls_expiry_logout(self):
  cookie,csrf=self.login()
  bad=self.boundary.request(method='POST',path='/api/session',host='jarvis.private.test',origin='https://evil.test',secure_transport=True,cookie=cookie)
  self.assertEqual(bad.status,403)
  self.assertEqual(self.request('/api/logout',cookie=cookie,csrf=csrf).status,200);self.assertEqual(self.request('/api/session',cookie=cookie).status,401)
 def test_pairing_is_single_use_expiring_and_rate_limited(self):
  code=self.boundary.pairing_code(owner_authorized=True);payload=json.dumps({'code':code}).encode()
  self.assertEqual(self.request('/api/login',body=payload).status,200);self.assertEqual(self.request('/api/login',body=payload).status,401)
  for _ in range(4):self.request('/api/login',body=b'{}')
  self.assertEqual(self.request('/api/login',body=b'{}').status,429)
