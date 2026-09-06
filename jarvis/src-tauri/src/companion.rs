//! Default-disabled private read companion worker; native owner commands only.
use serde_json::{json,Value};
use std::{collections::HashMap,io::{BufRead,BufReader,Write},path::PathBuf,process::{Child,ChildStdin,Command,Stdio},sync::{Arc,Mutex,mpsc},thread,time::Duration};
type Pending=Arc<Mutex<HashMap<String,mpsc::Sender<Value>>>>;
struct Worker{child:Child,input:ChildStdin,pending:Pending,counter:u64}
impl Drop for Worker{fn drop(&mut self){let _=self.child.kill();let _=self.child.wait();}}
pub struct CompanionManager{root:PathBuf,python:PathBuf,worker:Mutex<Option<Worker>>}
impl CompanionManager{
 pub fn new(root:PathBuf,python:PathBuf)->Self{Self{root,python,worker:Mutex::new(None)}}
 fn spawn(&self)->Result<Worker,String>{
  let mut child=Command::new(&self.python).arg(self.root.join("scripts/jarvis_companion.py")).current_dir(&self.root).env("PYTHONUNBUFFERED","1").stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn().map_err(|e|format!("Companion helper unavailable: {e}"))?;
  let input=child.stdin.take().ok_or("Companion input unavailable")?;let output=child.stdout.take().ok_or("Companion output unavailable")?;
  let pending:Pending=Arc::new(Mutex::new(HashMap::new()));let replies=pending.clone();
  thread::spawn(move||{for line in BufReader::new(output).lines(){let Ok(line)=line else{break};let Ok(value)=serde_json::from_str::<Value>(&line)else{continue};if let Some(id)=value.get("id").and_then(Value::as_str){if let Ok(mut map)=replies.lock(){if let Some(tx)=map.remove(id){let _=tx.send(value);}}}}if let Ok(mut map)=replies.lock(){map.clear();}});
  Ok(Worker{child,input,pending,counter:0})
 }
 /// Pair responses contain a secret: native caller displays locally, never logs or returns in URLs.
 pub fn command(&self,operation:&str,owner_authorized:bool)->Result<Value,String>{
  if !matches!(operation,"status"|"start"|"stop"|"pair"){return Err("Unknown companion operation".into());}
  if matches!(operation,"start"|"pair")&&!owner_authorized{return Err("Companion activation requires the local owner".into());}
  let mut slot=self.worker.lock().map_err(|_|"Companion lock unavailable")?;
  if operation=="stop"&&slot.is_none(){return Ok(json!({"state":"transport-blocked","listening":false}));}
  if slot.as_mut().is_some_and(|w|w.child.try_wait().ok().flatten().is_some()){slot.take();}
  if slot.is_none(){*slot=Some(self.spawn()?);}
  let worker=slot.as_mut().ok_or("Companion worker missing")?;worker.counter+=1;let id=worker.counter.to_string();let(tx,rx)=mpsc::channel();worker.pending.lock().map_err(|_|"Companion replies unavailable")?.insert(id.clone(),tx);
  let request=json!({"id":id,"operation":operation,"ownerAuthorized":owner_authorized});
  if writeln!(worker.input,"{request}").and_then(|_|worker.input.flush()).is_err(){slot.take();return Err("Companion worker stopped".into());}
  let value=match rx.recv_timeout(Duration::from_secs(25)){Ok(value)=>value,Err(_)=>{slot.take();return Err("Companion timed out; owned listener stopped".into());}};
  if operation=="stop"{slot.take();}
  if value.get("ok").and_then(Value::as_bool)!=Some(true){return Err(value.get("error").and_then(Value::as_str).unwrap_or("Companion operation failed").into());}
  Ok(value.get("result").cloned().unwrap_or(Value::Null))
 }
 pub fn shutdown(&self){if let Ok(mut slot)=self.worker.lock(){slot.take();}}
}
