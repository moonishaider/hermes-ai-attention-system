"""Declarative Capability Studio with permission intersection and protected fields."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from uuid import uuid4, uuid5, NAMESPACE_URL
from .domain import TaskRecord
from .work_ledger import WorkLedger
from .proactive import ProactiveChiefOfStaff

from .domain import stable_hash, utc_now
from .storage import Store


PROTECTED_KEYS = {
    "credentials", "oauth_scopes", "security_policy", "model_budget",
    "company_permissions", "client_permissions", "action_destination",
    "protected_code", "hermes_core", "filesystem_root", "browser_control",
}


@dataclass(frozen=True, slots=True)
class CapabilityValidation:
    allowed: bool
    reason: str
    requested_tools: tuple[str, ...]
    granted_tools: tuple[str, ...]
    requires_code: bool = False


class CapabilityStudio:
    KINDS = {"mission", "radar", "schedule", "skill", "report-template", "workflow"}

    def __init__(self, store: Store, approved_tools: set[str]) -> None:
        self.store = store
        self.approved_tools = approved_tools

    @staticmethod
    def _walk_keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {key for nested in value.values() for key in CapabilityStudio._walk_keys(nested)}
        if isinstance(value, list):
            return {key for nested in value for key in CapabilityStudio._walk_keys(nested)}
        return set()

    def validate(self, spec: dict[str, Any]) -> CapabilityValidation:
        kind = str(spec.get("kind", ""))
        if kind not in self.KINDS:
            return CapabilityValidation(False, "unsupported capability kind", (), ())
        protected = sorted(self._walk_keys(spec) & PROTECTED_KEYS)
        if protected:
            return CapabilityValidation(False, f"protected fields requested: {', '.join(protected)}", (), ())
        requested = tuple(sorted({str(tool) for tool in spec.get("tools", [])}))
        granted = tuple(tool for tool in requested if tool in self.approved_tools)
        if granted != requested:
            return CapabilityValidation(False, "requested tools exceed current permissions", requested, granted)
        requires_code = bool(spec.get("requires_code", False))
        return CapabilityValidation(
            True, "declarative specification is within current permissions",
            requested, granted, requires_code=requires_code,
        )

    def create(self, spec: dict[str, Any], *, permission_inventory: dict[str, Any]) -> dict[str, Any]:
        validation = self.validate(spec)
        if not validation.allowed:
            raise ValueError(validation.reason)
        if validation.requires_code:
            return {
                "status": "codex-spec-only",
                "implementation_spec": spec,
                "activation_performed": False,
            }
        capability_id = str(uuid4())
        now = utc_now()
        permission_hash = stable_hash(permission_inventory)
        spec_json = json.dumps(spec, sort_keys=True, separators=(",", ":"))
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO capabilities VALUES(?,?,?,?,?,?,?,?)",
                (capability_id, spec["kind"], spec["context_id"], "draft", spec_json,
                 permission_hash, now, now),
            )
            self.store.connection.execute(
                "INSERT INTO capability_revisions VALUES(?,?,?,?,?,?)",
                (str(uuid4()), capability_id, 1, spec_json, permission_hash, now),
            )
        return {"capability_id": capability_id, "status": "draft", "validation": validation}

    def dry_run(self, capability_id: str, *, current_permission_inventory: dict[str, Any], fixtures=None, inputs=None) -> dict[str, Any]:
        return self.run(capability_id, mode="dry", current_permission_inventory=current_permission_inventory,
                        fixtures=fixtures, inputs=inputs)

    def run(self, capability_id: str, *, mode: str, current_permission_inventory: dict[str, Any],
            fixtures=None, inputs=None, run_id=None, cancelled=None, spec_override=None) -> dict[str, Any]:
        """Execute typed steps; fixture and shadow results are explicitly labelled.

        spec_override is an internal scheduler frozen revision, never renderer input.
        Registered operations cannot send externally or execute arbitrary code.
        """
        ensure_schema(self.store.connection)
        if mode not in {"dry", "shadow", "active"}: raise ValueError("invalid execution mode")
        row=self.store.connection.execute("SELECT * FROM capabilities WHERE capability_id=?",(capability_id,)).fetchone()
        if not row: raise ValueError("unknown capability")
        if row["permission_hash"] != stable_hash(current_permission_inventory):
            raise PermissionError("permission inventory changed; re-review required")
        spec=spec_override or json.loads(row["spec_json"])
        validation=self.validate(spec)
        if not validation.allowed: raise PermissionError(validation.reason)
        run_id=run_id or str(uuid4()); now=utc_now(); outputs={}; fixtures=fixtures or {}; inputs=inputs or {}
        prior=self.store.connection.execute("SELECT * FROM workflow_executions WHERE run_id=?",(run_id,)).fetchone()
        if prior and (prior["spec_hash"] != stable_hash(spec) or prior["capability_id"] != capability_id or json.loads(prior["result_json"]).get("mode") != mode):
            raise PermissionError("run identity cannot be rebound to another workflow")
        if prior and prior["status"] in {"completed", "cancelled"}: return json.loads(prior["result_json"])
        if mode=="active" and row["status"]!="active" and not (spec_override and row["status"]=="draft"):
            raise PermissionError("capability is not active")
        result={"run_id":run_id,"mode":mode,"external_write":False,"status":"running","steps":[],
                "evidence_class":"fixture/simulation" if mode=="dry" else "local source execution"}
        with self.store.connection:
            self.store.connection.execute("INSERT OR IGNORE INTO workflow_executions VALUES(?,?,?,?,?,?,?)",
                (run_id,capability_id,stable_hash(spec),"running",json.dumps(result),now,now))
        try:
            steps=spec.get("steps",[])
            if not steps: raise ValueError("workflow has no executable steps; add inputs and operations")
            if len(steps)>30: raise ValueError("workflow exceeds 30-step bound")
            for step in steps:
                if cancelled and cancelled(): result["status"]="cancelled"; break
                sid=str(step["id"]); tool=str(step["tool"])
                if sid in outputs: raise ValueError("duplicate step id")
                if tool not in spec.get("tools",[]) or tool not in self.approved_tools: raise PermissionError("step tool is not granted")
                if tool not in READ_TOOLS|LOCAL_TOOLS: raise PermissionError("unregistered operation")
                if any(dep not in outputs for dep in step.get("depends_on",[])): raise ValueError("dependency is missing or out of order")
                args=_resolve(step.get("args",{}), outputs,inputs)
                context=spec["context_id"]
                if args.get("context_id",context)!=context: raise PermissionError("step cannot change workflow context")
                receipt=self.store.connection.execute("SELECT result_json FROM workflow_step_receipts WHERE run_id=? AND step_id=?",(run_id,sid)).fetchone()
                if receipt: output=json.loads(receipt[0])
                elif mode=="dry":
                    if tool in LOCAL_TOOLS: output={"preview":True,"operation":tool,"arguments":args}
                    else:
                        if sid not in fixtures: raise ValueError(f"missing fixture for {sid}")
                        output=fixtures[sid]
                        if isinstance(output,dict) and output.get("error"): raise RuntimeError(str(output["error"]))
                elif tool in LOCAL_TOOLS and mode=="shadow": output={"preview":True,"operation":tool,"arguments":args}
                else:
                    with self.store.connection:
                        output=self._execute(tool,args,context,run_id,sid)
                        self.store.connection.execute("INSERT OR IGNORE INTO workflow_step_receipts VALUES(?,?,?)",(run_id,sid,json.dumps(output)))
                outputs[sid]=output
                result["steps"].append({"id":sid,"tool":tool,"status":"completed","output":output})
                result["outputs"]=outputs
                with self.store.connection:
                    self.store.connection.execute("UPDATE workflow_executions SET result_json=?,updated_at=? WHERE run_id=?",(json.dumps(result),utc_now(),run_id))
            else: result["status"]="completed"
        except (ValueError,KeyError,TypeError,PermissionError,RuntimeError) as exc:
            result.update(status="failed",error=str(exc))
        with self.store.connection:
            self.store.connection.execute("UPDATE workflow_executions SET status=?,result_json=?,updated_at=? WHERE run_id=?",(result["status"],json.dumps(result),utc_now(),run_id))
            self.store.connection.execute("INSERT OR REPLACE INTO capability_runs VALUES(?,?,?,?,?,?,?)",(run_id,capability_id,"live" if mode=="active" else mode,result["status"],json.dumps(result),now,utc_now()))
        return result

    def _execute(self,tool,args,context,run_id,sid):
        if tool=="search_evidence": return self.store.search_evidence(str(args["query"]),context_id=context,limit=min(int(args.get("limit",10)),50))
        if tool=="ledger": return WorkLedger(self.store).query(context_id=context,local_date=args.get("local_date"),limit=min(int(args.get("limit",50)),100))
        if tool=="daily_brief": return ProactiveChiefOfStaff(WorkLedger(self.store)).daily_brief(context_id=context,local_date=args["local_date"])
        if tool=="list_tasks": return self.store.list_tasks(context_id=context)
        if tool=="create_task":
            task_id=str(uuid5(NAMESPACE_URL,run_id+":"+sid))
            self.store.upsert_task(TaskRecord(task_id=task_id,title=str(args["title"])[:1000],context_id=context,task_type="task",status="open",evidence_ids=tuple(args.get("evidence_ids",[]))))
            return {"task_id":task_id,"title":args["title"],"context_id":context}
        if tool=="save_output":
            artifact_id=str(uuid5(NAMESPACE_URL,run_id+":"+sid)); content=json.dumps(args.get("content"),ensure_ascii=False)
            if len(content)>500000: raise ValueError("output exceeds bounded local document size")
            self.store.connection.execute("INSERT OR IGNORE INTO workflow_outputs VALUES(?,?,?,?,?)",(artifact_id,run_id,str(args.get("title","Workflow output")),content,utc_now()))
            return {"artifact_id":artifact_id,"title":args.get("title","Workflow output"),"content":args.get("content")}
        raise ValueError("unsupported workflow operation")

    def revise(self, capability_id: str, spec: dict[str, Any], *, permission_inventory: dict[str, Any]):
        validation=self.validate(spec)
        if not validation.allowed or validation.requires_code: raise ValueError(validation.reason)
        row=self.store.connection.execute("SELECT * FROM capabilities WHERE capability_id=?",(capability_id,)).fetchone()
        if not row: raise ValueError("unknown capability")
        if spec.get("context_id")!=row["context_id"]: raise PermissionError("revision cannot silently change context")
        revision=self.store.connection.execute("SELECT COALESCE(MAX(revision),0)+1 FROM capability_revisions WHERE capability_id=?",(capability_id,)).fetchone()[0]
        encoded=json.dumps(spec,sort_keys=True);permission_hash=stable_hash(permission_inventory);now=utc_now()
        with self.store.connection:
            self.store.connection.execute("INSERT INTO capability_revisions VALUES(?,?,?,?,?,?)",(str(uuid4()),capability_id,revision,encoded,permission_hash,now))
            self.store.connection.execute("UPDATE capabilities SET spec_json=?,permission_hash=?,status='draft',updated_at=? WHERE capability_id=?",(encoded,permission_hash,now,capability_id))
        return {"capability_id":capability_id,"revision":revision,"status":"draft","scheduled_versions_unchanged":True}

    def set_status(self, capability_id: str, status: str) -> None:
        if status not in {"draft", "shadow", "active", "disabled", "archived"}:
            raise ValueError("invalid capability status")
        if status=="active":
            ensure_schema(self.store.connection)
            row=self.store.connection.execute("SELECT spec_json FROM capabilities WHERE capability_id=?",(capability_id,)).fetchone()
            if not row: raise ValueError("unknown capability")
            spec=json.loads(row[0])
            if spec.get("steps"):
                tested=self.store.connection.execute("SELECT 1 FROM workflow_executions WHERE capability_id=? AND spec_hash=? AND status='completed'",(capability_id,stable_hash(spec))).fetchone()
                if not tested: raise ValueError("execute this workflow revision successfully before activation")
        with self.store.connection:
            self.store.connection.execute(
                "UPDATE capabilities SET status=?,updated_at=? WHERE capability_id=?",
                (status, utc_now(), capability_id),
            )

    def record_feedback(
        self, *, capability_id: str, useful: bool, correction: str | None,
        evidence_ids: tuple[str, ...], provenance: dict[str, Any],
    ) -> str:
        row = self.store.connection.execute(
            "SELECT status FROM capabilities WHERE capability_id=?", (capability_id,)
        ).fetchone()
        if not row:
            raise ValueError("unknown capability")
        if correction and len(correction) > 1_000:
            raise ValueError("feedback correction is too large")
        feedback_id = str(uuid4())
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO behavior_feedback VALUES(?,?,?,?,?,?,?,?)",
                (feedback_id, "capability", capability_id, int(useful), correction,
                 json.dumps(sorted(evidence_ids)), json.dumps(provenance, sort_keys=True), utc_now()),
            )
            if useful and row["status"] in {"draft", "disabled"}:
                self.store.connection.execute(
                    "UPDATE capabilities SET status='shadow',updated_at=? WHERE capability_id=?",
                    (utc_now(), capability_id),
                )
            elif not useful and row["status"] != "archived":
                self.store.connection.execute(
                    "UPDATE capabilities SET status='disabled',updated_at=? WHERE capability_id=?",
                    (utc_now(), capability_id),
                )
        return feedback_id


READ_TOOLS={"search_evidence","ledger","daily_brief","list_tasks"}
LOCAL_TOOLS={"create_task","save_output"}

def _resolve(value,outputs,inputs):
    if isinstance(value,dict):
        if set(value)=={"from_step"}:
            return outputs[value["from_step"]]
        if set(value)=={"input"}: return inputs[value["input"]]
        return {k:_resolve(v,outputs,inputs) for k,v in value.items()}
    if isinstance(value,list): return [_resolve(v,outputs,inputs) for v in value]
    return value

def ensure_schema(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS workflow_executions(run_id TEXT PRIMARY KEY,capability_id TEXT NOT NULL,spec_hash TEXT NOT NULL,status TEXT NOT NULL,result_json TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS workflow_step_receipts(run_id TEXT NOT NULL,step_id TEXT NOT NULL,result_json TEXT NOT NULL,PRIMARY KEY(run_id,step_id));
    CREATE TABLE IF NOT EXISTS workflow_outputs(artifact_id TEXT PRIMARY KEY,run_id TEXT NOT NULL,title TEXT NOT NULL,content_json TEXT NOT NULL,created_at TEXT NOT NULL);
    """)
