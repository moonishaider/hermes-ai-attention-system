import { useEffect, useRef, useState } from 'react';
import { invoke, isCompanion } from './transport';
interface Reminder {taskId:string; title:string; occurrence:string; version:string; context:string;}
const call = <T,>(operation:string, request:Record<string,unknown>) => invoke<T>('workspace_operation', {operation:'awareness.'+operation,request});
export function TaskReminders({context, duringChat, query}:{context:string;duringChat:boolean;query:string}) {
  const [task,setTask]=useState<Reminder|null>(null);
  const [error,setError]=useState('');
  const showing=useRef(false);
  const epoch=useRef(0);
  useEffect(() => {
    if(isCompanion())return;
    let active=true, pending=false;epoch.current++;
    setTask(null);setError('');showing.current=false;
    const request={context,duringChat,query};
    async function poll() {
      if(pending || showing.current || document.visibilityState==='hidden')return;
      pending=true;
      try {
        const result=await call<{data:Reminder[]}>('reminders.pending',request);
        if(!active)return;
        const next=result.data?.[0];if(!next)return;
        showing.current=true;setTask(next);
      } catch(e) { if(active)setError(`Reminder check needs attention: ${String(e)}`); }
      finally {pending=false;}
    }
    void poll();const timer=window.setInterval(()=>void poll(),30000);
    return ()=>{active=false;epoch.current++;window.clearInterval(timer);};
  },[context,duringChat,query]);
  async function snooze() {
    if(!task)return;
    const owner=epoch.current;
    try {await call('task.transition',{taskId:task.taskId,expectedVersion:task.version,action:'snooze',until:new Date(Date.now()+10*60000).toISOString()});if(epoch.current===owner){showing.current=false;setTask(null);}}
    catch(e){if(epoch.current===owner)setError(`Snooze needs attention: ${String(e)}`);}
  }
  async function dismiss() {
    if(!task)return;
    const owner=epoch.current;
    try {
      const ack=await call<{acknowledged:boolean}>('reminders.ack',{context,duringChat,query,taskId:task.taskId,occurrence:task.occurrence,expectedVersion:task.version});
      if(epoch.current!==owner)return;
      if(!ack.acknowledged)setError('Reminder changed; check its current task state.');
      showing.current=false;setTask(null);
    } catch(e) {if(epoch.current===owner)setError(`Reminder dismissal needs attention: ${String(e)}`);}
  }
  return <>{task && <p className="workspace-notice" role="status">Due reminder: {task.title}<button className="quiet" onClick={()=>void snooze()}>Snooze 10 minutes</button><button className="quiet" onClick={()=>void dismiss()}>Dismiss reminder</button></p>}{error && <p role="status">{error}<button className="quiet" onClick={()=>setError('')}>Dismiss</button></p>}</>;
}
