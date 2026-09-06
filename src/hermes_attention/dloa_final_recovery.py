"""Exact known final-output recovery; never invokes a model or a source collector."""
import hashlib
import json
import sqlite3
from pathlib import Path
from datetime import datetime,timedelta
from .documents import _locked
from .dloa_synthesis import _item_keys


def cache_complete(state,manifest):
    from .dloa_observations import observation_items,adapt_observation_caches,valid_cache
    import copy
    state=copy.deepcopy(state);adapt_observation_caches(state,manifest)
    items=observation_items(manifest);keys=_item_keys(manifest,items)
    for item in items:
        cached=state.get('extraction_cache',{}).get(keys[item['evidence_id']],{})
        if not valid_cache(cached,item):return False
    return True


def _evidence_digest(state,key):
    binding=state.get('native_turns',{}).get(key,{})
    value={k:state.get(k,{}) for k in ('manifests','extraction_attempts','extraction_cache','extraction_recoveries','extraction_local_revalidations','extraction_local_edges','synthesis_attempts')}
    value['selected_binding']=binding
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def diagnose_final(workspace,database,session_id,turn_id):
    with _locked(workspace.root):state=workspace._read()
    key=session_id+':'+turn_id;bindings=state.get('native_turns',{});binding=bindings.get(key,{});attempt=state.get('synthesis_attempts',{}).get(key,{})
    result={'eligible':False,'sessionId':session_id,'failedTurnId':turn_id,'lineageTurnIds':[],'modelCalled':False}
    current=key
    while current:
        if current in [session_id+':'+t for t in result['lineageTurnIds']] or len(result['lineageTurnIds'])>=32:return result
        row=bindings.get(current)
        if not row or not current.startswith(session_id+':') or row.get('manifest_id')!=binding.get('manifest_id'):return result
        result['lineageTurnIds'].append(current[len(session_id)+1:]);parent=row.get('recovery_of')
        if parent:
            valid=False
            for r in state.get('extraction_recoveries',{}).values():
                a=state.get('extraction_attempts',{}).get(r.get('batchId'),{})
                if r.get('sessionId')==session_id and session_id+':'+r.get('newTurnId','')==current and session_id+':'+r.get('failedTurnId','')==parent and r.get('attemptDigest')==hashlib.sha256(json.dumps(a,sort_keys=True).encode()).hexdigest():valid=True
            edge=state.get('extraction_local_edges',{}).get(current,{})
            if edge.get('parent')==parent and edge.get('batches'):
                valid=all(state.get('extraction_local_revalidations',{}).get(bid,{}).get('attemptDigest')==digest and hashlib.sha256(json.dumps(state.get('extraction_attempts',{}).get(bid,{}),sort_keys=True).encode()).hexdigest()==digest for bid,digest in edge['batches'].items())
            if not valid:return result
        current=parent
    if attempt.get('status')!='uncertain' or attempt.get('manifest_id')!=binding.get('manifest_id'):return result
    manifest=state.get('manifests',{}).get(binding.get('manifest_id'))
    if not manifest or not cache_complete(state,manifest):return result
    # Final retry only consumes validated immutable extraction; unknown attempts anywhere
    # in its ancestry still require their own positively known recovery receipts.
    lineage={session_id+':'+t for t in result['lineageTurnIds']}
    for origin,a in state.get('synthesis_attempts',{}).items():
        if origin in lineage and origin!=key:return result
    for bid,a in state.get('extraction_attempts',{}).items():
        if a.get('origin_turn') not in lineage or a.get('status')=='completed':continue
        digest=hashlib.sha256(json.dumps(a,sort_keys=True).encode()).hexdigest()
        if not any(r.get('batchId')==bid and r.get('attemptDigest')==digest and r.get('sessionId')==session_id and session_id+':'+r.get('newTurnId','') in lineage for r in state.get('extraction_recoveries',{}).values()) and state.get('extraction_local_revalidations',{}).get(bid,{}).get('attemptDigest')!=digest:return result
    own=[a for a in state.get('extraction_attempts',{}).values() if a.get('origin_turn')==key]
    if any(a.get('status')!='completed' or not a.get('usage',{}).get('usage_known') for a in own):return result
    if any(any(type(a['usage'].get(k)) is not int or a['usage'][k]<0 for k in ('input_tokens','output_tokens')) or not isinstance(a['usage'].get('estimated_cost_usd'),(int,float)) or a['usage']['estimated_cost_usd']<0 for a in own):return result
    receipt=attempt.get('failure_receipt',{});method='saved final request and model receipt'
    if receipt:
        if receipt.get('error_class')!='IncompleteOutput' or receipt.get('response_received') is not True or receipt.get('usage_known') is not True or not receipt.get('request_sha256') or receipt.get('prompt_sha256')!=attempt.get('prompt_sha256'):return result
        tokens={k:receipt.get(k) for k in ('input_tokens','output_tokens')};cost=receipt.get('estimated_cost_usd')
    else:
        if key in state.get('style_review_attempts',{}):return result
        total=attempt.get('result',{});method='legacy unique residual usage receipt'
        if not total.get('totalUsageKnown') or not total.get('totalCostKnown') or total.get('currentTurnModelCalls')!=len(own)+1:return result
        tokens={k:total['totalUsage'][k]-sum(a['usage'][k] for a in own) for k in ('input_tokens','output_tokens')};cost=total['totalCostUsd']-sum(a['usage']['estimated_cost_usd'] for a in own)
    if any(type(v) is not int or v<0 for v in tokens.values()) or not isinstance(cost,(int,float)) or cost<0:return result
    path=Path(database)
    if not path.exists() or path.is_symlink():return result
    matches=[];started=datetime.fromisoformat(attempt['started_at'])
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as conn:
        conn.row_factory=sqlite3.Row
        if receipt:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='model_request_claims'").fetchone():return result
            claim=conn.execute('SELECT * FROM model_request_claims WHERE attempt_id=?',(receipt.get('model_attempt_id'),)).fetchone()
            if not claim or claim['request_sha256']!=receipt['request_sha256'] or claim['prompt_sha256']!=attempt['prompt_sha256'] or claim['feature']!='dloa-synthesis' or claim['model']!=receipt.get('model'):return result
        for model in conn.execute("SELECT * FROM model_attempts WHERE feature='dloa-synthesis' AND status='IncompleteOutput' AND usage_known=1 AND model='deepseek-v4-pro'"):
            if receipt and model['attempt_id']!=receipt.get('model_attempt_id'):continue
            when=datetime.fromisoformat(model['created_at'])
            if not started<=when<=started+timedelta(seconds=180):continue
            for usage in conn.execute("SELECT * FROM usage_events WHERE feature='dloa-synthesis' AND provider=? AND model=? AND success=0",(model['provider'],model['model'])):
                if abs((datetime.fromisoformat(usage['occurred_at'])-when).total_seconds())>2:continue
                if any(usage[k]!=tokens[k] for k in tokens) or cost is None or abs(usage['cost_usd']-cost)>1e-9:continue
                matches.append((model['attempt_id'],usage['event_id']))
    if len(matches)!=1:return result
    children={child[len(session_id)+1:] for child,r in state.get('final_recoveries',{}).items() if r.get('parent')==key}
    if len(children)>1:return result
    return {**result,'eligible':True,'recoveryEvidenceDigest':_evidence_digest(state,key),'manifestId':binding['manifest_id'],'finalAttemptDigest':hashlib.sha256(json.dumps(attempt,sort_keys=True).encode()).hexdigest(),'modelAttemptId':matches[0][0],'usageEventId':matches[0][1],'linkage_method':method,'historicalRequestHashVerified':bool(receipt),'historicalResponseAvailable':bool(attempt.get('failed_response_text')) and attempt.get('failed_response_truncated') is False and hashlib.sha256(attempt.get('failed_response_text','').encode()).hexdigest()==attempt.get('failed_response_sha256'),'acknowledgedNewTurnId':next(iter(children)) if children else None}


def prepare_final(workspace,database,session_id,failed_turn_id,new_turn_id,digest,model_attempt_id,usage_event_id,owner_text):
    if failed_turn_id==new_turn_id:raise PermissionError('Final recovery requires a new canonical turn')
    diagnosis=diagnose_final(workspace,database,session_id,failed_turn_id)
    if not diagnosis['eligible'] or diagnosis['finalAttemptDigest']!=digest or (model_attempt_id is not None and model_attempt_id!=diagnosis['modelAttemptId']) or (usage_event_id is not None and usage_event_id!=diagnosis['usageEventId']):raise PermissionError('Exact proven final-output receipt required')
    model_attempt_id=diagnosis['modelAttemptId'];usage_event_id=diagnosis['usageEventId']
    oldkey=session_id+':'+failed_turn_id;key=session_id+':'+new_turn_id
    with _locked(workspace.root):
        state=workspace._read();old=state['native_turns'][oldkey]
        if _evidence_digest(state,oldkey)!=diagnosis['recoveryEvidenceDigest']:raise PermissionError('Recovery evidence changed since diagnosis')
        if hashlib.sha256(json.dumps(state['synthesis_attempts'][oldkey],sort_keys=True).encode()).hexdigest()!=digest:raise PermissionError('Final receipt changed')
        recoveries=state.setdefault('final_recoveries',{})
        if any(child!=key and r['parent']==oldkey for child,r in recoveries.items()):raise PermissionError('Resume the existing final recovery turn')
        binding={'manifest_id':old['manifest_id'],'owner_request':old['owner_request']+'\nCurrent owner recovery request: '+owner_text,'recovery_of':oldkey,'final_only':True}
        if key in state['native_turns'] and state['native_turns'][key]!=binding:raise PermissionError('Conflicting new turn')
        receipt={'parent':oldkey,'finalAttemptDigest':digest,'modelAttemptId':model_attempt_id,'usageEventId':usage_event_id,'linkage_method':diagnosis['linkage_method']}
        if key in recoveries and recoveries[key]!=receipt:raise PermissionError('Conflicting final receipt')
        recoveries[key]=receipt;state['native_turns'][key]=binding;workspace._save(state)
    return {'status':'prepared','manifestId':old['manifest_id'],'finalAttemptDigest':digest,'finalOnly':True,'modelCalled':False}
