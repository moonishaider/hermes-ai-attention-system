//! One default-off wake helper owned by this Jarvis process.
use serde_json::{json,Value};
use std::{collections::HashMap,io::{BufRead,BufReader,Write},path::PathBuf,process::{Child,ChildStdin,Command,Stdio},sync::{Arc,Mutex,mpsc,atomic::{AtomicBool,AtomicU64,Ordering}},thread,time::{Duration,SystemTime,UNIX_EPOCH}};
use tauri::{AppHandle,Emitter,Manager};

fn cache_status(listening:&AtomicBool,revision:&Mutex<u64>,value:&Value){
 let version=value.get("revision").and_then(Value::as_u64).unwrap_or(0);
 if let Ok(mut old)=revision.lock(){if version<*old{return;}*old=version;listening.store(value.get("state").and_then(Value::as_str)==Some("listening"),Ordering::SeqCst);}
}

type Pending=Arc<Mutex<HashMap<String,mpsc::Sender<Value>>>>;
struct Worker {child:Child,input:ChildStdin,pending:Pending,counter:u64}
impl Drop for Worker {fn drop(&mut self){let _=self.child.kill();let _=self.child.wait();}}

pub struct WakeManager {root:PathBuf,python:PathBuf,app:AppHandle,worker:Mutex<Option<Worker>>,listening:Arc<AtomicBool>,epoch:Arc<AtomicU64>,revision:Arc<Mutex<u64>>}
impl WakeManager {
 pub fn new(root:PathBuf,python:PathBuf,app:AppHandle)->Self {Self{root,python,app,worker:Mutex::new(None),listening:Arc::new(AtomicBool::new(false)),epoch:Arc::new(AtomicU64::new(0)),revision:Arc::new(Mutex::new(0))}}
 fn spawn(&self)->Result<Worker,String>{
  let mut child=Command::new(&self.python).arg(self.root.join("scripts/jarvis_wake.py")).current_dir(&self.root).env("PYTHONUNBUFFERED","1").env("HERMES_DISABLE_LAZY_INSTALLS","1").stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn().map_err(|e|format!("Optional wake helper unavailable: {e}"))?;
  let input=child.stdin.take().ok_or("Wake stdin unavailable")?;
  let output=child.stdout.take().ok_or("Wake stdout unavailable")?;
  let pending:Pending=Arc::new(Mutex::new(HashMap::new()));let replies=pending.clone();let app=self.app.clone();let listening=self.listening.clone();let epoch=self.epoch.clone();if let Ok(mut version)=self.revision.lock(){*version=0;}let revision=self.revision.clone();let identity=epoch.fetch_add(1,Ordering::SeqCst)+1;
  thread::spawn(move||{
   for line in BufReader::new(output).lines(){let Ok(line)=line else{break};let Ok(value)=serde_json::from_str::<Value>(&line) else{continue};
    if value.get("event").and_then(Value::as_str)==Some("wake.detected") {if epoch.load(Ordering::SeqCst)!=identity{continue;}cache_status(&listening,&revision,&json!({"state":"paused","revision":value.get("revision").and_then(Value::as_u64).unwrap_or(0)}));if let Some(main)=app.get_webview_window("main"){let _=main.emit("jarvis-wake",value);}continue;}
    if value.get("event").and_then(Value::as_str)==Some("wake.state") {if epoch.load(Ordering::SeqCst)==identity{if let Some(result)=value.get("result"){cache_status(&listening,&revision,result);}}continue;}
    if let Some(id)=value.get("id").and_then(Value::as_str){if let Ok(mut map)=replies.lock(){if let Some(sender)=map.remove(id){let _=sender.send(value);}}}
   }
   if epoch.load(Ordering::SeqCst)==identity{listening.store(false,Ordering::Relaxed);}
   if let Ok(mut map)=replies.lock(){map.clear();}
  });
  Ok(Worker{child,input,pending,counter:0})
 }
 /// Native caller must verify local main origin and microphone grant before owner_enabled=true.
 pub fn command(&self,operation:&str,owner_enabled:bool)->Result<Value,String>{
  if !matches!(operation,"status"|"start"|"pause"|"resume"|"stop"){return Err("Unknown wake operation".into());}
  if operation=="start"&&!owner_enabled{return Err("Enable wake explicitly in the local owner interface".into());}
  let mut slot=self.worker.lock().map_err(|_|"Wake lock unavailable")?;
  if operation=="stop"&&slot.is_none(){return Ok(json!({"state":"off","available":false,"microphone_checked":false}));}
  if slot.as_mut().is_some_and(|w|w.child.try_wait().ok().flatten().is_some()){slot.take();}
  if slot.is_none(){*slot=Some(self.spawn()?);}
  let worker=slot.as_mut().ok_or("Wake helper unavailable")?;worker.counter+=1;
  let id=format!("{}-{}",SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis(),worker.counter);
  let(tx,rx)=mpsc::channel();worker.pending.lock().map_err(|_|"Wake replies unavailable")?.insert(id.clone(),tx);
  let request=json!({"id":id,"operation":operation,"ownerEnabled":operation=="start"&&owner_enabled});
  if writeln!(worker.input,"{request}").and_then(|_|worker.input.flush()).is_err(){self.listening.store(false,Ordering::Relaxed);slot.take();return Err("Wake helper closed; listener stopped".into());}
  let result=rx.recv_timeout(Duration::from_secs(10));
  let value=match result{Ok(value)=>value,Err(_)=>{self.listening.store(false,Ordering::Relaxed);slot.take();return Err("Wake helper timed out; owned listener stopped".into());}};
  if operation=="stop"{slot.take();}
  if value.get("ok").and_then(Value::as_bool)!=Some(true){return Err(value.get("error").and_then(Value::as_str).unwrap_or("Wake operation failed").into());}
  let result=value.get("result").cloned().unwrap_or(Value::Null);
  cache_status(&self.listening,&self.revision,&result);
  Ok(result)
 }
 pub fn listening(&self)->bool{self.listening.load(Ordering::Relaxed)}
 pub fn shutdown(&self){self.listening.store(false,Ordering::Relaxed);if let Ok(mut slot)=self.worker.lock(){slot.take();}}
}

#[cfg(test)] mod wake_status_tests {use super::*;#[test] fn detector_failure_beats_stale_start_reply(){let active=AtomicBool::new(true);let revision=Mutex::new(1);cache_status(&active,&revision,&json!({"state":"off","revision":2}));cache_status(&active,&revision,&json!({"state":"listening","revision":1}));assert!(!active.load(Ordering::SeqCst));}}
