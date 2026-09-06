import hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from hermes_attention.dloa import DloaWorkspace
from hermes_attention.dloa_synthesis import _item_keys,compact_final_packet,expand_final_packet
from hermes_attention.dloa_final_recovery import diagnose_final,prepare_final

class FinalRecoveryTest(unittest.TestCase):
 def test_lossless_reference_interning(self):
  fact={'text':'fact','quote':'identical long quote '*100,'attribution':'other'}
  packet={'evidence':[{'provenance':{'original':'context'},'validated_extraction':{'facts':[fact,fact]}}],'source_status':['partial'],'skill':{'exact':'owner format'}}
  compact=compact_final_packet(packet);self.assertEqual(expand_final_packet(compact),packet);self.assertLess(len(json.dumps(compact)),len(json.dumps(packet)))
 def test_legacy_exact_residual_receipt_and_new_turn_idempotency(self):
  with tempfile.TemporaryDirectory() as tmp:
   w=DloaWorkspace((Path(tmp)/'dloa').resolve());db=Path(tmp)/'receipts.db';c=sqlite3.connect(db)
   c.executescript('CREATE TABLE model_attempts(attempt_id,feature,provider,model,usage_known,status,created_at);CREATE TABLE usage_events(event_id,occurred_at,provider,model,feature,input_tokens,output_tokens,cost_usd,success);')
   c.execute('INSERT INTO model_attempts VALUES(?,?,?,?,?,?,?)',('model','dloa-synthesis','deepseek','deepseek-v4-pro',1,'IncompleteOutput','2026-09-05T12:01:00+00:00'))
   c.execute('INSERT INTO usage_events VALUES(?,?,?,?,?,?,?,?,?)',(82,'2026-09-05T12:01:00+00:00','deepseek','deepseek-v4-pro','dloa-synthesis',100,8192,.1,0));c.commit()
   item={'evidence_id':'a','sha256':hashlib.sha256(b'exact').hexdigest(),'text':'exact','actor_state':'owner'};m={'skill':{},'sources':[{'items':[item]}]};key=_item_keys(m,[item])['a']
   state={'native_turns':{'s:old':{'manifest_id':'m','owner_request':'original'}},'manifests':{'m':m},'extraction_cache':{key:{'evidence_id':'a','source_sha256':item['sha256'],'status':'processed','limitations':[],'facts':[{'text':'Exact supported fact','quote':'exact','attribution':'owner'}]}},'synthesis_attempts':{'s:old':{'status':'uncertain','manifest_id':'m','started_at':'2026-09-05T12:00:00+00:00','result':{'totalUsageKnown':True,'totalCostKnown':True,'currentTurnModelCalls':1,'totalUsage':{'input_tokens':100,'output_tokens':8192},'totalCostUsd':.1}}}}
   w._save(state);d=diagnose_final(w,db,'s','old');self.assertTrue(d['eligible']);self.assertFalse(d['historicalRequestHashVerified'])
   args=(w,db,'s','old','new',d['finalAttemptDigest'],None,None,'retry')
   self.assertTrue(prepare_final(*args)['finalOnly']);self.assertEqual(prepare_final(*args)['status'],'prepared');self.assertEqual(w._read()['synthesis_attempts'],state['synthesis_attempts'])
   with self.assertRaises(PermissionError):prepare_final(w,db,'s','old','competing',d['finalAttemptDigest'],None,None,'retry')
   c.execute('INSERT INTO usage_events SELECT 83,occurred_at,provider,model,feature,input_tokens,output_tokens,cost_usd,success FROM usage_events');c.commit();self.assertFalse(diagnose_final(w,db,'s','old')['eligible']);c.close()
   for field,value in [('totalUsageKnown',False),('currentTurnModelCalls',2)]:
    altered=json.loads(json.dumps(state));altered['synthesis_attempts']['s:old']['result'][field]=value;w._save(altered);self.assertFalse(diagnose_final(w,db,'s','old')['eligible'])

 def test_final_override_is_feature_bound_and_request_claim_precedes_transport(self):
  from types import SimpleNamespace
  from unittest.mock import patch
  from hermes_attention.runtime_models import DirectModelClient,ModelRouteError
  client=DirectModelClient.__new__(DirectModelClient);client.timeout_seconds=120
  spec={'provider':'deepseek','model':'deepseek-v4-pro','endpoint':'https://api.deepseek.com/chat/completions','thinking':True,'input_usd_per_million':1,'output_usd_per_million':1}
  client.config={'routes':{'difficult':spec},'budget_usd_monthly':{'hard':100}}
  conn=sqlite3.connect(':memory:');self.addCleanup(conn.close);client.store=SimpleNamespace(connection=conn,monthly_cost=lambda m:0,record_usage=lambda **kw:None)
  def transport(request,**kwargs):
   body=json.loads(request.data);self.assertEqual(body['thinking']['type'],'disabled')
   row=conn.execute('select request_sha256 from model_request_claims').fetchone();self.assertEqual(row[0],hashlib.sha256(request.data).hexdigest())
   class Response:
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self):return json.dumps({'choices':[{'message':{'content':'fixture'},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':2}}).encode()
   return Response()
  with patch.object(client,'_secret',return_value='fixture'),patch.object(client,'_tls_context',return_value=None),patch('hermes_attention.runtime_models.urlopen',transport):
   result=client.generate('difficult','fixture',feature='dloa-synthesis',max_output_tokens=8192,thinking_override=False)
   self.assertTrue(result['success']);self.assertTrue(spec['thinking']);self.assertEqual(conn.execute('select attempt_id from model_request_claims').fetchone()[0],result['model_attempt_id'])
   with self.assertRaises(ModelRouteError):client.generate('difficult','fixture',feature='finance',thinking_override=False)
