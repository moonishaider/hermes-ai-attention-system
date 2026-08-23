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
  buildCommit?: string;
  runtimeMarker?: boolean;
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

export interface HermesSession {
  id: string;
  source: string;
  title?: string | null;
  preview?: string | null;
  message_count?: number;
  last_active?: number | string | null;
  started_at?: number | string | null;
  archived?: boolean | number;
  pinned?: boolean | number;
}

export interface HermesMessage {
  id: number | string;
  session_id: string;
  role: "user" | "assistant" | "tool" | "system";
  content?: string | null;
  timestamp?: number | string | null;
  tool_name?: string | null;
  display_kind?: string | null;
  display_metadata?: {
    jarvis_turn_id?: string;
    context?: string;
    route?: string;
    progress?: string[];
    review_harness_isolated?: boolean;
  } | null;
}

export interface GuidedNavigationPlan {
  destination: string;
  label: string;
  context: string;
  account: string;
  profile: string;
  domain: string;
  action: string;
  query: string;
  mutation: false;
}

export interface PersonalActionStatus {
  ok: boolean;
  connected: boolean;
  account: string;
  refreshable: boolean;
  exact_scopes: boolean;
  genericKillSwitch: true;
  personalCapabilitiesEnabled: boolean;
  mode: "off" | "preview" | "auto-explicit" | "earned-auto";
  seconds_remaining?: number;
  freshness?: "ready-refreshable" | "reauthorization-required";
  resources: Array<{ resource_id: string; capability_id: string; provider_id: string; state: string; updated_at: string; metadata?: Record<string, unknown> }>;
}

export interface PersonalActionPreview {
  ok: boolean;
  capabilityId: string;
  proposalId: string;
  previewHash: string;
  expiresAt: string;
  target: Record<string, string>;
  payload: Record<string, unknown>;
  conflicts?: Array<{ start: string; end: string; source_ref: string }>;
  calendarStyleApplied?: boolean;
  externalWritePerformed: false;
}

export interface GuidedReadResult {
  ok: boolean;
  queryHash: string;
  retrievedAt: string;
  mutation: false;
  policy: string;
  results: Array<{ title: string; url: string; excerpt: string; retrieved_at: string; injection_flags: string[]; content_hash: string }>;
}

export interface JarvisState {
  ok: boolean;
  context: ContextId;
  ledgerCount: number;
  openTaskCount: number;
  projects: Array<{ project_id: string; name: string; objective: string; completion_contract: string; phase: string; lifecycle: string; freshness_at?: string | null; latest_snapshot?: { snapshot_id: string; state: Record<string, unknown>; evidence_ids: string[]; created_at: string } | null; recent_progress: Array<{ entry_id: string; summary: string; local_date: string; confidence_state: string; freshness_at: string }>; decisions: Array<{ decision_id: string; decision: string; reasoning: string; decided_at: string; actual_outcome?: string | null }>; blockers: string[]; next_actions: string[]; resources: string[] }>;
  missions: Array<{ mission_id: string; goal: string; completion_contract: string; status: string; lifecycle: string }>;
  radars: Array<{ radar_id: string; question: string; cadence: string; notification_policy: string; lifecycle: string }>;
  capabilities: Array<{ capability_id: string; kind: string; status: string; name: string }>;
  budget: { level: string; spent_usd: number; hard_usd: number };
  modelRoutes: Array<{ id: string; provider: string; model: string; purpose: string; enabled: boolean }>;
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
  recentLedger: Array<{ entry_id: string; kind: string; occurred_at_utc: string; local_date: string; actor_state: string; summary: string; confidence_state: string; freshness_at: string; evidence_ids: string[]; evidence_sources: Array<{ evidence_id: string; source_system?: string | null; uri?: string | null }>; attention_state?: { status: string; updated_at: string; snoozed_until?: string | null } | null }>;
  commitments: Array<{ task_id: string; title: string; status: string; due_at?: string | null; evidence_ids: string[]; confidence: number; updated_at: string }>;
  inboxItems: Array<{ task_id: string; title: string; task_type: string; status: string; priority: number; owner: string; waiting_on?: string | null; due_at?: string | null; evidence_ids: string[]; confidence: number; updated_at: string }>;
  recentDecisions: Array<{ decision_id: string; decision: string; reasoning: string; decided_at: string; review_at?: string | null; actual_outcome?: string | null }>;
  actionPreviews: Array<{ proposal_id: string; preview_hash: string; state: string; updated_at: string }>;
  learningItems: Array<{ memory_id: string; statement: string; namespace: string; confidence: number; status: string; created_at: string }>;
  meetingEvidence: Array<{ evidence_id: string; title: string; confidence_state: string; indexed_at: string; source_timestamp?: string | null; uri?: string | null; account_id?: string | null; container?: string | null }>;
  backfillStats: Record<string, { count: number; first_indexed?: string | null; last_indexed?: string | null }>;
}
