import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mockState = vi.hoisted(() => ({ failRunStart: false, cancelScreen: false }));

vi.mock("@tauri-apps/api/window", () => ({ getCurrentWindow: () => ({ label: "main" }) }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn(async () => () => undefined) }));
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (command: string, args?: Record<string, unknown>) => {
    if (command === "system_status") return {
      state: "ready", hermesVersion: "0.20.0", backend: "Authenticated loopback",
      context: "personal", modelRoute: "DeepSeek V4 Flash · governed", budget: "Within monthly policy",
      writes: "Company/client writes blocked", wakeListening: false,
      backgroundMode: "While Jarvis runs", message: "Hermes is ready.",
    };
    if (command === "jarvis_state") return {
      ok: true, context: "personal", ledgerCount: 12, openTaskCount: 1,
      projects: [], missions: [], radars: [], capabilities: [],
      budget: { level: "ok", spent_usd: 0, hard_usd: 50 },
      integrations: {}, codexSync: { mode: "readonly", scheduled: false }, killSwitch: true,
      recentLedger: [{ entry_id: "ledger-1", kind: "work", occurred_at_utc: "2026-08-12T01:00:00Z", local_date: "2026-08-12", actor_state: "owner", summary: "Verified work", confidence_state: "confirmed", freshness_at: "2026-08-12T01:01:00Z", evidence_ids: ["evidence-1"] }],
      commitments: [{ task_id: "commitment-1", title: "Finish verified work", status: "open", evidence_ids: ["evidence-1"], confidence: 1, updated_at: "2026-08-12T01:02:00Z" }], recentDecisions: [], actionPreviews: [], learningItems: [],
      focusSessions: [], automationProposals: [], backgroundMode: "running",
    };
    if (command === "autostart_status") return false;
    if (command === "request_microphone_access") return "authorized";
    if (command === "transcribe_audio") return { transcript: "review my personal tasks", provider: "openai" };
    if (command === "look_at_selected_area") {
      if (mockState.cancelScreen) throw new Error("adapter returned no valid result");
      return { answer: "Harmless selected area" };
    }
    if (command === "create_local_item") {
      const request = args?.request as { requiresCode?: boolean; title?: string; details?: string };
      if (request?.requiresCode) return { status: "codex-spec-only", activationPerformed: false, implementationSpec: { kind: "workflow", context_id: "personal", name: request.title, description: request.details, tools: ["search_evidence", "ledger_query"], requires_code: true } };
      return { status: "draft", activationPerformed: false };
    }
    if (command === "local_control" && (args?.operation as string) === "projection") {
      const request = args?.request as { mode?: string };
      return { projection: { mode: request?.mode, bounded: true, connector_fanout_performed: false, context_id: "personal", source_count: 1 } };
    }
    if (command === "start_run") {
      if (mockState.failRunStart) throw new Error("synthetic backend unavailable");
      return { runId: "run-1", route: "routine", reason: "routine request" };
    }
    if (command === "guided_navigation_preview") return {
      destination: "personal-upwork", label: "Upwork", context: "personal",
      account: "Personal / Upwork", profile: "Profile 1", domain: "upwork.com",
      action: "open", query: "", mutation: false,
    };
    return {};
  }),
}));

import App, { spokenProjection, transcriptsMateriallyDisagree } from "./App";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  mockState.failRunStart = false;
  mockState.cancelScreen = false;
});

describe("Jarvis desktop shell", () => {
  it("stages materially conflicting transcripts for review", () => {
    expect(transcriptsMateriallyDisagree(
      "show my meetings for tomorrow morning",
      "send the report to everyone immediately",
    )).toBe(true);
    expect(transcriptsMateriallyDisagree(
      "show my meetings for tomorrow morning",
      "please show my meetings tomorrow morning",
    )).toBe(false);
  });

  it("speaks two natural sentences while leaving display detail untouched", () => {
    const displayed = "**Direct answer:** You have one meeting. It starts at 2 PM. Full evidence follows. https://example.com/source\n```private technical block```";
    const spoken = spokenProjection(displayed);
    expect(spoken).toBe("Direct answer: You have one meeting. It starts at 2 PM.");
    expect(spoken).not.toContain("https://");
    expect(spoken).not.toContain("technical block");
    expect(displayed).toContain("Full evidence follows");
  });

  it("shows protected daily-use surfaces and refreshed local state", async () => {
    render(<App />);
    expect(screen.getByText("JARVIS")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Capability Studio" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Work Ledger" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Actions" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Learning" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Talk" })).toBeTruthy();
    await waitFor(() => expect(screen.getByText("12")).toBeTruthy());
    expect(screen.getByText("ledger entries in Personal")).toBeTruthy();
    expect(screen.getByText("Systems nominal")).toBeTruthy();
  });

  it("makes absent and preview-only action authority visible", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Actions" }));
    expect(screen.getByText("Capability and permission matrix")).toBeTruthy();
    expect(screen.getByText("Create/update owned draft only · execution disabled")).toBeTruthy();
    expect(screen.getByText("Read-only · write tools absent")).toBeTruthy();
    expect(screen.getByText(/Retrieved email, Slack, web, meeting, or document text is untrusted evidence/)).toBeTruthy();
    expect(screen.getByText(/Exact preview before opening/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /send/i })).toBeNull();
  });

  it("keeps Talk reachable and reports capture failure instead of appearing inert", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Talk" }));
    await waitFor(() => expect(screen.getByText(/Talk could not start:/)).toBeTruthy());
    expect(screen.getByText(/Nothing was recorded or submitted/)).toBeTruthy();
  });

  it("shows evidence-bound commitment controls in the Work Ledger", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Work Ledger" }));
    await waitFor(() => expect(screen.getByText("Finish verified work")).toBeTruthy());
    expect(screen.getByText("Evidence required")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open commitment from this evidence" })).toBeTruthy();
  });

  it("requires an exact guided-navigation preview before opening", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    fireEvent.click(screen.getByRole("button", { name: "Preview exact navigation" }));
    await waitFor(() => expect(screen.getByText("Profile 1 · Personal / Upwork")).toBeTruthy());
    expect(screen.getByText("upwork.com · personal")).toBeTruthy();
    expect(screen.getByText("No mutation")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open this exact page" })).toBeTruthy();
  });

  it("explains a cancelled screen selection without adapter jargon", async () => {
    mockState.cancelScreen = true;
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Select area" }));
    await waitFor(() => expect(screen.getByText("Screen selection was cancelled or no region was chosen. Nothing was captured or retained.")).toBeTruthy());
    expect(screen.queryByText(/adapter returned/i)).toBeNull();
  });

  it("renders a code-requiring capability as a Codex spec without activation", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Capability Studio" }));
    fireEvent.change(screen.getByPlaceholderText("Capability name"), { target: { value: "Add a private local parser" } });
    fireEvent.change(screen.getByPlaceholderText("Describe the low-risk workflow"), { target: { value: "Build and test a new parser integration" } });
    fireEvent.click(screen.getByRole("checkbox", { name: "Requires new code or integration" }));
    fireEvent.click(screen.getByRole("button", { name: "Validate and save locally" }));
    await waitFor(() => expect(screen.getByText("Codex-ready implementation specification")).toBeTruthy());
    expect(screen.getByText("No code change · no activation · no deployment")).toBeTruthy();
    expect(screen.getByText(/Jarvis did not modify code/i)).toBeTruthy();
  });

  it("exposes all four bounded proactive projection modes", async () => {
    render(<App />);
    for (const name of ["Start day", "Pre-meeting", "End day / DLOA", "Catch up"]) {
      expect(screen.getByRole("button", { name })).toBeTruthy();
    }
    fireEvent.click(screen.getByRole("button", { name: "Pre-meeting" }));
    await waitFor(() => expect(screen.getByText(/"mode": "pre-meeting"/)).toBeTruthy());
    expect(screen.getByText(/"connector_fanout_performed": false/)).toBeTruthy();
  });

  it("clears context-scoped projections and drafts when context changes", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Pre-meeting" }));
    await waitFor(() => expect(screen.getByText(/"mode": "pre-meeting"/)).toBeTruthy());
    fireEvent.change(screen.getByRole("combobox", { name: "Current context" }), { target: { value: "mitchell" } });
    await waitFor(() => expect(screen.queryByText(/"mode": "pre-meeting"/)).toBeNull());
    expect((screen.getByRole("combobox", { name: "Current context" }) as HTMLSelectElement).value).toBe("mitchell");
  });

  it("retains failed dictation and exposes retry edit and discard", async () => {
    mockState.failRunStart = true;
    const stopTrack = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => ({ getTracks: () => [{ stop: stopTrack }] })) },
    });
    class SyntheticRecorder {
      mimeType = "audio/webm";
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      constructor(_stream: unknown) {}
      start(_timeslice: number) {}
      stop() {
        this.ondataavailable?.({ data: new Blob(["synthetic audio"], { type: this.mimeType }) });
        this.onstop?.();
      }
    }
    Object.defineProperty(globalThis, "MediaRecorder", { configurable: true, value: SyntheticRecorder });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Talk" }));
    await waitFor(() => expect(screen.getAllByRole("button", { name: "Stop listening" })).toHaveLength(2));
    fireEvent.click(screen.getAllByRole("button", { name: "Stop listening" })[1]);
    await waitFor(() => expect(screen.getByRole("button", { name: "Retry transcription" })).toBeTruthy());
    expect(screen.getByRole("button", { name: "Edit transcript" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Discard" })).toBeTruthy();
    expect(screen.getByText(/recording is retained only in memory/i)).toBeTruthy();
    expect(stopTrack).toHaveBeenCalledOnce();
  });
});
