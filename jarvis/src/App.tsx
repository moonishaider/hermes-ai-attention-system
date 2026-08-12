import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";
import type { ContextId, GuidedNavigationPlan, HealthStatus, JarvisState, RunEvent, RunStart } from "./types";

const NAV = ["Now", "Chat", "Work Ledger", "Projects", "Missions", "Radars", "Actions", "Learning", "Capability Studio", "Decisions", "Settings"];
const CONTEXTS: { id: ContextId; label: string }[] = [
  { id: "inside-success", label: "Inside Success" },
  { id: "mitchell", label: "Mitchell · dormant" },
  { id: "personal", label: "Personal" },
  { id: "mixed", label: "Mixed" },
  { id: "unknown", label: "Unknown" },
];

export function transcriptsMateriallyDisagree(live: string, final: string) {
  const words = (value: string) => value.toLowerCase().match(/[a-z0-9]+/g) ?? [];
  const liveWords = words(live);
  const finalWords = words(final);
  if (liveWords.length < 4 || finalWords.length < 4) return false;
  const left = new Set(liveWords);
  const right = new Set(finalWords);
  const shared = [...left].filter((word) => right.has(word)).length;
  const union = new Set([...left, ...right]).size;
  return union > 0 && shared / union < 0.45;
}

export function spokenProjection(value: string) {
  const plain = value
    .replace(/```[\s\S]*?```/g, "")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/[*#_`>|\[\]()]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const sentences = plain.match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? [];
  return sentences.slice(0, 2).map((sentence) => sentence.trim()).join(" ").slice(0, 420);
}

const fallbackHealth: HealthStatus = {
  state: "starting", hermesVersion: "0.20.0", backend: "Checking",
  context: "personal", modelRoute: "DeepSeek V4 Flash", budget: "Checking",
  writes: "Blocked", wakeListening: false, backgroundMode: "While Jarvis runs",
  message: "Starting the protected Hermes backend…",
};

function App() {
  const isHud = getCurrentWindow().label === "hud";
  const [health, setHealth] = useState<HealthStatus>(fallbackHealth);
  const [active, setActive] = useState("Now");
  const [context, setContext] = useState<ContextId>("personal");
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [progress, setProgress] = useState<string[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [background, setBackground] = useState("running");
  const [autostart, setAutostart] = useState(false);
  const [recording, setRecording] = useState(false);
  const [localState, setLocalState] = useState<JarvisState | null>(null);
  const [localTitle, setLocalTitle] = useState("");
  const [localDetails, setLocalDetails] = useState("");
  const [capabilityRequiresCode, setCapabilityRequiresCode] = useState(false);
  const [codexSpec, setCodexSpec] = useState<Record<string, unknown> | null>(null);
  const [localNotice, setLocalNotice] = useState("");
  const [commitmentTitle, setCommitmentTitle] = useState("");
  const [selectedCommitment, setSelectedCommitment] = useState<string | null>(null);
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [voiceRetryAvailable, setVoiceRetryAvailable] = useState(false);
  const [modelOverride, setModelOverride] = useState<"auto" | "routine" | "difficult" | "review">("auto");
  const [projection, setProjection] = useState<Record<string, unknown> | null>(null);
  const [navigationDestination, setNavigationDestination] = useState("personal-upwork");
  const [navigationQuery, setNavigationQuery] = useState("");
  const [navigationPlan, setNavigationPlan] = useState<GuidedNavigationPlan | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const lastRecordingRef = useRef<Blob | null>(null);
  const recognitionRef = useRef<{ start: () => void; stop: () => void } | null>(null);
  const liveTranscriptRef = useRef("");
  const runStartedRef = useRef(0);
  const routeRef = useRef("routine");
  const stageCostRef = useRef(0);
  const stageTokensRef = useRef(0);
  const voiceToggleRef = useRef<() => Promise<void>>(async () => undefined);
  const speakResponseRef = useRef(false);
  const voiceDeliveryIdRef = useRef<string | null>(null);

  useEffect(() => {
    const refreshHealth = () => invoke<HealthStatus>("system_status").then(setHealth).catch((error) => {
      setHealth({ ...fallbackHealth, state: "degraded", backend: "Unavailable", message: String(error) });
    });
    void refreshHealth();
    const healthTimer = window.setInterval(refreshHealth, 5000);
    invoke<boolean>("autostart_status").then(setAutostart).catch(() => undefined);
    const unlisten = listen<RunEvent>("jarvis-run-event", ({ payload }) => {
      if (payload.event === "message.delta" && payload.delta) setAnswer((old) => old + payload.delta);
      if (["governor.review_started", "governor.escalation_started"].includes(payload.event)) {
        setRunId(payload.run_id ?? null);
        routeRef.current = payload.route ?? "difficult";
        stageCostRef.current += payload.stage_cost_usd ?? 0;
        stageTokensRef.current += payload.stage_tokens ?? 0;
        setAnswer("");
        const label = payload.event === "governor.review_started" ? "Terra independent review" : "Pro escalation";
        setProgress((old) => [...old, `${label} · ${payload.reason ?? "governed second pass"}`]);
      }
      if (payload.event === "run.completed" && payload.output) {
        setAnswer(payload.output);
        const latency = runStartedRef.current ? Date.now() - runStartedRef.current : 0;
        const input = payload.usage?.input_tokens ?? 0;
        const output = payload.usage?.output_tokens ?? 0;
        const rates = routeRef.current === "review" ? [2, 12] : routeRef.current === "difficult" ? [0.435, 0.87] : [0.14, 0.28];
        const cost = stageCostRef.current + (input * rates[0] + output * rates[1]) / 1_000_000;
        const tokens = stageTokensRef.current + input + output;
        setProgress((old) => [...old, `Completed · ${(latency / 1000).toFixed(1)}s · ${tokens} tokens · ~$${cost.toFixed(4)}`]);
        if (speakResponseRef.current && "speechSynthesis" in window) {
          window.speechSynthesis.cancel();
          const spoken = spokenProjection(payload.output);
          const utterance = new SpeechSynthesisUtterance(spoken || "The full result is ready on screen.");
          const ryan = window.speechSynthesis.getVoices().find((voice) => voice.name.toLowerCase().includes("ryan"));
          if (ryan) utterance.voice = ryan;
          utterance.rate = 1.08;
          window.speechSynthesis.speak(utterance);
        }
        speakResponseRef.current = false;
      }
      if (payload.event === "tool.started") setProgress((old) => [...old, `Checking ${payload.tool || payload.name || "source"}…`]);
      if (payload.event === "tool.completed") setProgress((old) => [...old, `Completed ${payload.tool || payload.name || "source"}`]);
      if (["run.completed", "run.failed", "run.cancelled"].includes(payload.event)) {
        setBusy(false); setRunId(null);
      }
      if (payload.error) setProgress((old) => [...old, `Unavailable: ${payload.error}`]);
    });
    const unlistenVoice = listen("jarvis-voice-requested", () => { void voiceToggleRef.current(); });
    return () => {
      window.clearInterval(healthTimer);
      unlisten.then((fn) => fn());
      unlistenVoice.then((fn) => fn());
    };
  }, []);

  useEffect(() => {
    // A context switch is a hard visual boundary. Never leave an answer,
    // projection, transcript, draft, or navigation preview from the previous
    // context on screen while the newly scoped state loads.
    setAnswer("");
    setProgress([]);
    setProjection(null);
    setNavigationPlan(null);
    setVoiceTranscript("");
    setPrompt("");
    setLocalNotice("");
    invoke<JarvisState>("jarvis_state", { context }).then((value) => {
      setLocalState(value); setBackground(value.backgroundMode || "running");
    }).catch(() => setLocalState(null));
  }, [context]);

  useEffect(() => {
    const current = localState?.focusSessions?.find((item) => !item.stopped_at);
    if (!current) return;
    const sample = async () => {
      await invoke("observe_frontmost", { focusId: current.focus_id, context }).catch(() => undefined);
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    };
    const timer = window.setInterval(() => void sample(), 45_000);
    return () => window.clearInterval(timer);
  }, [context, localState?.focusSessions?.map((item) => `${item.focus_id}:${item.stopped_at ?? "active"}`).join("|")]);

  const contextLabel = useMemo(() => CONTEXTS.find((item) => item.id === context)?.label ?? context, [context]);

  async function startPrompt(text: string, speakResponse = false, deliveryId?: string): Promise<boolean> {
    if (!text.trim() || busy) return false;
    setBusy(true); setAnswer("");
    setProgress([`Acknowledged · ${contextLabel}`, "Preparing the smallest relevant source plan…"]);
    stageCostRef.current = 0; stageTokensRef.current = 0;
    speakResponseRef.current = speakResponse;
    if (speakResponse && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const acknowledgement = new SpeechSynthesisUtterance("I'm checking that now.");
      acknowledgement.rate = 1.08;
      window.speechSynthesis.speak(acknowledgement);
    }
    try {
      const started = await invoke<RunStart>("start_run", {
        request: { prompt: text.trim(), context, overrideRoute: modelOverride, deliveryId },
      });
      setRunId(started.runId);
      runStartedRef.current = Date.now();
      routeRef.current = started.route;
      setProgress((old) => [...old, `Route: ${started.route} · ${started.reason}`]);
      setPrompt("");
      return true;
    } catch (error) {
      setProgress((old) => [...old, `Could not start: ${String(error)}`]);
      setBusy(false);
      return false;
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    await startPrompt(prompt);
  }

  async function cancel() {
    if (runId) await invoke("stop_run", { runId }).catch(() => undefined);
    setBusy(false); setRunId(null);
  }

  function stopSpeaking() {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }

  async function transcribeBlob(blob: Blob) {
    setProgress(["Transcribing the complete recording…"]);
    setVoiceRetryAvailable(false);
    try {
      const audio = Array.from(new Uint8Array(await blob.arrayBuffer()));
      const result = await invoke<{ transcript?: string; provider?: string }>("transcribe_audio", { audio, mimeType: blob.type || "audio/webm" });
      if (result.transcript?.trim()) {
        const transcript = result.transcript.trim();
        setVoiceTranscript(transcript);
        const liveTranscript = liveTranscriptRef.current.trim();
        if (transcriptsMateriallyDisagree(liveTranscript, transcript)) {
          setPrompt(transcript);
          setProgress([
            "The live and final transcripts disagree, so Jarvis did not submit anything.",
            "Review the transcript in the composer, then choose Ask Jarvis, Retry transcription, or Discard.",
          ]);
          setVoiceRetryAvailable(true);
          return;
        }
        if (!voiceDeliveryIdRef.current) voiceDeliveryIdRef.current = crypto.randomUUID();
        const delivered = await startPrompt(transcript, true, voiceDeliveryIdRef.current);
        if (delivered) {
          lastRecordingRef.current = null;
          voiceDeliveryIdRef.current = null;
          setVoiceRetryAvailable(false);
        } else {
          setProgress((old) => [...old, "The recording is retained only in memory so you can retry, edit, or discard it."]);
          setVoiceRetryAvailable(true);
        }
      } else {
        setProgress(["I did not detect a complete request. Nothing was submitted."]);
        setVoiceRetryAvailable(true);
      }
    } catch (error) {
      setProgress([`Voice transcription failed safely: ${String(error)}`]);
      setVoiceRetryAvailable(true);
    }
  }

  async function toggleVoice() {
    if (recording && recorderRef.current) {
      recognitionRef.current?.stop();
      recorderRef.current.stop();
      setRecording(false);
      return;
    }
    stopSpeaking();
    if (busy) await cancel();
    setActive("Chat");
    try {
      let permission = await invoke<string>("request_microphone_access");
      if (permission === "prompted") {
        setProgress(["Waiting for macOS microphone permission…"]);
        const deadline = Date.now() + 60_000;
        while (permission === "prompted" && Date.now() < deadline) {
          await new Promise((resolve) => window.setTimeout(resolve, 250));
          permission = await invoke<string>("request_microphone_access");
        }
      }
      if (permission !== "authorized") {
        const detail = permission === "denied"
          ? "Microphone access is off for Jarvis in System Settings"
          : permission === "restricted"
            ? "Microphone access is restricted by macOS"
            : "Microphone permission was not completed";
        throw new Error(detail);
      }
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
        throw new Error("this packaged WebView does not expose microphone capture");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
      const recorder = new MediaRecorder(stream);
      streamRef.current = stream;
      recorderRef.current = recorder;
      chunksRef.current = [];
      voiceDeliveryIdRef.current = crypto.randomUUID();
      liveTranscriptRef.current = "";
      setVoiceTranscript("");
      const Recognition = (window as unknown as { webkitSpeechRecognition?: new () => {
        continuous: boolean; interimResults: boolean; lang: string;
        onresult: ((event: { results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }> }) => void) | null;
        start: () => void; stop: () => void;
      } }).webkitSpeechRecognition;
      if (Recognition) {
        const recognition = new Recognition();
        recognition.continuous = true; recognition.interimResults = true; recognition.lang = "en-US";
        recognition.onresult = (event) => {
          const text = Array.from(event.results).map((result) => result[0]?.transcript ?? "").join(" ").trim();
          if (text) {
            liveTranscriptRef.current = text;
            setVoiceTranscript(text);
          }
        };
        recognitionRef.current = recognition;
        try { recognition.start(); } catch { recognitionRef.current = null; }
      }
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        lastRecordingRef.current = blob;
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        recognitionRef.current = null;
        await transcribeBlob(blob);
      };
      // Timesliced capture avoids relying on one final WebKit buffer for a
      // long dictated request. Chunks remain memory-only.
      recorder.start(500);
      setRecording(true);
      setProgress(["Listening until you press Stop…"]);
    } catch (error) {
      setRecording(false);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setProgress([`Talk could not start: ${String(error)}. Nothing was recorded or submitted.`]);
    }
  }

  voiceToggleRef.current = toggleVoice;

  function editVoiceTranscript() {
    if (!voiceTranscript.trim()) return;
    setPrompt(voiceTranscript.trim());
    setProgress(["Transcript moved to the composer. Edit it, then choose Ask Jarvis."]);
  }

  function discardVoiceRecording() {
    lastRecordingRef.current = null;
    voiceDeliveryIdRef.current = null;
    chunksRef.current = [];
    liveTranscriptRef.current = "";
    setVoiceTranscript("");
    setVoiceRetryAvailable(false);
    setProgress(["Recording and transcript discarded. Nothing else was submitted."]);
  }

  async function lookAtArea() {
    setActive("Chat");
    setProgress(["Choose exactly one window or region. Pixels will not be retained…"]);
    setAnswer("");
    try {
      const result = await invoke<{ answer: string }>("look_at_selected_area", {
        prompt: "Explain the selected area", context,
      });
      setAnswer(result.answer);
      setProgress(["Selected area understood with GPT-5.6 Luna · pixels discarded"]);
    } catch (error) {
      const message = String(error);
      setProgress([
        message.includes("adapter returned no valid result") || message.includes("capture cancelled")
          ? "Screen selection was cancelled or no region was chosen. Nothing was captured or retained."
          : `Screen understanding stopped safely: ${message}`,
      ]);
    }
  }

  async function toggleAutostart() {
    const next = !autostart;
    await invoke("set_autostart", { enabled: next });
    setAutostart(next);
  }

  async function setBackgroundMode(mode: "off" | "running" | "login") {
    await invoke("local_control", { operation: "setting", request: { mode } });
    setBackground(mode);
    if (mode === "login" && !autostart) await toggleAutostart();
  }

  async function buildCalendarProfile() {
    setLocalNotice("Reading a bounded year of personal Calendar style metadata…");
    try {
      await invoke("local_control", { operation: "calendar-profile", request: {} });
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
      setLocalNotice("Calendar style profile is ready for your review. No event was changed.");
    } catch (error) {
      setLocalNotice(`Calendar style profile unavailable: ${String(error)}`);
    }
  }

  async function reviewCalendarProfile() {
    const profileId = localState?.calendarStyle?.profile_id;
    if (!profileId) return;
    await invoke("local_control", {
      operation: "review-calendar-profile", request: { profileId },
    });
    setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    setLocalNotice("Calendar style profile marked owner-reviewed. No calendar event was changed.");
  }

  async function startFocus(minutes: 30 | 60 | 120) {
    if (["mixed", "unknown"].includes(context)) {
      setLocalNotice("Choose one explicit context before starting awareness."); return;
    }
    setLocalNotice("Starting a visible metadata-only focus session…");
    const started = await invoke<{ focusId: string }>("local_control", { operation: "focus", request: { context, minutes } });
    await invoke("observe_frontmost", { focusId: started.focusId, context }).catch(() => undefined);
    setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    setLocalNotice(`Focus session active for ${minutes} minutes · no screenshot retained`);
  }

  async function loadProjection(mode: "start-of-day" | "end-of-day" | "pre-meeting" | "absence-return") {
    setLocalNotice("Building a bounded ledger projection…");
    try {
      const result = await invoke<{ projection: Record<string, unknown> }>("local_control", {
        operation: "projection", request: { context, mode },
      });
      setProjection(result.projection);
      setLocalNotice("Ready from the local Work Ledger. Nothing was sent.");
    } catch (error) {
      setLocalNotice(`Projection unavailable: ${String(error)}`);
    }
  }

  async function capabilityControl(capabilityId: string, action: "useful" | "not-useful" | "draft" | "disabled" | "archived") {
    await invoke("local_control", { operation: "capability-control", request: { capabilityId, action } });
    setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    setLocalNotice(`Capability ${action} recorded locally.`);
  }

  async function recordAutomationOutcome(proposalId: string, outcome: "accepted" | "rejected" | "undone") {
    await invoke("local_control", { operation: "automation-outcome", request: { proposalId, outcome } });
    setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    setLocalNotice(`Automation proposal ${outcome}.`);
  }

  async function stopFocus(focusId: string) {
    await invoke("local_control", { operation: "stop-focus", request: { focusId } });
    setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    setLocalNotice("Focus session stopped.");
  }

  async function createLocal(kind: "mission" | "radar" | "capability") {
    if (!localTitle.trim() || !localDetails.trim()) return;
    setLocalNotice("Validating locally…");
    try {
      const result = await invoke<{ status: string; implementationSpec?: Record<string, unknown>; activationPerformed?: boolean }>("create_local_item", {
        request: {
          kind, context, title: localTitle.trim(), details: localDetails.trim(),
          sources: kind === "radar" ? ["public-web"] : [],
          tools: kind === "capability" ? ["search_evidence", "ledger_query"] : [],
          requiresCode: kind === "capability" && capabilityRequiresCode,
        },
      });
      if (result.status === "codex-spec-only" && result.implementationSpec) {
        setCodexSpec(result.implementationSpec);
        setLocalNotice("Codex-ready specification generated. Jarvis did not modify code, install, activate, or deploy anything.");
      } else {
        setCodexSpec(null);
        setLocalNotice(`${kind} saved locally · ${result.status}`);
      }
      setLocalTitle(""); setLocalDetails("");
      setCapabilityRequiresCode(false);
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    } catch (error) {
      setLocalNotice(`Not created: ${String(error)}`);
    }
  }

  async function openCommitment(evidenceId: string) {
    if (!commitmentTitle.trim()) { setLocalNotice("Enter the commitment exactly as you mean it first."); return; }
    try {
      await invoke("local_control", { operation: "commitment-open", request: { context, title: commitmentTitle.trim(), evidenceId } });
      setCommitmentTitle(""); setLocalNotice("Commitment opened locally with source evidence.");
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    } catch (error) { setLocalNotice(`Commitment not opened: ${String(error)}`); }
  }

  async function completeCommitment(evidenceId: string) {
    if (!selectedCommitment) return;
    try {
      await invoke("local_control", { operation: "commitment-complete", request: { taskId: selectedCommitment, evidenceId } });
      setSelectedCommitment(null); setLocalNotice("Commitment completion verified from same-context evidence.");
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    } catch (error) { setLocalNotice(`Completion not accepted: ${String(error)}`); }
  }

  async function previewNavigation() {
    try {
      const plan = await invoke<GuidedNavigationPlan>("guided_navigation_preview", {
        request: { destination: navigationDestination, context, query: navigationQuery },
      });
      setNavigationPlan(plan);
      setLocalNotice("Review the exact profile, account, domain, and read-only action. Nothing has opened yet.");
    } catch (error) {
      setNavigationPlan(null);
      setLocalNotice(`Navigation not staged: ${String(error)}`);
    }
  }

  async function openNavigation() {
    if (!navigationPlan) return;
    try {
      await invoke<GuidedNavigationPlan>("guided_navigation_open", {
        request: { destination: navigationPlan.destination, context: navigationPlan.context, query: navigationPlan.query },
      });
      setLocalNotice(`Opened ${navigationPlan.label} in ${navigationPlan.profile}. Jarvis did not type or submit anything.`);
      setNavigationPlan(null);
    } catch (error) {
      setLocalNotice(`Navigation stopped safely: ${String(error)}`);
    }
  }

  if (isHud) return <div className="hud-shell">
    <div className="hud-title"><span className="orb"/><span>Ask Jarvis</span><small>{contextLabel}</small></div>
    <form className="hud-composer" onSubmit={submit}>
      <input autoFocus value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="What needs your attention?"/>
      <button type="button" className={recording ? "danger" : "quiet"} onClick={() => void toggleVoice()}>{recording ? "Stop" : "Talk"}</button>
      <button type="submit">Ask</button>
    </form>
    {voiceTranscript && <div className="live-transcript">{voiceTranscript}</div>}
    {progress[0] && <div className="hud-status">{progress[0]}</div>}
  </div>;

  return <div className="shell">
    <aside>
      <div className="brand"><span className="orb"/><div><strong>JARVIS</strong><small>Hermes intelligence</small></div></div>
      <nav>{NAV.map((item) => <button key={item} className={active === item ? "active" : ""} onClick={() => setActive(item)}>{item}</button>)}</nav>
      <div className="sidebar-foot">
        <span className={`health-dot ${health.state}`}/><span>{health.state === "ready" ? "Systems nominal" : health.message}</span>
      </div>
    </aside>
    <main>
      <header>
        <div><p className="eyebrow">{active}</p><h1>{active === "Now" ? "Good evening, Syed." : active}</h1></div>
        <div className="header-actions"><button type="button" className={recording ? "danger" : "quiet"} onClick={() => void toggleVoice()}>{recording ? "Stop listening" : "Talk"}</button><select aria-label="Current context" value={context} onChange={(event) => setContext(event.target.value as ContextId)}>
          {CONTEXTS.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}
        </select></div>
      </header>

      {active === "Now" && <>
        <section className="hero card">
          <div><p className="eyebrow">Current attention</p><h2>Ready when you are.</h2><p>{health.message}</p></div>
          <div className="pulse"><span/><span/><span/></div>
        </section>
        <section className="grid">
          <article className="card"><p className="eyebrow">Today</p><h3>Attention brief</h3><p>Source-backed priorities, meetings, blockers, and people waiting—without mixing contexts.</p><button onClick={() => { setPrompt("Give me my source-backed attention brief for today."); setActive("Chat"); }}>Open brief</button></article>
          <article className="card"><p className="eyebrow">Projects</p><h3>Resume intelligently</h3><p>Continue from Codex, GitHub, decisions, tasks, and verified evidence.</p><button onClick={() => { setPrompt("Resume my most relevant active project with sources and next three actions."); setActive("Chat"); }}>Resume project</button></article>
          <article className="card"><p className="eyebrow">Awareness</p><h3>Look once</h3><p>Explicit selected-area understanding. No continuous capture or retained screenshot.</p><button onClick={lookAtArea}>Select area</button></article>
        </section>
        <section className="card intelligence-strip">
          <div><p className="eyebrow">Background intelligence</p><strong>{background === "off" ? "Off" : background === "login" ? "While logged in" : "While Jarvis runs"}</strong><small>{localState?.proactive?.source_count ?? 0} bounded ledger sources in the current brief</small></div>
          <div className="focus-controls"><button className="quiet" onClick={() => void loadProjection("start-of-day")}>Start day</button><button className="quiet" onClick={() => void loadProjection("pre-meeting")}>Pre-meeting</button><button className="quiet" onClick={() => void loadProjection("end-of-day")}>End day / DLOA</button><button className="quiet" onClick={() => void loadProjection("absence-return")}>Catch up</button><button className="quiet" onClick={() => void startFocus(30)}>Focus 30m</button><button className="quiet" onClick={() => void startFocus(60)}>60m</button>{localState?.focusSessions?.find((item) => !item.stopped_at) && <button className="danger" onClick={() => void stopFocus(localState.focusSessions.find((item) => !item.stopped_at)!.focus_id)}>Stop focus</button>}</div>
        </section>
        {projection && <section className="card surface"><p className="eyebrow">Ledger projection · local only</p><pre>{String((projection.dloa as { text?: string } | undefined)?.text ?? JSON.stringify(projection, null, 2))}</pre><button className="quiet" onClick={() => setProjection(null)}>Dismiss</button></section>}
        {localState?.focusSessions?.find((item) => !item.stopped_at) && <section className="card focus-timeline">
          <p className="eyebrow">Focus active · visible metadata only</p>
          <strong>{localState.focusSessions.find((item) => !item.stopped_at)?.observations?.[0]?.app_id ?? "Waiting for the first app sample"}</strong>
          <small>Profile/domain remain unknown unless proven; Jarvis never guesses. Screenshots retained: 0.</small>
        </section>}
        <section className="card state-strip"><strong>{localState?.ledgerCount ?? "—"}</strong><span>ledger entries in {contextLabel}</span><strong>{localState?.openTaskCount ?? "—"}</strong><span>open local tasks</span><strong>{localState?.budget?.level ?? "checking"}</strong><span>model budget</span></section>
      </>}

      {active === "Work Ledger" && <section className="card surface">
        <p className="eyebrow">Verified timeline</p><h2>{localState?.ledgerCount ?? 0} source-backed entries</h2>
        <p>One incremental ledger powers briefs, DLOA, commitments, projects, and catch-up. Context and actor labels stay visible.</p>
        <div className="setting"><input value={commitmentTitle} onChange={(event) => setCommitmentTitle(event.target.value)} placeholder="Exact commitment to track"/><span className="pill">Evidence required</span></div>
        {localState?.commitments?.map((item) => <article key={item.task_id}>
          <strong>{item.title}</strong><span>{item.status} · {item.evidence_ids.length} evidence link(s)</span>
          {item.status === "open" && <button className={selectedCommitment === item.task_id ? "danger" : "quiet"} onClick={() => setSelectedCommitment(selectedCommitment === item.task_id ? null : item.task_id)}>{selectedCommitment === item.task_id ? "Cancel completion" : "Select for completion proof"}</button>}
        </article>)}
        <div className="item-list">{localState?.recentLedger?.map((item) => <article key={item.entry_id}>
          <strong>{item.summary}</strong><span>{item.local_date} · {item.confidence_state}</span>
          <p>{item.kind} · actor {item.actor_state} · fresh {item.freshness_at.slice(0, 10)}</p>
          {item.evidence_ids[0] && (selectedCommitment
            ? <button className="quiet" onClick={() => void completeCommitment(item.evidence_ids[0])}>Use as completion proof</button>
            : <button className="quiet" onClick={() => void openCommitment(item.evidence_ids[0])}>Open commitment from this evidence</button>)}
        </article>)}</div>
        {localNotice && <small>{localNotice}</small>}
      </section>}

      {active === "Actions" && <section className="card surface">
        <p className="eyebrow">Action firewall</p><h2>External writes remain fail-closed</h2>
        <p>Company/client writes are unavailable. DLOA remains exact-preview only. Personal Calendar and Gmail draft execution are disabled until separately granted and accepted.</p>
        <span className="pill">Global kill switch on</span>
        <h3>Capability and permission matrix</h3>
        <div className="item-list permission-matrix">
          <article><strong>Personal Calendar</strong><span>Wrapper reviewed · execution disabled</span><p>Only the selected personal calendar can ever be targeted. Attendees, recurrence, ambiguity, or unusual reminders require an exact preview; no event is created during this build.</p></article>
          <article><strong>Personal Gmail drafts</strong><span>Create/update owned draft only · execution disabled</span><p>Draft sending is absent. Jarvis cannot call Gmail send endpoints, and can update only a draft it previously created after the capability is separately accepted.</p></article>
          <article><strong>Work Google accounts</strong><span>Read-only · write tools absent</span><p>Work Gmail and Calendar write capabilities are not registered. The interface cannot widen scopes or substitute the personal account.</p></article>
          <article><strong>Owner authorization</strong><span>Local exact intent required</span><p>Retrieved email, Slack, web, meeting, or document text is untrusted evidence and cannot approve an action. A changed target, permission snapshot, preview hash, or expired request fails closed.</p></article>
          <article><strong>Guided navigation</strong><span>Exact preview before opening</span><p>Fixed profile, account, domain, context, and read-only action are shown first. No arbitrary URL, typing, submission, download, settings change, or generic computer control exists.</p></article>
        </div>
        <div className="item-list">{localState?.actionPreviews?.map((item) => <article key={item.proposal_id}>
          <strong>{item.state}</strong><span>{item.updated_at.slice(0, 10)}</span><p>Preview hash {item.preview_hash.slice(0, 16)}… · not executed here</p>
        </article>)}</div>
      </section>}

      {active === "Learning" && <section className="card surface">
        <p className="eyebrow">Inspectable learning</p><h2>Memories, preferences, and workflow proposals</h2>
        <p>Learning is context-scoped and reversible. Security policy, credentials, permissions, and write destinations cannot be self-modified.</p>
        <div className="item-list">{localState?.learningItems?.length ? localState.learningItems.map((item) => <article key={item.memory_id}>
          <strong>{item.statement}</strong><span>{item.status} · {(item.confidence * 100).toFixed(0)}%</span><p>{item.namespace} · {item.created_at.slice(0, 10)}</p>
        </article>) : <p>No local learned item is stored in this context yet.</p>}</div>
      </section>}

      {active === "Chat" && <section className="chat-layout">
        <div className="conversation card">
          {progress.length > 0 && <div className="progress">{progress.map((line, index) => <div key={`${line}-${index}`}><span className={line.startsWith("Completed") ? "done" : "working"}/>{line}</div>)}</div>}
          {voiceTranscript && <div className="live-transcript"><small>Live transcript</small>{voiceTranscript}</div>}
          {answer ? <div className="answer">{answer}</div> : <div className="empty">Ask naturally. Jarvis will show what it checks and cite the result.</div>}
        </div>
        <form className="composer" onSubmit={submit}>
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="What needs your attention?" rows={2}/>
          <div><select aria-label="Model routing" value={modelOverride} onChange={(event) => setModelOverride(event.target.value as typeof modelOverride)}><option value="auto">Model · Auto</option><option value="routine">Flash</option><option value="difficult">Pro</option><option value="review">Pro + Terra review</option></select><button type="button" className={recording ? "danger" : "quiet"} onClick={() => void toggleVoice()}>{recording ? "Stop listening" : "Talk"}</button>{voiceRetryAvailable && lastRecordingRef.current && <button type="button" className="quiet" onClick={() => void transcribeBlob(lastRecordingRef.current!)}>Retry transcription</button>}{voiceRetryAvailable && voiceTranscript && <button type="button" className="quiet" onClick={editVoiceTranscript}>Edit transcript</button>}{voiceRetryAvailable && (voiceTranscript || lastRecordingRef.current) && <button type="button" className="quiet" onClick={discardVoiceRecording}>Discard</button>}<button type="button" className="quiet" onClick={stopSpeaking}>Stop speaking</button>{busy ? <button type="button" className="danger" onClick={cancel}>Cancel</button> : <button type="submit">Ask Jarvis</button>}</div>
        </form>
      </section>}

      {["Projects", "Missions", "Radars", "Capability Studio", "Decisions"].includes(active) && <section className="card surface">
        <p className="eyebrow">{active}</p><h2>{active === "Capability Studio" ? "Teach Jarvis a bounded capability" : `Your ${active.toLowerCase()}`}</h2>
        <p>{active === "Projects" && "Living objectives, verified progress, decisions, blockers, and the next three actions."}
          {active === "Missions" && "Persistent goals with completion contracts, evidence, questions, and review cadence."}
          {active === "Radars" && "Meaningful-change monitoring from approved sources—digest-first, never notification spam."}
          {active === "Capability Studio" && "Describe a workflow. Jarvis validates tools, context, permissions, dry-runs it, and cannot widen its own authority."}
          {active === "Decisions" && "Consequential choices, alternatives, reasons, evidence, and later outcomes."}</p>
        {active === "Projects" && <div className="item-list">{localState?.projects.length ? localState.projects.map((item) => <article key={item.project_id}><strong>{item.name}</strong><span>{item.phase} · {item.lifecycle}</span><p>{item.objective}</p></article>) : <p>No living project is stored in this context yet.</p>}</div>}
        {active === "Missions" && <div className="item-list">{localState?.missions.map((item) => <article key={item.mission_id}><strong>{item.goal}</strong><span>{item.status} · {item.lifecycle}</span><p>{item.completion_contract}</p></article>)}</div>}
        {active === "Radars" && <div className="item-list">{localState?.radars.map((item) => <article key={item.radar_id}><strong>{item.question}</strong><span>{item.cadence} · {item.notification_policy}</span></article>)}</div>}
        {active === "Capability Studio" && <div className="item-list">{localState?.capabilities.map((item) => <article key={item.capability_id}><strong>{item.name}</strong><span>{item.kind} · {item.status}</span><div className="focus-controls"><button className="quiet" onClick={() => void capabilityControl(item.capability_id, "useful")}>Useful · shadow</button><button className="quiet" onClick={() => void capabilityControl(item.capability_id, "not-useful")}>Not useful · disable</button>{item.status === "disabled" || item.status === "archived" ? <button className="quiet" onClick={() => void capabilityControl(item.capability_id, "draft")}>Restore draft</button> : <button className="quiet" onClick={() => void capabilityControl(item.capability_id, "disabled")}>Disable</button>}<button className="quiet" onClick={() => void capabilityControl(item.capability_id, "archived")}>Archive</button></div></article>)}</div>}
        {active === "Capability Studio" && localState?.automationProposals?.map((item) => <article className="automation-proposal" key={item.proposal_id}><strong>Automation opportunity: {item.signature}</strong><span>{item.status} · {item.occurrence_count} observations · ~{item.estimated_time_saved_minutes.toFixed(0)} minutes potential savings</span><div className="focus-controls"><button className="quiet" onClick={() => void recordAutomationOutcome(item.proposal_id, "accepted")}>Accept</button><button className="quiet" onClick={() => void recordAutomationOutcome(item.proposal_id, "rejected")}>Reject</button><button className="quiet" onClick={() => void recordAutomationOutcome(item.proposal_id, "undone")}>Undo</button></div></article>)}
        {["Missions", "Radars", "Capability Studio"].includes(active) && <div className="local-create">
          <input value={localTitle} onChange={(event) => setLocalTitle(event.target.value)} placeholder={active === "Missions" ? "Goal" : active === "Radars" ? "Question to watch" : "Capability name"}/>
          <textarea value={localDetails} onChange={(event) => setLocalDetails(event.target.value)} placeholder={active === "Missions" ? "What proves this is complete?" : active === "Radars" ? "What would count as a meaningful change?" : "Describe the low-risk workflow"}/>
          {active === "Capability Studio" && <label className="setting"><span>Requires new code or integration <small>Generate a Codex spec only; never self-modify or deploy</small></span><input aria-label="Requires new code or integration" type="checkbox" checked={capabilityRequiresCode} onChange={(event) => setCapabilityRequiresCode(event.target.checked)}/></label>}
          <button onClick={() => void createLocal(active === "Missions" ? "mission" : active === "Radars" ? "radar" : "capability")}>Validate and save locally</button>
          {active === "Capability Studio" && codexSpec && <article className="navigation-preview"><strong>Codex-ready implementation specification</strong><span>Context: {String(codexSpec.context_id)}</span><span>Requested tools: {Array.isArray(codexSpec.tools) ? codexSpec.tools.join(", ") : "none"}</span><span>No code change · no activation · no deployment</span><pre>{JSON.stringify(codexSpec, null, 2)}</pre></article>}
          {localNotice && <small>{localNotice}</small>}
        </div>}
        {active === "Decisions" && <button onClick={() => { setActive("Chat"); setPrompt("Show my recent evidence-backed decisions in this context."); }}>Review with Jarvis</button>}
      </section>}

      {active === "Settings" && <section className="settings-grid">
        <article className="card"><h3>Activation</h3><p><kbd>⌘</kbd><kbd>⇧</kbd><kbd>Space</kbd> opens Quick Entry.</p><p><kbd>⌃</kbd><kbd>⌥</kbd><kbd>Space</kbd> starts Talk to Jarvis.</p><div className="setting"><span>Wake phrase <small>Off by default · local only</small></span><button disabled>Off</button></div></article>
        <article className="card"><h3>Background intelligence</h3><div className="segmented"><button className={background === "off" ? "selected" : ""} onClick={() => void setBackgroundMode("off")}>Off</button><button className={background === "running" ? "selected" : ""} onClick={() => void setBackgroundMode("running")}>While running</button><button className={background === "login" ? "selected" : ""} onClick={() => void setBackgroundMode("login")}>While logged in</button></div><div className="setting"><span>Launch at login <small>Visible opt-in</small></span><button onClick={toggleAutostart}>{autostart ? "On" : "Off"}</button></div></article>
        <article className="card"><h3>Personal Calendar style</h3><p>{localState?.calendarStyle ? `${localState.calendarStyle.review_status} · updated ${localState.calendarStyle.updated_at.slice(0, 10)}` : "No bounded style profile has been generated yet."}</p><span className="pill">Existing personal calendar only</span>{localState?.calendarStyle && <dl><div><dt>Sample</dt><dd>{localState.calendarStyle.profile.sample_size} events</dd></div><div><dt>Typical timed event</dt><dd>{localState.calendarStyle.profile.median_timed_duration_minutes ?? "—"} min</dd></div><div><dt>All-day / recurring</dt><dd>{Math.round(localState.calendarStyle.profile.all_day_ratio * 100)}% / {Math.round(localState.calendarStyle.profile.recurrence_ratio * 100)}%</dd></div><div><dt>Meeting links</dt><dd>{Math.round(localState.calendarStyle.profile.meeting_link_ratio * 100)}%</dd></div></dl>}<div className="setting"><button onClick={() => void buildCalendarProfile()}>Build read-only profile</button>{localState?.calendarStyle?.review_status === "pending-owner-review" && <button className="quiet" onClick={() => void reviewCalendarProfile()}>Looks right</button>}</div>{localNotice && <small>{localNotice}</small>}</article>
        <article className="card"><h3>Safety</h3><p>Company/client writes unavailable. DLOA remains exact-preview only. Personal actions are capability-scoped.</p><span className="pill">External-action kill switch on</span></article>
        <article className="card"><h3>Guided navigation</h3><p>Open one reviewed page in the correct existing Chrome profile. No arbitrary URL, typing, submission, setting change, download, or computer control.</p><select aria-label="Reviewed destination" value={navigationDestination} onChange={(event) => { setNavigationDestination(event.target.value); setNavigationPlan(null); }}>
          <option value="personal-upwork">Personal · Upwork messages · Profile 1</option>
          <option value="personal-calendar">Personal · Calendar · Profile 1</option>
          <option value="personal-gmail">Personal · Gmail · Profile 1</option>
          <option value="mitchell-work">Mitchell · Upwork messages · Profile 1</option>
          <option value="inside-success-calendar">Inside Success · Calendar · Profile 2</option>
          <option value="inside-success-zoom">Inside Success · Zoom recordings · Profile 2</option>
          <option value="public-search">Personal · public search · Profile 1</option>
        </select>{navigationDestination === "public-search" && <input value={navigationQuery} onChange={(event) => { setNavigationQuery(event.target.value); setNavigationPlan(null); }} placeholder="Public search query"/>}<div className="setting"><button className="quiet" onClick={() => void previewNavigation()}>Preview exact navigation</button></div>{navigationPlan && <div className="navigation-preview"><strong>{navigationPlan.action} · {navigationPlan.label}</strong><span>{navigationPlan.profile} · {navigationPlan.account}</span><span>{navigationPlan.domain} · {navigationPlan.context}</span><span>No mutation</span><button onClick={() => void openNavigation()}>Open this exact page</button><button className="quiet" onClick={() => setNavigationPlan(null)}>Cancel</button></div>}{localNotice && <small>{localNotice}</small>}</article>
        <article className="card"><h3>Runtime</h3><dl><div><dt>Hermes</dt><dd>{health.hermesVersion}</dd></div><div><dt>Route</dt><dd>{health.modelRoute}</dd></div><div><dt>Budget</dt><dd>{health.budget}</dd></div></dl></article>
      </section>}
    </main>
  </div>;
}

export default App;
