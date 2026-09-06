import type { ConversationRun } from './conversationRuns';
export function reportRetryIdentity(run:ConversationRun,storage:Pick<Storage,'getItem'|'setItem'>,uuid:()=>string){
 const sourceRunId=run.reportRecovery?.sourceRunId??run.runId;
 if(!sourceRunId)throw new Error('Report recovery origin unavailable');
 const key=`jarvis.report-retry.${sourceRunId}`;
 const newTurnId=run.reportRecovery?.newTurnId??storage.getItem(key)??uuid();
 storage.setItem(key,newTurnId);
 return {sourceRunId,newTurnId};
}
export const retainRecoveredRun=(status:string,persistencePending?:boolean,reportRecovery?:ConversationRun['reportRecovery'])=>!['completed','cancelled','failed','interrupted'].includes(status)||Boolean(persistencePending||reportRecovery);
