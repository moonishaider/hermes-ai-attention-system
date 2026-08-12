import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/window", () => ({ getCurrentWindow: () => ({ label: "main" }) }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn(async () => () => undefined) }));
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (command: string) => {
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
    return {};
  }),
}));

import App, { transcriptsMateriallyDisagree } from "./App";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
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
});
