//! Native owner file selection. The renderer receives document IDs, not a filesystem capability.
use crate::HermesAdapter;
use serde_json::{Value, json};
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

fn dispatch(adapter: &HermesAdapter, value: Value) -> Result<Value,String> {
    let bytes=serde_json::to_vec(&value).map_err(|e|e.to_string())?;
    adapter.run_python("jarvis_documents.py",&[],Some(&bytes))
}

#[tauri::command]
pub(crate) async fn attach_files(app: AppHandle, adapter: State<'_,HermesAdapter>, session_id: String, retention: Option<String>) -> Result<Value,String> {
    HermesAdapter::validate_jarvis_session_id(&session_id)?;
    let adapter=adapter.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let selected=app.dialog().file().add_filter("Documents and images",&["txt","md","pdf","png","jpg","jpeg","webp","csv","xlsx","docx"]).blocking_pick_files();
        let Some(paths)=selected else {return Ok(json!({"data":[]}));};
        if paths.len()>20 {return Err("Choose no more than 20 files at once".into());}
        let mut data=Vec::new(); let mut errors=Vec::new();
        for path in paths {
            let path=path.into_path().map_err(|_|"Only local files can be attached")?;
            let result=dispatch(&adapter,json!({"operation":"ingest_file","sessionId":session_id,"path":path,"retention":retention.as_deref().unwrap_or("conversation")}));
            match result {Ok(value)=>data.push(value),Err(error)=>errors.push(json!({"name":path.file_name().unwrap_or_default().to_string_lossy(),"error":error}))}
        }
        Ok(json!({"data":data,"errors":errors}))
    }).await.map_err(|e|e.to_string())?
}

#[tauri::command]
pub(crate) async fn attach_bytes(adapter: State<'_,HermesAdapter>, session_id:String, name:String, mime_type:String, bytes:Vec<u8>, retention:Option<String>) -> Result<Value,String> {
    HermesAdapter::validate_jarvis_session_id(&session_id)?;
    if bytes.len()>20*1024*1024 {return Err("File exceeds the 20 MiB attachment limit".into());}
    if name.len()>240 || name.contains('/') || name.contains('\\') {return Err("Invalid attachment name".into());}
    let adapter=adapter.inner().clone();
    tauri::async_runtime::spawn_blocking(move || dispatch(&adapter,json!({"operation":"ingest_bytes","sessionId":session_id,"name":name,"mimeType":mime_type,"bytes":bytes,"retention":retention.as_deref().unwrap_or("conversation")})).map(|v|json!({"data":[v]}))).await.map_err(|e|e.to_string())?
}

#[tauri::command]
pub(crate) async fn list_attachments(adapter:State<'_,HermesAdapter>,session_id:String)->Result<Value,String>{
    HermesAdapter::validate_jarvis_session_id(&session_id)?;
    let adapter=adapter.inner().clone();
    tauri::async_runtime::spawn_blocking(move ||dispatch(&adapter,json!({"operation":"list","sessionId":session_id}))).await.map_err(|e|e.to_string())?
}

#[tauri::command]
pub(crate) async fn attachment_control(adapter:State<'_,HermesAdapter>,id:String,action:String,session_id:String)->Result<Value,String>{
    if !matches!(action.as_str(),"forget"|"restore"|"retry"|"ocr") {return Err("Unsupported attachment operation".into());}
    HermesAdapter::validate_jarvis_session_id(&session_id)?;
    let adapter=adapter.inner().clone();
    tauri::async_runtime::spawn_blocking(move ||dispatch(&adapter,json!({"operation":action,"id":id,"sessionId":session_id}))).await.map_err(|e|e.to_string())?
}

#[tauri::command]
pub(crate) async fn artifact_control(app:AppHandle,adapter:State<'_,HermesAdapter>,id:String,action:String,session_id:String)->Result<Value,String>{
    if !matches!(action.as_str(),"open"|"reveal"|"save-as") {return Err("Unsupported artifact operation".into());}
    HermesAdapter::validate_jarvis_session_id(&session_id)?;
    let adapter=adapter.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let result=dispatch(&adapter,json!({"operation":"artifact_path","id":id,"sessionId":session_id}))?;
        let path=result.get("path").and_then(Value::as_str).ok_or("Generated artifact is unavailable")?;
        let source=std::path::PathBuf::from(path).canonicalize().map_err(|e|e.to_string())?;
        let workspace=adapter.inner.project_root.join("runtime-data/documents").canonicalize().map_err(|e|e.to_string())?;
        if !source.starts_with(workspace) || !source.is_file() {return Err("Artifact leaves the private workspace".into());}
        if action=="save-as" {
            let name=result.pointer("/attachment/display_name").and_then(Value::as_str).filter(|name|!name.is_empty() && !name.contains('/') && !name.contains('\\')).map(str::to_owned).unwrap_or_else(||source.file_name().unwrap_or_default().to_string_lossy().to_string());
            let Some(destination)=app.dialog().file().set_file_name(name).blocking_save_file() else {return Ok(json!({"cancelled":true}));};
            let destination=destination.into_path().map_err(|_|"Choose a local output location")?;
            // A native selection grants only this new destination, never its whole directory.
            let mut input=std::fs::File::open(&source).map_err(|e|e.to_string())?;
            let mut output=std::fs::OpenOptions::new().write(true).create_new(true).open(&destination).map_err(|_|"Choose a new filename; existing files are preserved")?;
            std::io::copy(&mut input,&mut output).map_err(|e|e.to_string())?;
        } else {
            let mut command=std::process::Command::new("/usr/bin/open");
            if action=="reveal" {command.arg("-R");}
            if !command.arg(&source).status().map_err(|e|e.to_string())?.success(){return Err("macOS could not open the artifact".into());}
        }
        Ok(json!({"ok":true,"action":action,"id":id}))
    }).await.map_err(|e|e.to_string())?
}
