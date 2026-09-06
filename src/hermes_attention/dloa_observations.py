"""Pure resource-observation views; raw manifests and provider IDs stay immutable."""
import copy
import hashlib
import json

FIELDS=('sha256','text','actor_id','actor_state','source_claims_owner','source','source_id','connection_id','account_id','occurred_at','source_ref','kind','provenance')
def _digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def observation_items(manifest):
    groups={}
    for source in manifest['sources']:
        for item in source['items']:
            identity=item['evidence_id'];values={k:item.get(k) for k in FIELDS}
            if values['source'] in {'slack-owner','slack-colleagues'}:values['source']='slack'
            signature=_digest(values)
            groups.setdefault(identity,{}).setdefault(signature,[]).append(item)
    result=[]
    for identity,variants in groups.items():
        for signature,copies in sorted(variants.items()):
            item=copy.deepcopy(min(copies,key=lambda i:(str(i.get('source')),json.dumps(i,sort_keys=True,ensure_ascii=False))))
            if len(copies)>1:
                item['observation_collection_sources']=sorted({i.get('source') for i in copies})
                item['observation_collection_scopes']=[{k:source.get(k) for k in ('source','scope','connection_id','account_id')} for source in manifest['sources'] if source.get('source') in item['observation_collection_sources']]
            if len(variants)>1:
                item['resource_evidence_id']=identity;item['evidence_id']='obs_'+_digest([identity,signature])
            result.append(item)
    return result

def original_item(item):
    return {**item,'evidence_id':item.get('resource_evidence_id',item['evidence_id'])}

def valid_cache(record,item):
    if not isinstance(record,dict) or record.get('status')!='processed' or not isinstance(record.get('facts'),list) or not isinstance(record.get('limitations'),list) or not all(isinstance(x,str) for x in record['limitations']):return False
    return bool(record.get('evidence_id')==item['evidence_id'] and record.get('source_sha256')==item['sha256'] and hashlib.sha256(item['text'].encode()).hexdigest()==item['sha256'] and all(isinstance(f,dict) and set(f)=={'text','quote','attribution'} and isinstance(f['text'],str) and f['text'].strip() and isinstance(f['quote'],str) and f['quote'] and f['quote'] in item['text'] and f['attribution'] in {'owner','other','uncertain'} and (f['attribution']!='owner' or item.get('actor_state')=='owner') for f in record['facts']))

def adapt_observation_caches(state,manifest):
    """Create only exact receipt-backed cache aliases, under caller's state lock."""
    from .dloa_synthesis import _item_keys
    items=observation_items(manifest);keys=_item_keys(manifest,items);changed=False
    for item in items:
        if 'resource_evidence_id' not in item and not item.get('observation_collection_sources'):continue
        target=keys[item['evidence_id']]
        if target in state.get('extraction_cache',{}) or target in state.get('extraction_observation_aliases',{}):continue
        original=original_item(item);record=None
        for source in item.get('observation_collection_sources',[item.get('source')]):
            candidate={**original,'source':source};source_key=_item_keys(manifest,[candidate])[candidate['evidence_id']]
            possible=state.get('extraction_cache',{}).get(source_key)
            if valid_cache(possible,candidate):record=possible;break
        if record is None:continue
        state['extraction_cache'][target]={**copy.deepcopy(record),'evidence_id':item['evidence_id']}
        state.setdefault('extraction_observation_aliases',{})[target]={'source_key':source_key,'source_receipt_sha256':_digest(record),'resource_evidence_id':original['evidence_id'],'observation_id':item['evidence_id'],'manifest_id':manifest.get('id'),'source_sha256':item['sha256']}
        changed=True
    return changed

def identity_version_for(state,manifest,item):
    identity=item['evidence_id'];resource=item.get('resource_evidence_id',identity)
    version=state.get('identity_fact_versions',{}).get(identity) or state.get('identity_fact_versions',{}).get(resource)
    if not version or version.get('conversation_id')!=manifest.get('conversation_id') or version.get('original_text_sha256')!=item['sha256']:return {}
    if version.get('manifest_id')!=manifest.get('id') and state.get('identity_version_bindings',{}).get(manifest.get('id'),{}).get(identity)!=_digest(version):return {}
    if identity!=resource:
        original=state.get('manifests',{}).get(version.get('manifest_id'),manifest)
        candidates=[i for i in observation_items(original) if i.get('resource_evidence_id',i['evidence_id'])==resource and i['sha256']==item['sha256']]
        if len(candidates)!=1 or any(candidates[0].get(k)!=item.get(k) for k in FIELDS):return {}
    return version
