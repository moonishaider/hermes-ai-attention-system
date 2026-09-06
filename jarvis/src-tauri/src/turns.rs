//! Native ownership for run events, cancellation, and window recovery.
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::HashMap;
use std::path::Path;

#[derive(Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct Turn {
    pub run_id: String,
    pub session_id: String,
    pub turn_id: String,
    pub context: String,
    pub route: String,
    pub reason: String,
    pub status: String,
    pub output: String,
    pub sequence: u64,
    pub provider_run_id: Option<String>,
    pub cancelled: bool,
    pub input_hash: String,
    #[serde(default)]
    pub terminal_pending: Option<Value>,
    #[serde(default)]
    pub stage_sessions: Vec<String>,
    #[serde(default)]
    pub native_nonce: String,
    #[serde(default)]
    pub owner_request: String,
    #[serde(default)]
    pub pending_action: Option<Value>,
    #[serde(default)]
    pub browser_selection_id: Option<String>,
    #[serde(default)]
    pub dispatch_pending: bool,
    #[serde(default)]
    pub dloa_manifest_id: Option<String>,
    #[serde(default)]
    pub action_receipt:Option<Value>,
    #[serde(default)]
    pub report_pending:Option<Value>,
    #[serde(default)]
    pub report_retry_from:Option<String>,
    #[serde(default)]
    pub report_retry_dispatched:bool,
}

impl Turn {
    pub fn report_setup_pending(&self)->bool {
        self.report_retry_from.is_some() && !self.report_retry_dispatched && !self.cancelled
            && matches!(self.status.as_str(),"queued"|"unresolved") && self.terminal_pending.is_none()
    }
    pub fn report_retry_eligible(&self)->bool {
        matches!(self.status.as_str(),"unresolved"|"failed"|"interrupted") && self.dloa_manifest_id.is_some()
            && self.terminal_pending.is_none() && self.pending_action.is_none() && self.action_receipt.is_none()
            && self.provider_run_id.is_none()
    }
    pub fn validate_report_retry_id(&self,new_id:&str)->Result<(),String>{
        if new_id==self.turn_id || new_id.is_empty() || new_id.len()>96 || !new_id.chars().all(|c|c.is_ascii_alphanumeric()||matches!(c,'-'|'_')) {
            return Err("Report retry requires a distinct valid new turn ID".into());
        }
        if !self.report_retry_eligible(){return Err("This run has no recoverable incomplete report".into());}
        Ok(())
    }
}

#[derive(Default)]
pub(crate) struct Turns { pub rows: HashMap<String, Turn> }

impl Turns {
    pub fn requires_retained_response(diagnosis:&Value)->bool {
        diagnosis.get("batches").and_then(Value::as_array).is_some_and(|batches|batches.iter().any(|b|b.get("localRevalidation").and_then(Value::as_bool)==Some(true)))
    }
    pub fn valid_local_revalidation(receipt:&Value,batch:&Value)->bool {
        let status_valid=if batch.get("recoveryKind").and_then(Value::as_str)==Some("known-invalid-received") {
            let valid=batch.get("validatedChunkCount").and_then(Value::as_u64);
            let remaining=batch.get("remainingChunkCount").and_then(Value::as_u64);
            let total=batch.get("chunkCount").and_then(Value::as_u64);
            receipt.get("status").and_then(Value::as_str)==Some("salvaged")
                && receipt.get("recoveryKind")==batch.get("recoveryKind")
                && matches!((valid,remaining,total),(Some(v),Some(r),Some(t)) if r>0 && v.checked_add(r)==Some(t))
                && ["validatedChunkCount","remainingChunkCount","chunkCount"].iter().all(|key|receipt.get(*key)==batch.get(*key))
        }else{receipt.get("status").and_then(Value::as_str)==Some("revalidated")};
        status_valid
            && receipt.get("modelCalled").and_then(Value::as_bool)==Some(false)
            && batch.get("batchId").and_then(Value::as_str).is_some()
            && batch.get("attemptDigest").and_then(Value::as_str).is_some()
            && receipt.get("batchId")==batch.get("batchId")
            && receipt.get("attemptDigest")==batch.get("attemptDigest")
    }
    pub fn valid_final_recovery(receipt:&Value,diagnosis:&Value,manifest:&str)->bool {
        receipt.get("status").and_then(Value::as_str)==Some("prepared")
            && receipt.get("finalOnly").and_then(Value::as_bool)==Some(true)
            && receipt.get("modelCalled").and_then(Value::as_bool)==Some(false)
            && receipt.get("manifestId").and_then(Value::as_str)==Some(manifest)
            && diagnosis.get("finalAttemptDigest").and_then(Value::as_str).is_some_and(|v|!v.is_empty())
            && receipt.get("finalAttemptDigest")==diagnosis.get("finalAttemptDigest")
    }
    pub fn verified_report_diagnosis(&self,source:&Turn,diagnosis:&Value)->bool {
        if !source.report_retry_eligible() || diagnosis.get("eligible").and_then(Value::as_bool)!=Some(true) {return false;}
        let Some(ids)=diagnosis.get("lineageTurnIds").and_then(Value::as_array) else{return false;};
        if ids.is_empty() || ids.len()>32 || ids[0].as_str()!=Some(source.turn_id.as_str()){return false;}
        let mut seen=std::collections::HashSet::new();let mut child:Option<&Turn>=None;
        for id in ids {
            let Some(id)=id.as_str() else{return false;};
            if !seen.insert(id){return false;}
            let Some(row)=self.rows.values().find(|r|r.session_id==source.session_id && r.turn_id==id) else{return false;};
            if row.dloa_manifest_id!=source.dloa_manifest_id || row.provider_run_id.is_some() || row.action_receipt.is_some(){return false;}
            if let Some(prior)=child {
                if !prior.report_retry_dispatched || prior.report_retry_from.as_deref()!=Some(row.run_id.as_str()){return false;}
            }
            child=Some(row);
        }
        child.is_some_and(|root|root.report_retry_from.is_none())
    }
    fn validate_path(path:&Path)->Result<(),String>{
        for ancestor in path.ancestors(){if ancestor.is_symlink(){return Err("Turn journal path cannot contain a symbolic link".into());}}
        Ok(())
    }
    pub fn load(path: &Path) -> Result<Self, String> {
        Self::validate_path(path)?;
        if !path.exists() { return Ok(Self::default()); }
        if path.is_symlink() { return Err("Turn journal cannot be a symbolic link".into()); }
        let bytes = std::fs::read(path).map_err(|_| "Unable to read the private turn journal")?;
        let rows = serde_json::from_slice(&bytes).map_err(|_| "Turn journal needs recovery; original preserved")?;
        Ok(Self { rows })
    }
    pub fn save(&self, path: &Path) -> Result<(), String> {
        use std::io::Write;
        #[cfg(unix)] use std::os::unix::fs::OpenOptionsExt;
        Self::validate_path(path)?;
        let bytes = serde_json::to_vec(&self.rows).map_err(|e| e.to_string())?;
        let mut random=[0u8;16];getrandom::fill(&mut random).map_err(|e|e.to_string())?;
        let suffix:String=random.iter().map(|v|format!("{v:02x}")).collect();
        let temporary = path.with_extension(format!("pending-{suffix}"));
        let mut file = std::fs::OpenOptions::new().create_new(true).write(true)
            .mode(0o600).open(&temporary).map_err(|e| e.to_string())?;
        file.write_all(&bytes).and_then(|()| file.sync_all()).map_err(|e| e.to_string())?;
        std::fs::rename(temporary, path).map_err(|e| e.to_string())?;
        std::fs::File::open(path.parent().ok_or("Turn journal parent is missing")?).and_then(|parent|parent.sync_all()).map_err(|e|e.to_string())
    }
    pub fn event(&mut self, root: &str, mut event: Value) -> Option<Value> {
        let row = self.rows.get_mut(root)?;
        let kind = event.get("event").and_then(Value::as_str).unwrap_or("").to_owned();
        if matches!(row.status.as_str(), "completed" | "cancelled" | "failed" | "interrupted") { return None; }
        if let Some(provider) = event.get("run_id").and_then(Value::as_str) {
            if provider != root { event["provider_run_id"] = json!(provider); }
        }
        if let Some(receipt)=event.get("actionReceipt"){row.action_receipt=Some(receipt.clone());}
        row.sequence += 1;
        event["run_id"] = json!(root);
        event["session_id"] = json!(row.session_id);
        event["turn_id"] = json!(row.turn_id);
        event["sequence"] = json!(row.sequence);
        if kind == "message.delta" {
            if let Some(delta) = event.get("delta").and_then(Value::as_str) { row.output.push_str(delta); }
        } else if kind.starts_with("governor.") { row.output.clear(); }
        else if let Some(status) = kind.strip_prefix("run.") {
            if matches!(status, "completed" | "cancelled" | "failed" | "interrupted") {
                row.status = status.into();
                row.pending_action=None;
                if row.terminal_pending.is_none() {row.owner_request.clear();row.native_nonce.clear();}
                if let Some(output) = event.get("output").and_then(Value::as_str) { row.output = output.into(); }
            }
        }
        Some(event)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn row(root: &str, session: &str) -> Turn { Turn { run_id: root.into(), session_id: session.into(), turn_id: format!("turn-{root}"), context: "unknown".into(), route:"routine".into(), reason:String::new(), status:"running".into(), output:String::new(), sequence:0, provider_run_id:None, cancelled:false, input_hash:String::new(), terminal_pending:None, stage_sessions:Vec::new(),native_nonce:String::new(),owner_request:String::new(),pending_action:None,browser_selection_id:None,dispatch_pending:false,dloa_manifest_id:None,action_receipt:None,report_pending:None,report_retry_from:None,report_retry_dispatched:false } }
    #[test] fn report_retry_requires_exact_failed_local_report_and_distinct_id() {
        let mut report=row("old","session");
        report.status="unresolved".into();report.dloa_manifest_id=Some("manifest".into());
        assert!(report.validate_report_retry_id("new-turn").is_ok());
        assert!(report.validate_report_retry_id(&report.turn_id).is_err());
        assert!(report.validate_report_retry_id("../invalid").is_err());
        for state in ["running","queued","waiting_action","completed","cancelled"] {
            report.status=state.into();assert!(!report.report_retry_eligible());
        }
        report.status="failed".into();report.provider_run_id=Some("unresolved-provider".into());assert!(!report.report_retry_eligible());
        report.provider_run_id=None;report.action_receipt=Some(json!({"status":"uncertain"}));assert!(!report.report_retry_eligible());
        report.action_receipt=None;report.terminal_pending=Some(json!({}));assert!(!report.report_retry_eligible());
    }
    #[test] fn resumed_audited_response_never_uses_incomplete_output_ack_path() {
        assert!(Turns::requires_retained_response(&json!({"eligible":true,"batches":[{"localRevalidation":true},{"eligible":true}]})));
        assert!(!Turns::requires_retained_response(&json!({"eligible":true,"batches":[{"eligible":true}]})));
    }
    #[test] fn local_revalidation_requires_exact_receipt_and_no_model_call() {
        let batch=json!({"batchId":"batch","attemptDigest":"digest"});
        let receipt=json!({"status":"revalidated","modelCalled":false,"batchId":"batch","attemptDigest":"digest"});
        assert!(Turns::valid_local_revalidation(&receipt,&batch));
        for (key,value) in [("modelCalled",json!(true)),("attemptDigest",json!("changed")),("batchId",json!("other")),("status",json!("uncertain"))] {
            let mut changed=receipt.clone();changed[key]=value;assert!(!Turns::valid_local_revalidation(&changed,&batch));
        }
    }
    #[test] fn final_recovery_requires_exact_local_final_only_receipt() {
        let diagnosis=json!({"finalAttemptDigest":"digest"});
        let receipt=json!({"status":"prepared","finalOnly":true,"modelCalled":false,"manifestId":"manifest","finalAttemptDigest":"digest"});
        assert!(Turns::valid_final_recovery(&receipt,&diagnosis,"manifest"));
        for (key,value) in [("status",json!("completed")),("finalOnly",json!(false)),("modelCalled",json!(true)),("manifestId",json!("changed")),("finalAttemptDigest",json!("changed"))] {
            let mut altered=receipt.clone();altered[key]=value;assert!(!Turns::valid_final_recovery(&altered,&diagnosis,"manifest"));
        }
        assert!(!Turns::valid_final_recovery(&receipt,&json!({}),"manifest"));
    }
    #[test] fn partial_salvage_requires_truthful_exact_counts() {
        let batch=json!({"batchId":"batch","attemptDigest":"digest","recoveryKind":"known-invalid-received","validatedChunkCount":6,"remainingChunkCount":2,"chunkCount":8});
        let mut receipt=batch.clone();receipt["status"]=json!("salvaged");receipt["modelCalled"]=json!(false);
        assert!(Turns::valid_local_revalidation(&receipt,&batch));
        for (key,value) in [("status",json!("revalidated")),("remainingChunkCount",json!(0)),("validatedChunkCount",json!(8)),("chunkCount",json!(9)),("modelCalled",json!(true)),("attemptDigest",json!("changed"))] {
            let mut changed=receipt.clone();changed[key]=value;assert!(!Turns::valid_local_revalidation(&changed,&batch));
        }
        let mut invalid=batch.clone();invalid["chunkCount"]=json!(9);
        receipt["chunkCount"]=json!(9);assert!(!Turns::valid_local_revalidation(&receipt,&invalid));
        let mut empty=batch.clone();empty["validatedChunkCount"]=json!(0);empty["remainingChunkCount"]=json!(8);
        let mut empty_receipt=empty.clone();empty_receipt["status"]=json!("salvaged");empty_receipt["modelCalled"]=json!(false);
        assert!(Turns::valid_local_revalidation(&empty_receipt,&empty));
    }
    #[test] fn report_diagnosis_requires_real_same_manifest_dispatched_ancestry() {
        let mut original=row("old","session");original.status="failed".into();original.dloa_manifest_id=Some("manifest".into());
        let mut child=row("child","session");child.status="unresolved".into();child.dloa_manifest_id=Some("manifest".into());child.report_retry_from=Some("old".into());child.report_retry_dispatched=true;
        let mut registry=Turns::default();registry.rows.insert("old".into(),original);registry.rows.insert("child".into(),child.clone());
        let proof=json!({"eligible":true,"lineageTurnIds":["turn-child","turn-old"]});
        assert!(registry.verified_report_diagnosis(&child,&proof));
        assert!(!registry.verified_report_diagnosis(&child,&json!({"eligible":true,"lineageTurnIds":["turn-child"]})));
        registry.rows.get_mut("child").unwrap().report_retry_dispatched=false;assert!(!registry.verified_report_diagnosis(&child,&proof));
        registry.rows.get_mut("child").unwrap().report_retry_dispatched=true;registry.rows.get_mut("old").unwrap().dloa_manifest_id=Some("different".into());assert!(!registry.verified_report_diagnosis(&child,&proof));
    }
    #[test] fn report_setup_can_resume_after_restart_but_not_dispatch_or_cancel() {
        let mut report=row("new","session");report.report_retry_from=Some("old".into());
        report.status="queued".into();assert!(report.report_setup_pending());
        report.status="unresolved".into();assert!(report.report_setup_pending());
        let restored:Turn=serde_json::from_value(serde_json::to_value(&report).unwrap()).unwrap();assert!(restored.report_setup_pending());
        report.report_retry_dispatched=true;assert!(!report.report_setup_pending());
        report.report_retry_dispatched=false;report.cancelled=true;assert!(!report.report_setup_pending());
        report.cancelled=false;report.status="failed".into();assert!(!report.report_setup_pending());
    }
    #[test] fn report_retry_dispatch_claim_and_origin_survive_roundtrip() {
        let mut report=row("new","session");report.report_retry_from=Some("old".into());report.report_retry_dispatched=true;
        let restored:Turn=serde_json::from_value(serde_json::to_value(&report).unwrap()).unwrap();
        assert_eq!(restored.report_retry_from.as_deref(),Some("old"));assert!(restored.report_retry_dispatched);
        let mut registry=Turns::default();registry.rows.insert("new".into(),restored);
        registry.event("new",json!({"event":"run.failed","output":"Incomplete"}));
        assert!(registry.rows["new"].report_retry_dispatched);assert_eq!(registry.rows["new"].report_retry_from.as_deref(),Some("old"));
    }
    #[test] fn late_events_never_change_another_turn_or_completed_output() {
        let mut registry=Turns::default(); registry.rows.insert("A".into(),row("A","session-A")); registry.rows.insert("B".into(),row("B","session-B"));
        let a=registry.event("A",json!({"event":"message.delta","run_id":"provider-a","delta":"alpha"})).unwrap();
        assert_eq!(a["session_id"],"session-A"); assert_eq!(a["run_id"],"A"); assert_eq!(a["sequence"],1);
        registry.event("B",json!({"event":"message.delta","delta":"beta"}));
        registry.event("A",json!({"event":"run.cancelled"}));
        assert!(registry.event("A",json!({"event":"message.delta","delta":"late"})).is_none());
        assert_eq!(registry.rows["A"].output,"alpha"); assert_eq!(registry.rows["B"].output,"beta");
    }
    #[test] fn review_child_retains_owner_and_resets_stage_output() {
        let mut registry=Turns::default(); registry.rows.insert("root".into(),row("root","owner"));
        registry.event("root",json!({"event":"message.delta","delta":"draft"}));
        let event=registry.event("root",json!({"event":"governor.review_started","run_id":"child"})).unwrap();
        assert_eq!(event["run_id"],"root"); assert_eq!(event["provider_run_id"],"child"); assert!(registry.rows["root"].output.is_empty());
    }
    #[test] fn durable_journal_roundtrip_preserves_unknown_dispatch_and_report_retry() {
        use std::os::unix::fs::PermissionsExt;
        let root=std::env::temp_dir().canonicalize().unwrap().join(format!("jarvis-journal-test-{}",std::process::id()));
        std::fs::create_dir(&root).unwrap();let path=root.join("turns.json");
        let mut registry=Turns::default();let mut turn=row("root","owner");
        turn.dispatch_pending=true;turn.native_nonce="private-nonce".into();turn.report_pending=Some(json!({"manifestId":"fixture"}));
        registry.rows.insert("root".into(),turn);registry.save(&path).unwrap();
        let loaded=Turns::load(&path).unwrap();assert!(loaded.rows["root"].dispatch_pending);
        assert_eq!(loaded.rows["root"].native_nonce,"private-nonce");assert!(loaded.rows["root"].report_pending.is_some());
        assert_eq!(std::fs::metadata(&path).unwrap().permissions().mode()&0o777,0o600);
        std::fs::write(&path,b"corrupt fixture").unwrap();assert!(Turns::load(&path).is_err());
        assert_eq!(std::fs::read(&path).unwrap(),b"corrupt fixture");
        std::fs::remove_file(path).unwrap();std::fs::remove_dir(root).unwrap();
    }
    #[test] fn journal_refuses_symlink_ancestors_without_touching_target() {
        let root=std::env::temp_dir().canonicalize().unwrap().join(format!("jarvis-journal-links-{}",std::process::id()));
        std::fs::create_dir(&root).unwrap();let target=root.join("target");std::fs::create_dir(&target).unwrap();
        let link=root.join("alias");std::os::unix::fs::symlink(&target,&link).unwrap();
        assert!(Turns::default().save(&link.join("turns.json")).is_err());assert!(Turns::load(&link.join("turns.json")).is_err());
        assert!(!target.join("turns.json").exists());std::fs::remove_file(link).unwrap();std::fs::remove_dir(target).unwrap();std::fs::remove_dir(root).unwrap();
    }
}
