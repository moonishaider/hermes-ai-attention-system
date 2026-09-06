"""Additive exact-read authorship receipts; never upgrades cached fact subjects."""
import hashlib
import json
import re
from pathlib import Path
from .documents import _locked
from .dloa_observations import observation_items
from .slack_identity import thread_author_receipt,verified_author,exact_parent_body


def retain_author_receipt(workspace,conversation_id,manifest_id,evidence_id,authenticated_payload):
    """Trusted collector boundary only. Never register this payload API as a model tool."""
    with _locked(workspace.root):
        state=workspace._read();manifest=state.get('manifests',{}).get(manifest_id)
        if not manifest or manifest.get('conversation_id')!=conversation_id:raise PermissionError('Exact conversation manifest required')
        matches=[i for i in observation_items(manifest) if i['evidence_id']==evidence_id]
        if not matches:raise ValueError('Retained evidence unavailable')
        item=matches[0];ref=item.get('source_ref') or '';match=re.search(r'/archives/(C[A-Z0-9]+)/p(\d+)',ref)
        if not match:raise ValueError('Exact Slack source permalink required')
        channel=match[1];digits=match[2];ts=digits[:-6]+'.'+digits[-6:]
        receipt=thread_author_receipt(authenticated_payload,channel_id=channel,message_ts=ts,connection_id=item['connection_id'])
        verified_author(item,receipt,channel_id=channel,message_ts=ts)
        identity=hashlib.sha256(json.dumps([conversation_id,manifest_id,item['connection_id'],channel,ts],sort_keys=True).encode()).hexdigest()
        body=exact_parent_body(authenticated_payload)
        event={'authenticated_body':body,'authenticated_body_sha256':hashlib.sha256(body.encode()).hexdigest(),'evidence_id':evidence_id,'manifest_id':manifest_id,'conversation_id':conversation_id,'original_text_sha256':item['sha256'],'receipt':receipt,'fact_subject_verified':False}
        events=state.setdefault('identity_verifications',{})
        if identity in events:
            if events[identity]!=event:raise ValueError('Existing identity verification differs; keep separate reviewed revision')
            return {'verified':True,'receipt_id':identity,'cacheHit':True,'fact_subject_verified':False}
        events[identity]=event;workspace._save(state)
        return {'verified':True,'receipt_id':identity,'cacheHit':False,'fact_subject_verified':False}


def review_author_facts(workspace,conversation_id,manifest_id,receipt_ids,owner_id,reviewer):
    """At most two verified messages, one durably claimed semantic review call."""
    from .dloa_synthesis import _spans,_validate_rows
    if not isinstance(receipt_ids,list) or not 1<=len(receipt_ids)<=2 or len(set(receipt_ids))!=len(receipt_ids):raise ValueError('One or two exact identity receipts required')
    with _locked(workspace.root):
        state=workspace._read();manifest=state.get('manifests',{}).get(manifest_id)
        if not manifest or manifest.get('conversation_id')!=conversation_id:raise PermissionError('Exact conversation manifest required')
        items={i['evidence_id']:i for i in observation_items(manifest)};batch=[];keys={};events={}
        for identity in receipt_ids:
            event=state.get('identity_verifications',{}).get(identity,{})
            if event.get('conversation_id')!=conversation_id or event.get('manifest_id')!=manifest_id:raise PermissionError('Exact identity receipt manifest required')
            item=items[event['evidence_id']]
            if event['original_text_sha256']!=item['sha256'] or event['receipt']['author_id']!=owner_id:raise PermissionError('Verified author does not match configured owner')
            body=event['authenticated_body']
            if hashlib.sha256(body.encode()).hexdigest()!=event['authenticated_body_sha256']:raise PermissionError('Authenticated body hash differs')
            derived={**item,'text':body,'sha256':event['authenticated_body_sha256'],'actor_state':'owner','actor_id':owner_id};batch.append(derived);events[item['evidence_id']]=event
            keys[item['evidence_id']]=hashlib.sha256(json.dumps([item['sha256'],event,'identity-facts-v1'],sort_keys=True).encode()).hexdigest()
        request_key=hashlib.sha256(json.dumps(sorted(keys.values())).encode()).hexdigest()
        attempts=state.setdefault('identity_fact_attempts',{})
        if request_key in attempts:return {'status':attempts[request_key]['status'],'cacheHit':True,'modelCalled':False,'attemptId':request_key}
        payload=[{k:i.get(k) for k in ('evidence_id','occurred_at','actor_id')}|{'source_spans':_spans(i)} for i in batch]
        prompt='Extract only owner message acts and referenced work from these exact authenticated Slack messages. Author identity is verified, but named people and quoted reports are not owner actions. Return JSON {"items":[{"evidence_id":"exact","facts":[{"text":"concise supported fact","span_start":"exact opaque span_id string","span_end":"exact opaque span_id string","attribution":"owner|other|uncertain","event_basis":"message_act|referenced_event|unknown"}],"limitations":[]}]}. A message_act is saying, asking, giving feedback or reminding in this very message, dated at its message timestamp. Referenced meetings/work do NOT inherit posting time. Do not infer missing referenced action or details from an unavailable image. Use the exact span_id strings supplied in source_spans, never numeric start/end character offsets. No facts outside original source spans.\n'+json.dumps(payload,ensure_ascii=False)
        if len(prompt)>16000:raise ValueError('Affected identity review exceeds short-message budget')
        attempts[request_key]={'status':'running','receipt_ids':receipt_ids,'conversation_id':conversation_id,'manifest_id':manifest_id,'request_sha256':hashlib.sha256(prompt.encode()).hexdigest()};workspace._save(state)
    response={}
    try:
        response=reviewer(prompt)
        if not response.get('success'):raise ValueError('Identity fact review did not complete')
        value=json.loads(response['text'].strip().removeprefix('```json').removesuffix('```'));bases={}
        for row in value['items']:
            bases[row['evidence_id']]=[]
            for fact in row['facts']:
                basis=fact.pop('event_basis')
                if basis not in {'message_act','referenced_event','unknown'}:raise ValueError('Invalid activity-time basis')
                bases[row['evidence_id']].append(basis)
        normalized=_validate_rows(value,batch,keys,span_mode=True)
        with _locked(workspace.root):
            state=workspace._read()
            for item in batch:
                state.setdefault('identity_fact_versions',{})[item['evidence_id']]={'version_id':keys[item['evidence_id']],'identity_receipt':events[item['evidence_id']],'facts':normalized[keys[item['evidence_id']]]['facts'],'event_bases':bases[item['evidence_id']],'original_text_sha256':events[item['evidence_id']]['original_text_sha256'],'manifest_id':manifest_id,'conversation_id':conversation_id,'semantic_validation':'model-derived subject/time classification; exact spans checked'}
            state['identity_fact_attempts'][request_key].update(status='completed',model_receipt=response);workspace._save(state)
        return {'status':'completed','attemptId':request_key,'modelCalled':True,'items':len(batch)}
    except Exception as error:
        with _locked(workspace.root):
            state=workspace._read();state['identity_fact_attempts'][request_key].update(status='uncertain',error=type(error).__name__,model_receipt=response);workspace._save(state)
        return {'status':'uncertain','attemptId':request_key,'modelCalled':True,'message':'Affected review did not validate; original facts preserved, no automatic retry.'}


async def hydrate_owner_messages(items,plan,reader,cache_root,*,budget=8,timeout_seconds=8):
    """Bounded authenticated exact reads for normal collection, before manifest creation."""
    import asyncio,time
    from .slack_identity import exact_parent_body
    root=Path(cache_root);root.mkdir(parents=True,exist_ok=True,mode=0o700)
    cache_path=root/'authors.json';remaining=[max(0,min(int(budget),20))];semaphore=asyncio.Semaphore(2);counts={'verified':0,'read':0,'cached':0,'unverified':0}
    async def hydrate(item):
        ref=item.get('source_ref') or '';match=re.search(r'/archives/(C[A-Z0-9]+)/p(\d+)',ref)
        if not match:counts['unverified']+=1;return item
        channel=match[1];digits=match[2];ts=digits[:-6]+'.'+digits[-6:];search_sha=hashlib.sha256(item['text'].encode()).hexdigest();key=hashlib.sha256(json.dumps([plan.connection_id,plan.account_id,channel,ts]).encode()).hexdigest()
        async with semaphore:
            with _locked(root):
                state=json.loads(cache_path.read_text()) if cache_path.exists() else {};entry=state.get(key,{})
                hit=entry.get('status')=='verified' and entry.get('search_sha256')==search_sha
                if not hit:
                    if not remaining[0] or (entry.get('status')=='reading' and time.time()-entry.get('started_at',0)<120):counts['unverified']+=1;return item
                    remaining[0]-=1;counts['read']+=1;state[key]={'status':'reading','started_at':time.time(),'search_sha256':search_sha};temporary=cache_path.with_suffix('.tmp');temporary.write_text(json.dumps(state));temporary.chmod(0o600);temporary.replace(cache_path)
            try:
                if hit:counts['cached']+=1
                else:
                    payload=await asyncio.wait_for(reader(channel,ts),timeout=timeout_seconds)
                    receipt=thread_author_receipt(payload,channel_id=channel,message_ts=ts,connection_id=plan.connection_id);body=exact_parent_body(payload)
                    entry={'status':'verified','search_sha256':search_sha,'receipt':receipt,'body':body,'body_sha256':hashlib.sha256(body.encode()).hexdigest()}
                    with _locked(root):
                        state=json.loads(cache_path.read_text());state[key]=entry;temporary=cache_path.with_suffix('.tmp');temporary.write_text(json.dumps(state));temporary.chmod(0o600);temporary.replace(cache_path)
                candidate={**item,'connection_id':plan.connection_id};verified_author(candidate,entry['receipt'],channel_id=channel,message_ts=ts)
                if hashlib.sha256(entry['body'].encode()).hexdigest()!=entry['body_sha256']:raise ValueError('Exact body cache hash differs')
                counts['verified']+=1
                return {**item,'text':entry['body'],'actor_id':entry['receipt']['author_id'],'provenance':{**item.get('provenance',{}),'verified_author_receipt':entry['receipt'],'verified_body_sha256':entry['body_sha256'],'search_text_sha256':search_sha,'body_source':'authenticated exact thread parent; original search digest retained'}}
            except Exception:
                counts['unverified']+=1;return item
    hydrated=await asyncio.gather(*(hydrate(item) for item in items))
    return hydrated,{**counts,'remaining_budget':remaining[0]}


def revalidate_author_response(workspace,conversation_id,manifest_id,attempt_id,attempt_digest,owner_id):
    """Local acknowledgement of a complete known response; never invokes a model."""
    from .dloa_synthesis import _spans,_validate_rows
    with _locked(workspace.root):
        state=workspace._read();attempt=state.get('identity_fact_attempts',{}).get(attempt_id,{})
        digest=hashlib.sha256(json.dumps(attempt,sort_keys=True).encode()).hexdigest()
        if digest!=attempt_digest or attempt.get('status')!='uncertain' or attempt.get('error')!='ValueError' or attempt.get('conversation_id')!=conversation_id or attempt.get('manifest_id')!=manifest_id:raise PermissionError('Exact known failed identity response required')
        response=attempt.get('model_receipt',{});text=response.get('text')
        if response.get('success') is not True or response.get('response_received') is not True or response.get('usage_known') is not True or not isinstance(text,str) or not text or response.get('prompt_sha256')!=attempt.get('request_sha256') or not response.get('model_attempt_id'):raise PermissionError('Complete received response and exact request receipt required')
        manifest=state['manifests'][manifest_id];items={i['evidence_id']:i for i in observation_items(manifest)};batch=[];events={};keys={}
        for receipt_id in attempt['receipt_ids']:
            event=state['identity_verifications'][receipt_id];item=items[event['evidence_id']];body=event['authenticated_body']
            if event['manifest_id']!=manifest_id or event['conversation_id']!=conversation_id or event['original_text_sha256']!=item['sha256'] or event['receipt']['author_id']!=owner_id or hashlib.sha256(body.encode()).hexdigest()!=event['authenticated_body_sha256']:raise PermissionError('Exact authenticated evidence changed')
            batch.append({**item,'text':body,'sha256':event['authenticated_body_sha256'],'actor_id':owner_id,'actor_state':'owner'});events[item['evidence_id']]=event;keys[item['evidence_id']]=hashlib.sha256(json.dumps([item['sha256'],event,'identity-facts-v1'],sort_keys=True).encode()).hexdigest()
        value=json.loads(text.strip().removeprefix('```json').removesuffix('```'));by_id={i['evidence_id']:i for i in batch};bases={}
        for row in value['items']:
            item=by_id[row['evidence_id']];spans=_spans(item);starts={span['start']:span for span in spans};ends={span['end']:span for span in spans};bases[row['evidence_id']]=[]
            for fact in row['facts']:
                start=fact['span_start'];end=fact['span_end']
                if type(start) is int and type(end) is int:
                    if start not in starts or end not in ends or start>=end:raise ValueError('Numeric offsets must equal existing same-item span boundaries')
                    fact['span_start']=starts[start]['span_id'];fact['span_end']=ends[end]['span_id']
                elif not isinstance(start,str) or not isinstance(end,str):raise ValueError('Span IDs or exact integer boundaries required')
                basis=fact.pop('event_basis')
                if basis not in {'message_act','referenced_event','unknown'}:raise ValueError('Invalid activity-time basis')
                bases[row['evidence_id']].append(basis)
        normalized=_validate_rows(value,batch,keys,span_mode=True)
        receipt={'attemptId':attempt_id,'attemptDigest':digest,'responseSha256':hashlib.sha256(text.encode()).hexdigest(),'modelAttemptId':response['model_attempt_id'],'modelCalled':False,'normalization':'exact existing source-span boundaries only','items':len(batch)}
        prior=state.setdefault('identity_local_revalidations',{}).get(attempt_id)
        if prior:
            if prior!=receipt:raise PermissionError('Conflicting local response acknowledgement')
            return {'status':'revalidated','cacheHit':True,**receipt}
        for item in batch:
            state.setdefault('identity_fact_versions',{})[item['evidence_id']]={'version_id':keys[item['evidence_id']],'identity_receipt':events[item['evidence_id']],'facts':normalized[keys[item['evidence_id']]]['facts'],'event_bases':bases[item['evidence_id']],'original_text_sha256':events[item['evidence_id']]['original_text_sha256'],'manifest_id':manifest_id,'conversation_id':conversation_id,'semantic_validation':'model-derived subject/time classification; exact spans checked'}
        state['identity_local_revalidations'][attempt_id]=receipt;workspace._save(state)
        return {'status':'revalidated','cacheHit':False,**receipt}
