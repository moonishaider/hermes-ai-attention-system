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
    if not version or version.get('conversation_id')!=manifest.get('conversation_id'):return {}
    if version.get('original_text_sha256')!=item['sha256']:
        return _authenticated_body_version(state,manifest,item,version)
    if version.get('manifest_id')!=manifest.get('id') and state.get('identity_version_bindings',{}).get(manifest.get('id'),{}).get(identity)!=_digest(version):return {}
    if identity!=resource:
        original=state.get('manifests',{}).get(version.get('manifest_id'),manifest)
        candidates=[i for i in observation_items(original) if i.get('resource_evidence_id',i['evidence_id'])==resource and i['sha256']==item['sha256']]
        if len(candidates)!=1 or any(candidates[0].get(k)!=item.get(k) for k in FIELDS):return {}
    return version

def _authenticated_body_version(state,manifest,item,version):
    """Preserve assessed units when a search rendering becomes its exact read body.

    No new subject assessment, source lookup or mutation. Full receipt equality and
    immutable resource metadata bind the earlier facts to this current observation.
    """
    event=version.get('identity_receipt',{});receipt=event.get('receipt',{})
    body=event.get('authenticated_body');provenance=item.get('provenance',{})
    if not isinstance(body,str) or not body or body!=item.get('text'):return {}
    digest=hashlib.sha256(body.encode()).hexdigest()
    if digest!=item.get('sha256') or digest!=event.get('authenticated_body_sha256') or digest!=provenance.get('verified_body_sha256'):return {}
    if not receipt or receipt!=provenance.get('verified_author_receipt') or receipt.get('fact_subject_verified') is not False:return {}
    if item.get('actor_state')!='owner' or not item.get('actor_id') or receipt.get('author_id')!=item['actor_id']:return {}
    if event.get('conversation_id')!=manifest.get('conversation_id') or event.get('manifest_id')!=version.get('manifest_id') or event.get('original_text_sha256')!=version.get('original_text_sha256'):return {}
    original=state.get('manifests',{}).get(version.get('manifest_id'),{})
    if original.get('conversation_id')!=manifest.get('conversation_id'):return {}
    resource=item.get('resource_evidence_id',item['evidence_id'])
    old=[i for i in observation_items(original) if i.get('resource_evidence_id',i['evidence_id'])==resource and i.get('sha256')==version['original_text_sha256']]
    if len(old)!=1 or event.get('evidence_id')!=old[0]['evidence_id']:return {}
    if any(old[0].get(k)!=item.get(k) for k in ('connection_id','account_id','source_id','source_ref','occurred_at','kind')):return {}
    if item.get('source') not in {'slack-owner','slack-colleagues'} or old[0].get('source') not in {'slack-owner','slack-colleagues'}:return {}
    from .slack_identity import verified_author
    try:verified_author(item,receipt,channel_id=receipt.get('channel_id'),message_ts=receipt.get('message_ts'))
    except (ValueError,KeyError):return {}
    facts=version.get('facts');bases=version.get('event_bases')
    if not valid_cache({'status':'processed','facts':facts,'limitations':[],'evidence_id':item['evidence_id'],'source_sha256':digest},item):return {}
    if not isinstance(bases,list) or len(bases)!=len(facts) or any(b not in {'message_act','referenced_event','unknown'} for b in bases):return {}
    lineage={'prior_version_id':version['version_id'],'prior_manifest_id':version['manifest_id'],'current_manifest_id':manifest['id'],'current_evidence_id':item['evidence_id'],'authenticated_body_sha256':digest,'prior_version_sha256':_digest(version)}
    return {**copy.deepcopy(version),'version_id':_digest(['authenticated-body-rebind-v1',lineage]),'manifest_id':manifest['id'],'original_text_sha256':digest,'current_source_lineage':lineage}
