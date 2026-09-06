//! Owned signed Cua Driver lifecycle. Standard permissions only; no TCC changes.
use std::{fs,path::{Path,PathBuf},process::{Command,Stdio},thread,time::Duration};
use serde::Deserialize;
use sha2::{Digest,Sha256};
#[cfg(unix)] use std::os::unix::fs::MetadataExt;

#[derive(Deserialize)]
#[serde(rename_all="camelCase",deny_unknown_fields)]
struct Config { enabled:bool, app:PathBuf, socket:PathBuf, state_dir:PathBuf, binary_sha256:String }

pub(crate) struct CuaDriver { root:PathBuf,config:Config,pid:Option<u32> }
fn owned_regular_path(path:&Path,root:&Path)->Result<(),String>{
    if !path.starts_with(root) || path.components().any(|c|matches!(c,std::path::Component::ParentDir)){return Err("Driver path escapes owned runtime".into());}
    for p in path.ancestors(){
        if let Ok(meta)=fs::symlink_metadata(p){
            if meta.file_type().is_symlink(){return Err("Driver path cannot contain symbolic links".into());}
            if p.starts_with(root) && meta.uid()!=unsafe{libc::geteuid()}{return Err("Driver path is not owner-controlled".into());}
        }
    }
    Ok(())
}
fn bounded(command:&mut Command,seconds:u64)->Result<(bool,String),String>{
    use std::io::Read;
    let mut child=command.stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn().map_err(|e|e.to_string())?;
    let stdout=child.stdout.take().ok_or("Driver stdout missing")?;
    let (sender,receiver)=std::sync::mpsc::channel();
    thread::spawn(move ||{let mut bytes=Vec::new();let result=stdout.take(65537).read_to_end(&mut bytes).map(|_|bytes);let _=sender.send(result);});
    let deadline=std::time::Instant::now()+Duration::from_secs(seconds);
    let status=loop{
        if let Some(status)=child.try_wait().map_err(|e|e.to_string())?{break status;}
        if std::time::Instant::now()>=deadline{let _=child.kill();let _=child.wait();return Err("Owned driver command timed out; no operation was retried".into());}
        thread::sleep(Duration::from_millis(25));
    };
    let bytes=receiver.recv_timeout(Duration::from_secs(1)).map_err(|_|"Driver output did not close")?.map_err(|e|e.to_string())?;
    if bytes.len()>65536{return Err("Driver status exceeded output bound".into());}
    Ok((status.success(),String::from_utf8_lossy(&bytes).into_owned()))
}
impl CuaDriver {
    pub fn load(root:&Path)->Result<Option<Self>,String>{
        let path=root.join("runtime-data/runtime-cua.json");
        if !path.exists(){return Ok(None);}
        owned_regular_path(&path,root)?;
        let meta=fs::metadata(&path).map_err(|e|e.to_string())?;
        if !meta.is_file() || meta.mode()&0o777!=0o600 || meta.len()>16384{return Err("Driver config must be a private regular file".into());}
        let config:Config=serde_json::from_slice(&fs::read(path).map_err(|e|e.to_string())?).map_err(|_|"Invalid private driver config")?;
        let owned=Self{root:root.into(),config,pid:None};owned.validate()?;Ok(Some(owned))
    }
    fn binary(&self)->PathBuf{self.config.app.join("Contents/MacOS/cua-driver")}
    fn validate(&self)->Result<(),String>{
        let marker=self.root.join(".hermes-ai-attention-project");owned_regular_path(&marker,&self.root)?;
        if !marker.is_file(){return Err("Marked owned runtime required".into());}
        let expected=self.root.join("computer-use/cua-driver-0.23.2/CuaDriver.app");
        if self.config.app!=expected || self.config.socket!=self.root.join("runtime-data/cua-driver.sock") || self.config.state_dir!=self.root.join("runtime-data/cua-driver-state"){return Err("Driver configuration is outside reviewed exact paths".into());}
        if self.config.socket.as_os_str().len()>103{return Err("Driver socket exceeds macOS path limit".into());}
        for path in [&self.config.app,&self.config.socket,&self.config.state_dir,&self.root.join("scripts/jarvis_cua_driver.py")]{owned_regular_path(path,&self.root)?;}
        let binary=self.binary();owned_regular_path(&binary,&self.root)?;
        let meta=fs::metadata(&binary).map_err(|_|"Signed driver binary unavailable")?;
        if !meta.is_file() || meta.mode()&0o111==0{return Err("Driver binary is not executable".into());}
        let hash=format!("{:x}",Sha256::digest(fs::read(binary).map_err(|e|e.to_string())?));
        if hash!=self.config.binary_sha256{return Err("Pinned driver binary changed".into());}
        Ok(())
    }
    pub fn enabled(&self)->bool{self.config.enabled}
    pub fn configure(&self,command:&mut Command)->Result<(),String>{
        self.validate()?;
        command.env("HERMES_CUA_DRIVER_CMD",self.root.join("scripts/jarvis_cua_driver.py"))
            .env("CUA_DRIVER_RS_TELEMETRY_ENABLED","0").env("CUA_DRIVER_RS_HOME",&self.config.state_dir)
            .env_remove("CUA_DRIVER_PERMISSION_MODE").env_remove("CUA_DRIVER_DANGEROUSLY_BYPASS_APPROVALS")
            .env_remove("CUA_DRIVER_EMBEDDED");
        Ok(())
    }
    fn command(&self)->Command{
        let mut command=Command::new(self.binary());
        command.env_clear().env("PATH","/usr/bin:/bin:/usr/sbin:/sbin").env("HOME",std::env::var_os("HOME").unwrap_or_default());
        command.env("CUA_DRIVER_RS_TELEMETRY_ENABLED","0").env("CUA_DRIVER_RS_HOME",&self.config.state_dir)
            .env_remove("CUA_DRIVER_PERMISSION_MODE").env_remove("CUA_DRIVER_DANGEROUSLY_BYPASS_APPROVALS")
            .env_remove("CUA_DRIVER_EMBEDDED").stdin(Stdio::null()).stderr(Stdio::null());command
    }
    fn verified_pid(&self)->Result<Option<u32>,String>{
        self.validate()?;
        let (success,text)=bounded(self.command().args(["status","--socket"]).arg(&self.config.socket),5)?;
        if !success{return Ok(None);}
        if !text.contains("permission mode: standard"){return Err("Existing driver is not in standard permission mode".into());}
        let pid=text.lines().find_map(|line|line.trim().strip_prefix("pid: ").and_then(|v|v.parse::<u32>().ok())).ok_or("Driver status lacks process identity")?;
        let (_,actual)=bounded(Command::new("/bin/ps").args(["-p",&pid.to_string(),"-o","comm="]),3)?;
        if actual.trim()!=self.binary().to_string_lossy(){return Err("Driver socket belongs to an unexpected process".into());}
        Ok(Some(pid))
    }
    pub fn start(&mut self)->Result<bool,String>{
        if !self.config.enabled{return Ok(false);}
        if let Some(pid)=self.verified_pid()?{self.pid=Some(pid);return Ok(true);}
        let (valid,_)=bounded(Command::new("/usr/bin/codesign").args(["--verify","--deep","--strict"]).arg(&self.config.app),10)?;
        if !valid{return Err("Driver app signature check failed".into());}
        fs::create_dir_all(&self.config.state_dir).map_err(|e|e.to_string())?;
        let (launched,_)=bounded(Command::new("/usr/bin/open").args(["-n","-g","--env","CUA_DRIVER_RS_TELEMETRY_ENABLED=0","--env","CUA_DRIVER_DANGEROUSLY_BYPASS_APPROVALS=0","--env","CUA_DRIVER_EMBEDDED=0","--env","CUA_DRIVER_PERMISSION_MODE=standard","--env"])
            .arg(format!("CUA_DRIVER_RS_HOME={}",self.config.state_dir.display())).arg(&self.config.app)
            .args(["--args","serve","--socket"]).arg(&self.config.socket)
            .args(["--permission-mode","standard"]),10)?;
        if !launched{return Err("Signed driver did not launch".into());}
        for _ in 0..3{if let Some(pid)=self.verified_pid()?{self.pid=Some(pid);return Ok(true);}thread::sleep(Duration::from_millis(250));}
        Err("Driver startup not confirmed; inspect its normal macOS permission gate".into())
    }
    pub fn stop(&mut self)->Result<(),String>{
        let Some(pid)=self.pid else{return Ok(());};
        if self.verified_pid()?!=Some(pid){return Err("Driver process changed; refusing to stop another process".into());}
        let (stopped,_)=bounded(self.command().args(["stop","--socket"]).arg(&self.config.socket),5)?;
        if !stopped{return Err("Owned driver stop was not confirmed".into());}
        self.pid=None;Ok(())
    }
}
#[cfg(test)]mod tests{
    use super::*;
    #[test]fn reject_parent_traversal_and_foreign_runtime(){let root=Path::new("/tmp/owned-runtime");assert!(owned_regular_path(Path::new("/tmp/owned-runtime/../other"),root).is_err());assert!(owned_regular_path(Path::new("/tmp/foreign"),root).is_err());}
    #[test]fn disabled_config_never_spawns(){let mut driver=CuaDriver{root:PathBuf::from("/absent"),config:Config{enabled:false,app:PathBuf::new(),socket:PathBuf::new(),state_dir:PathBuf::new(),binary_sha256:String::new()},pid:None};assert!(!driver.start().unwrap());driver.stop().unwrap();}
}
