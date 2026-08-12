export type ContextId = "inside-success" | "mitchell" | "personal" | "mixed" | "unknown";

export interface HealthStatus {
  state: "starting" | "ready" | "degraded" | "stopped";
  hermesVersion: string;
  backend: string;
  context: ContextId;
  modelRoute: string;
  budget: string;
  writes: string;
  wakeListening: boolean;
  backgroundMode: string;
  message: string;
}

export interface RunEvent {
  event: string;
  run_id?: string;
  delta?: string;
  output?: string;
  tool?: string;
  name?: string;
  status?: string;
  error?: string;
  route?: string;
  reason?: string;
  stage_cost_usd?: number;
  stage_tokens?: number;
  usage?: { input_tokens?: number; output_tokens?: number; total_tokens?: number };
  runtime?: { model?: string; provider?: string };
}

export interface RunStart { runId: string; route: string; reason: string; }

export interface JarvisState {
  ok: boolean;
  context: ContextId;
  ledgerCount: number;
  openTaskCount: number;
  projects: Array<{ project_id: string; name: string; objective: string; phase: string; lifecycle: string }>;
  missions: Array<{ mission_id: string; goal: string; completion_contract: string; status: string; lifecycle: string }>;
  radars: Array<{ radar_id: string; question: string; cadence: string; notification_policy: string; lifecycle: string }>;
  capabilities: Array<{ capability_id: string; kind: string; status: string; name: string }>;
  budget: { level: string; spent_usd: number; hard_usd: number };
  integrations: Record<string, string>;
  codexSync: { last_updated_at?: string | null; mode: string; scheduled: boolean };
  killSwitch: boolean;
  backgroundMode: "off" | "running" | "login";
  proactive?: {
    mode: string;
    source_count: number;
    freshness?: string | null;
    priorities?: unknown[];
    meetings?: unknown[];
    blockers?: unknown[];
  } | null;
  focusSessions: Array<{ focus_id: string; mode: string; started_at: string; expires_at: string; stopped_at?: string | null; observations?: Array<{ occurred_at: string; app_id: string; domain?: string | null; browser_profile?: string | null; context_id: string }> }>;
  automationProposals: Array<{ proposal_id: string; signature: string; status: string; occurrence_count: number; estimated_time_saved_minutes: number; false_alerts: number }>;
  calendarStyle?: {
    profile_id: string;
    review_status: string;
    updated_at: string;
    evidence_window: { start: string; end: string; sample_size: number };
    profile: {
      sample_size: number;
      median_timed_duration_minutes?: number | null;
      all_day_ratio: number;
      recurrence_ratio: number;
      location_ratio: number;
      meeting_link_ratio: number;
      title_capitalization: string;
      timezone_behavior: string;
    };
  } | null;
  recentLedger: Array<{ entry_id: string; kind: string; occurred_at_utc: string; local_date: string; actor_state: string; summary: string; confidence_state: string; freshness_at: string; evidence_ids: string[] }>;
  commitments: Array<{ task_id: string; title: string; status: string; due_at?: string | null; evidence_ids: string[]; confidence: number; updated_at: string }>;
  recentDecisions: Array<{ decision_id: string; decision: string; reasoning: string; decided_at: string; review_at?: string | null; actual_outcome?: string | null }>;
  actionPreviews: Array<{ proposal_id: string; preview_hash: string; state: string; updated_at: string }>;
  learningItems: Array<{ memory_id: string; statement: string; namespace: string; confidence: number; status: string; created_at: string }>;
}
