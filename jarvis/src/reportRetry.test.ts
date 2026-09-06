import {expect,it,vi} from 'vitest';
import {reportRetryIdentity,retainRecoveredRun} from './reportRetry';
import type {ConversationRun} from './conversationRuns';
const original={runId:'old',reportRecovery:{kind:'known-incomplete'}} as ConversationRun;
it('retains retry identity after failed invocation and renderer restart',()=>{
 const values=new Map<string,string>();const storage={getItem:(key:string)=>values.get(key)??null,setItem:(key:string,value:string)=>{values.set(key,value);}};
 const uuid=vi.fn().mockReturnValueOnce('new-1').mockReturnValueOnce('must-not-use');
 expect(reportRetryIdentity(original,storage,uuid)).toEqual({sourceRunId:'old',newTurnId:'new-1'});
 expect(reportRetryIdentity({...original},storage,uuid)).toEqual({sourceRunId:'old',newTurnId:'new-1'});
 expect(uuid).toHaveBeenCalledTimes(1);
 const child={runId:'child',reportRecovery:{kind:'known-incomplete',sourceRunId:'old',newTurnId:'native-new'}} as ConversationRun;
 expect(reportRetryIdentity(child,storage,uuid)).toEqual({sourceRunId:'old',newTurnId:'native-new'});
});
it('retains failed reports only with native recovery or pending save',()=>{
 expect(retainRecoveredRun('failed',false,{kind:'known-incomplete'})).toBe(true);
 expect(retainRecoveredRun('failed',false)).toBe(false);
 expect(retainRecoveredRun('completed',true)).toBe(true);
 expect(retainRecoveredRun('unresolved',false)).toBe(true);
});
