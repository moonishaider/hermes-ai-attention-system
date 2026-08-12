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
      recentLedger: [], commitments: [], recentDecisions: [], actionPreviews: [], learningItems: [],
      focusSessions: [], automationProposals: [], backgroundMode: "running",
    };
    if (command === "autostart_status") return false;
    return {};
  }),
}));

import App from "./App";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Jarvis desktop shell", () => {
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
});
