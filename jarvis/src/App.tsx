import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";
import type { ContextId, GuidedNavigationPlan, GuidedReadResult, HealthStatus, HermesMessage, HermesSession, JarvisState, PersonalActionPreview, PersonalActionStatus, RunEvent, RunStart } from "./types";

const EVERYDAY_NAV = ["Today", "Chat", "Inbox", "Projects", "Actions"];
const ADVANCED_NAV = ["Missions", "Radars", "Teach Jarvis", "Learning", "Decisions", "Activity", "Diagnostics", "Settings"];
const CONTEXTS: { id: ContextId; label: string }[] = [
  { id: "inside-success", label: "Inside Success" },
  { id: "mitchell", label: "Mitchell · dormant" },
  { id: "personal", label: "Personal" },
  { id: "mixed", label: "Mixed" },
  { id: "unknown", label: "Unknown" },
];

export function inferContext(value: string, fallback: ContextId = "personal") {
  const text = value.toLowerCase();
  const inside = /\b(inside success|dloa|dla|reps?|appointment setters?|sales department|sd-dloa|miami workday)\b/.test(text);
  const mitchell = /\b(mitchell|transformify|kajabi|bookfunnel|mitchell client)\b/.test(text);
  const personal = /\b(personal|upwork|home|my own|moonishaider12|private calendar)\b/.test(text);
  const matches = [inside, mitchell, personal].filter(Boolean).length;
  if (matches > 1 || /\b(across (my )?(contexts|work)|work and personal|mixed context)\b/.test(text)) {
    return { context: "mixed" as ContextId, inferred: true, reason: "More than one context is named" };
  }
  if (inside) return { context: "inside-success" as ContextId, inferred: true, reason: "Inside Success terms detected" };
  if (mitchell) return { context: "mitchell" as ContextId, inferred: true, reason: "Mitchell terms detected" };
  if (personal) return { context: "personal" as ContextId, inferred: true, reason: "Personal terms detected" };
  return { context: fallback, inferred: false, reason: "Kept the current context" };
}

function titleFromPrompt(value: string) {
  const compact = value.replace(/\s+/g, " ").trim();
  return (compact.length > 58 ? `${compact.slice(0, 57).trim()}…` : compact) || "New conversation";
}

function sessionContext(sessionId: string): ContextId | null {
  const match = sessionId.match(/^jarvis_(inside-success|mitchell|personal|mixed|unknown)_/);
  return (match?.[1] as ContextId | undefined) ?? null;
}

function nextLocalHour() {
  const value = new Date(Date.now() + 60 * 60 * 1000);
  value.setMinutes(0, 0, 0);
  const offset = value.getTimezoneOffset();
  return new Date(value.getTime() - offset * 60_000).toISOString().slice(0, 16);
}

type ExplicitPersonalAction = {
  action: "calendar" | "gmail-draft";
  payload: Record<string, unknown>;
};

export function parseExplicitPersonalAction(value: string, now = new Date()): ExplicitPersonalAction | null {
  const text = value.trim();
  const lower = text.toLowerCase().replace(/\s+/g, " ");
  if (/\b(invite|attendee|recurr|every (day|week|month)|work calendar|company calendar|send (the )?(email|draft|it))\b/.test(lower)) return null;
  const calendar = text.match(/^(?:please\s+)?(?:add|create|schedule|put)\s+(?:a\s+)?(?:personal\s+)?(?:calendar\s+)?(?:event|appointment|session|meeting)\s+(?:called|named|titled)\s+["“]?(.+?)["”]?\s+(today|tomorrow|on\s+\d{4}-\d{2}-\d{2})\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)(?:\s+for\s+(15|30|60)\s+minutes?)?\.?$/i);
  if (calendar) {
    const start = new Date(now);
    const day = calendar[2].toLowerCase();
    if (day === "tomorrow") start.setDate(start.getDate() + 1);
    else if (day.startsWith("on ")) {
      const [year, month, date] = day.slice(3).split("-").map(Number);
      start.setFullYear(year, month - 1, date);
    }
    let hour = Number(calendar[3]) % 12;
    if (calendar[5].toLowerCase() === "pm") hour += 12;
    start.setHours(hour, Number(calendar[4] || 0), 0, 0);
    if (start.getTime() <= now.getTime()) return null;
    const duration = Number(calendar[6] || 30);
    return { action: "calendar", payload: {
      title: calendar[1].trim(), start: start.toISOString(),
      end: new Date(start.getTime() + duration * 60_000).toISOString(),
      durationExplicit: Boolean(calendar[6]),
    } };
  }
  const draft = text.match(/^(?:please\s+)?(?:create|write|prepare|draft)\s+(?:an?\s+)?(?:unsent\s+)?(?:personal\s+)?(?:gmail\s+)?draft(?:\s+to\s+([^\s,;]+@[^\s,;]+))?\s+with\s+subject\s+["“]?(.+?)["”]?\s+and\s+(?:body|message)\s+["“]?([\s\S]+?)["”]?\.?$/i);
  if (draft) return { action: "gmail-draft", payload: {
    recipient: draft[1] || "", subject: draft[2].trim(), body: draft[3].trim(),
  } };
  return null;
}

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

export function isSpokenStopCommand(value: string) {
  const normalized = value.toLowerCase().replace(/[^a-z\s']/g, " ").replace(/\s+/g, " ").trim();
  return /^(?:(?:hey\s+)?jarvis\s+)?(?:stop|stop speaking|be quiet|cancel)(?:\s+(?:now|please))?$/.test(normalized);
}

export type SourceCard = { url: string; label: string; host: string; openable: boolean };

const SOURCE_HOSTS = [
  "github.com", "slack.com", "zoom.us", "calendar.google.com", "mail.google.com",
  "docs.google.com", "drive.google.com", "chatgpt.com", "gemini.google.com",
  "upwork.com", "openai.com",
];

export function sourceCards(value: string): SourceCard[] {
  const matches = [...value.matchAll(/(?:\[([^\]]{1,120})\]\()?(https:\/\/[^\s)\]}>]+)/g)];
  const seen = new Set<string>();
  return matches.flatMap((match) => {
    const url = match[2].replace(/[.,;:!?]+$/, "");
    if (seen.has(url)) return [];
    seen.add(url);
    try {
      const parsed = new URL(url);
      const host = parsed.hostname.toLowerCase();
      const openable = SOURCE_HOSTS.some((allowed) => host === allowed || host.endsWith(`.${allowed}`));
      return [{ url, host, openable, label: match[1]?.trim() || host.replace(/^www\./, "") }];
    } catch {
      return [];
    }
  });
}

export function withoutRawSourceUrls(value: string) {
  return value
    .replace(/\[([^\]]{1,120})\]\(https:\/\/[^\s)\]}>]+\)/g, "$1")
    .replace(/https:\/\/[^\s)\]}>]+/g, (match) => `[source]${/[.,;:!?]$/.test(match) ? match.slice(-1) : ""}`)
    .replace(/[ \t]+\n/g, "\n")
    .trim();
}

type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: { results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};

const fallbackHealth: HealthStatus = {
  state: "starting", hermesVersion: "0.20.0", backend: "Checking",
  context: "personal", modelRoute: "DeepSeek V4 Flash", budget: "Checking",
  writes: "Blocked", wakeListening: false, backgroundMode: "While Jarvis runs",
  message: "Starting the protected Hermes backend…",
};

function App() {
  const isHud = getCurrentWindow().label === "hud";
  const [health, setHealth] = useState<HealthStatus>(fallbackHealth);
  const [active, setActive] = useState("Today");
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
  const [voiceDeliveryFailed, setVoiceDeliveryFailed] = useState(false);
  const [speechStatus, setSpeechStatus] = useState<"idle" | "speaking" | "completed" | "stopped">("idle");
  const [modelOverride, setModelOverride] = useState<"auto" | "routine" | "difficult" | "review">("auto");
  const [projection, setProjection] = useState<Record<string, unknown> | null>(null);
  const [navigationDestination, setNavigationDestination] = useState("personal-upwork");
  const [navigationQuery, setNavigationQuery] = useState("");
  const [navigationPlan, setNavigationPlan] = useState<GuidedNavigationPlan | null>(null);
  const [guidedRead, setGuidedRead] = useState<GuidedReadResult | null>(null);
  const [personalActions, setPersonalActions] = useState<PersonalActionStatus | null>(null);
  const [personalPreview, setPersonalPreview] = useState<PersonalActionPreview | null>(null);
  const [personalResult, setPersonalResult] = useState<{ providerId: string; resourceKind: string; undoAvailable: boolean } | null>(null);
  const [eventTitle, setEventTitle] = useState("Jarvis acceptance check");
  const [eventStart, setEventStart] = useState(nextLocalHour);
  const [eventDuration, setEventDuration] = useState("15");
  const [draftRecipient, setDraftRecipient] = useState("");
  const [draftSubject, setDraftSubject] = useState("Jarvis draft acceptance check");
  const [draftBody, setDraftBody] = useState("This is a private unsent draft created through Jarvis acceptance. It has not been sent.");
  const [showAdvancedActions, setShowAdvancedActions] = useState(false);
  const [showAdvancedNav, setShowAdvancedNav] = useState(false);
  const [showActionPolicy, setShowActionPolicy] = useState(false);
  const [conversations, setConversations] = useState<HermesSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<HermesMessage[]>([]);
  const [conversationNotice, setConversationNotice] = useState("Loading recent conversations…");
  const [conversationSearch, setConversationSearch] = useState("");
  const [showArchivedConversations, setShowArchivedConversations] = useState(false);
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [conversationTitle, setConversationTitle] = useState("");
  const [contextReason, setContextReason] = useState("Current context");
  const [showContextCorrection, setShowContextCorrection] = useState(false);
  const [voiceSettling, setVoiceSettling] = useState(false);
  const [repairingCapability, setRepairingCapability] = useState<string | null>(null);
  const [showTour, setShowTour] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskType, setTaskType] = useState("personal-task");
  const [taskDue, setTaskDue] = useState("");
  const [checkpointSummary, setCheckpointSummary] = useState("");
  const [checkpointNext, setCheckpointNext] = useState("");
  const [decisionText, setDecisionText] = useState("");
  const [decisionReason, setDecisionReason] = useState("");
  const [checkpointProjectId, setCheckpointProjectId] = useState<string | null>(null);
  const [decisionOutcome, setDecisionOutcome] = useState("");
  const [meetingFollowupTitle, setMeetingFollowupTitle] = useState("");
  const [meetingProjectId, setMeetingProjectId] = useState("");
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
  const currentSessionIdRef = useRef<string | null>(null);
  const speechSessionRef = useRef(0);
  const bargeRecognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const silenceTimerRef = useRef<number | null>(null);
  const voiceDeadlineRef = useRef<number | null>(null);
  const conversationViewportRef = useRef<HTMLDivElement | null>(null);
  const scrollPositionsRef = useRef<Record<string, number>>({});

  function stopBargeListener() {
    const listener = bargeRecognitionRef.current;
    bargeRecognitionRef.current = null;
    if (listener) {
      listener.onend = null;
      listener.onerror = null;
      try { listener.stop(); } catch { /* already stopped */ }
    }
  }

  function cancelSpeech(session: number, status: "stopped" | "completed") {
    if (!("speechSynthesis" in window) || speechSessionRef.current !== session) return;
    ++speechSessionRef.current;
    stopBargeListener();
    window.speechSynthesis.cancel();
    setSpeechStatus(status);
  }

  function startBargeListener(session: number) {
    stopBargeListener();
    const Recognition = (window as unknown as { webkitSpeechRecognition?: new () => BrowserSpeechRecognition }).webkitSpeechRecognition;
    if (!Recognition) return;
    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
      const latest = Array.from(event.results).slice(-2).map((result) => result[0]?.transcript ?? "").join(" ").trim();
      if (isSpokenStopCommand(latest)) cancelSpeech(session, "stopped");
    };
    recognition.onend = () => {
      if (bargeRecognitionRef.current !== recognition || speechSessionRef.current !== session || !window.speechSynthesis.speaking) return;
      window.setTimeout(() => {
        if (bargeRecognitionRef.current === recognition && speechSessionRef.current === session && window.speechSynthesis.speaking) {
          try { recognition.start(); } catch { /* fail closed; button remains available */ }
        }
      }, 120);
    };
    recognition.onerror = () => undefined;
    bargeRecognitionRef.current = recognition;
    try { recognition.start(); } catch { bargeRecognitionRef.current = null; }
  }

  function speakText(value: string) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const session = ++speechSessionRef.current;
    const utterance = new SpeechSynthesisUtterance(value);
    const ryan = window.speechSynthesis.getVoices().find((voice) => voice.name.toLowerCase().includes("ryan"));
    if (ryan) utterance.voice = ryan;
    utterance.rate = 1.08;
    utterance.onstart = () => {
      if (speechSessionRef.current !== session) return;
      setSpeechStatus("speaking");
      startBargeListener(session);
    };
    utterance.onend = () => {
      if (speechSessionRef.current !== session) return;
      stopBargeListener();
      setSpeechStatus("completed");
    };
    utterance.onerror = () => {
      if (speechSessionRef.current !== session) return;
      stopBargeListener();
      setSpeechStatus("stopped");
    };
    window.speechSynthesis.speak(utterance);
  }

  async function refreshConversations() {
    try {
      const value = await invoke<{ data?: HermesSession[] }>("list_conversations");
      const recent = (value.data ?? []).filter((item) => item.source === "desktop");
      setConversations(recent);
      setConversationNotice(recent.length ? "" : "No conversations yet");
      return recent;
    } catch (error) {
      setConversationNotice(`Conversation history unavailable: ${String(error)}`);
      return [];
    }
  }

  async function loadConversation(sessionId: string) {
    if (currentSessionIdRef.current && conversationViewportRef.current) {
      scrollPositionsRef.current[currentSessionIdRef.current] = conversationViewportRef.current.scrollTop;
    }
    const selectedContext = sessionContext(sessionId);
    if (selectedContext) {
      setContext(selectedContext);
      setContextReason("Restored with this conversation");
    }
    setCurrentSessionId(sessionId);
    currentSessionIdRef.current = sessionId;
    window.localStorage.setItem("jarvis.activeConversation", sessionId);
    setAnswer("");
    setProgress([]);
    setConversationNotice("Loading conversation…");
    try {
      const value = await invoke<{ data?: HermesMessage[] }>("conversation_messages", { sessionId });
      setMessages((value.data ?? []).filter((item) => ["user", "assistant", "tool"].includes(item.role) && item.content));
      setConversationNotice("");
      setActive("Chat");
      window.requestAnimationFrame(() => {
        if (conversationViewportRef.current) conversationViewportRef.current.scrollTop = scrollPositionsRef.current[sessionId] ?? conversationViewportRef.current.scrollHeight;
      });
    } catch (error) {
      setMessages([]);
      setConversationNotice(`Conversation could not be loaded: ${String(error)}`);
    }
  }

  async function ensureConversation(text: string, targetContext: ContextId) {
    if (currentSessionIdRef.current && sessionContext(currentSessionIdRef.current) === targetContext) {
      return currentSessionIdRef.current;
    }
    const value = await invoke<{ session?: HermesSession }>("create_conversation", {
      title: titleFromPrompt(text), context: targetContext,
    });
    const session = value.session;
    if (!session?.id) throw new Error("Hermes returned no conversation id");
    setCurrentSessionId(session.id);
    currentSessionIdRef.current = session.id;
    window.localStorage.setItem("jarvis.activeConversation", session.id);
    setMessages([]);
    await refreshConversations();
    return session.id;
  }

  function newConversation() {
    currentSessionIdRef.current = null;
    setCurrentSessionId(null);
    setMessages([]);
    setAnswer("");
    setProgress([]);
    setPrompt("");
    setConversationNotice("New conversation");
    window.localStorage.removeItem("jarvis.activeConversation");
    setActive("Chat");
  }

  async function controlConversation(sessionId: string, action: "rename" | "pin" | "unpin" | "archive" | "unarchive", title?: string) {
    try {
      await invoke("conversation_control", { request: { sessionId, action, ...(title ? { title } : {}) } });
      setRenamingSessionId(null); setConversationTitle("");
      if (action === "archive" && currentSessionIdRef.current === sessionId) newConversation();
      await refreshConversations();
      setConversationNotice(`${action === "archive" ? "Archived" : action === "unarchive" ? "Restored" : action === "rename" ? "Renamed" : action === "pin" ? "Pinned" : "Unpinned"} · conversation content unchanged`);
    } catch (error) {
      setConversationNotice(`Conversation was not changed: ${String(error)}`);
    }
  }

  function clearSilenceTimer() {
    if (silenceTimerRef.current !== null) window.clearTimeout(silenceTimerRef.current);
    silenceTimerRef.current = null;
    setVoiceSettling(false);
  }

  function scheduleNaturalVoiceFinish() {
    clearSilenceTimer();
    setVoiceSettling(true);
    silenceTimerRef.current = window.setTimeout(() => {
      if (recorderRef.current?.state === "recording") {
        recognitionRef.current?.stop();
        recorderRef.current.stop();
        setRecording(false);
        setVoiceSettling(false);
        setProgress(["Thought complete · transcribing the full recording…"]);
      }
    }, 5500);
  }

  useEffect(() => {
    const refreshHealth = () => invoke<HealthStatus>("system_status").then(setHealth).catch((error) => {
      setHealth({ ...fallbackHealth, state: "degraded", backend: "Unavailable", message: String(error) });
    });
    void refreshHealth();
    const healthTimer = window.setInterval(refreshHealth, 5000);
    invoke<boolean>("autostart_status").then(setAutostart).catch(() => undefined);
    invoke<PersonalActionStatus>("personal_action_status").then(setPersonalActions).catch(() => undefined);
    void (async () => {
      const recent = await refreshConversations();
      const saved = window.localStorage.getItem("jarvis.activeConversation");
      const available = recent.find((item) => item.id === saved && !Boolean(item.archived));
      if (available) await loadConversation(available.id);
    })();
    if (!window.localStorage.getItem("jarvis.tour.ux2")) setShowTour(true);
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
          const spoken = spokenProjection(payload.output);
          speakText(spoken || "The full result is ready on screen.");
        }
        speakResponseRef.current = false;
        const sessionId = currentSessionIdRef.current;
        if (sessionId) window.setTimeout(() => { void loadConversation(sessionId); void refreshConversations(); }, 120);
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
      if (silenceTimerRef.current !== null) window.clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
      if (voiceDeadlineRef.current !== null) window.clearTimeout(voiceDeadlineRef.current);
      recognitionRef.current?.stop();
      if (recorderRef.current?.state === "recording") recorderRef.current.stop();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      stopBargeListener();
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
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
    if (!current || current.mode !== "focus") return;
    const sample = async () => {
      await invoke("observe_frontmost", { focusId: current.focus_id, context }).catch(() => undefined);
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    };
    const timer = window.setInterval(() => void sample(), 45_000);
    return () => window.clearInterval(timer);
  }, [context, localState?.focusSessions?.map((item) => `${item.focus_id}:${item.stopped_at ?? "active"}`).join("|")]);

  const contextLabel = useMemo(() => CONTEXTS.find((item) => item.id === context)?.label ?? context, [context]);
  const contextBadgeText = useMemo(() => {
    if (context === "mixed" || context === "unknown") return `${contextLabel} · needs review`;
    const confidence = contextReason.startsWith("Corrected") ? 100 : contextReason.startsWith("Restored") ? 98 : contextReason.includes("detected") ? 96 : 82;
    return `${contextLabel} · ${confidence}%`;
  }, [context, contextLabel, contextReason]);
  const visibleConversations = useMemo(() => {
    const query = conversationSearch.toLowerCase().trim();
    return conversations
      .filter((item) => Boolean(item.archived) === showArchivedConversations)
      .filter((item) => !query || `${item.title ?? ""} ${item.preview ?? ""}`.toLowerCase().includes(query))
      .sort((left, right) => Number(Boolean(right.pinned)) - Number(Boolean(left.pinned)));
  }, [conversations, conversationSearch, showArchivedConversations]);
  const conversationContent = useMemo(() => messages.filter((item) => item.role === "user" || item.role === "assistant"), [messages]);
  const technicalMessages = useMemo(() => messages.filter((item) => item.role === "tool"), [messages]);
  const currentFocus = useMemo(() => localState?.focusSessions?.find((item) => !item.stopped_at) ?? null, [localState?.focusSessions]);
  const visibleTodayEvidence = useMemo(() => (localState?.recentLedger ?? []).filter((item) => {
    const state = item.attention_state;
    if (!state || state.status === "active") return true;
    if (state.status === "snoozed" && state.snoozed_until) return new Date(state.snoozed_until).getTime() <= Date.now();
    return false;
  }), [localState?.recentLedger]);
  const sourceEvidenceStatus = useMemo(() => {
    const status = new Map<string, string>();
    for (const entry of localState?.recentLedger ?? []) {
      for (const source of entry.evidence_sources ?? []) {
        if (!source.uri) continue;
        status.set(source.uri, `${entry.local_date} · ${entry.confidence_state} · fresh ${entry.freshness_at.slice(0, 10)}`);
      }
    }
    return status;
  }, [localState?.recentLedger]);

  function finishTour() {
    window.localStorage.setItem("jarvis.tour.ux2", "seen");
    setShowTour(false);
  }

  async function startPrompt(text: string, speakResponse = false, deliveryId?: string): Promise<boolean> {
    if (!text.trim() || busy) return false;
    const inference = inferContext(text, context);
    const targetContext = inference.context;
    if (inference.inferred && targetContext !== context) setContext(targetContext);
    setContextReason(inference.reason);
    let sessionId: string;
    try {
      sessionId = await ensureConversation(text, targetContext);
    } catch (error) {
      setProgress([`Conversation could not start: ${String(error)}`]);
      return false;
    }
    const optimistic: HermesMessage = {
      id: `pending-${Date.now()}`, session_id: sessionId, role: "user", content: text.trim(), timestamp: Date.now() / 1000,
    };
    setMessages((old) => [...old, optimistic]);
    const personalAction = targetContext === "personal" ? parseExplicitPersonalAction(text) : null;
    if (personalAction && personalActions?.connected && personalActions.personalCapabilitiesEnabled && personalActions.mode === "auto-explicit") {
      setBusy(true); setAnswer(""); setProgress(["Explicit personal request recognized", "Checking account, target, permission snapshot, and Action Firewall…"]);
      try {
        const result = await invoke<{ providerId: string; resourceKind: string; undoAvailable: boolean; conversationPersisted?: boolean; conversationWarning?: string }>("personal_action_explicit", {
          request: { action: personalAction.action, context: targetContext, sessionId, ownerRequest: text.trim(), ...personalAction.payload },
        });
        setPersonalResult(result); await refreshPersonalActions(); setPrompt("");
        const message = result.resourceKind === "gmail-draft"
          ? "I created the unsent personal Gmail draft and opened it. Sending is unavailable."
          : "I created the personal calendar event exactly as requested. Undo is available in Actions.";
        setAnswer(message); setProgress((old) => [...old, "Completed through the bounded personal capability", ...(result.conversationWarning ? [result.conversationWarning] : [])]);
        if (result.conversationPersisted) {
          await loadConversation(sessionId);
          await refreshConversations();
        } else {
          setMessages((old) => [...old, { id: `local-${Date.now()}`, session_id: sessionId, role: "assistant", content: message, timestamp: Date.now() / 1000 }]);
        }
        if (speakResponse) speakText(message);
        return true;
      } catch (error) {
        setProgress((old) => [...old, `Personal action stopped safely: ${String(error)}`]);
        return false;
      } finally { setBusy(false); }
    }
    setBusy(true); setAnswer("");
    setProgress([`Acknowledged · ${CONTEXTS.find((item) => item.id === targetContext)?.label ?? targetContext}`, "Preparing the smallest relevant source plan…"]);
    stageCostRef.current = 0; stageTokensRef.current = 0;
    speakResponseRef.current = speakResponse;
    if (speakResponse && "speechSynthesis" in window) {
      speakText("I'm checking that now.");
    }
    try {
      const started = await invoke<RunStart>("start_run", {
        request: { prompt: text.trim(), context: targetContext, sessionId, overrideRoute: modelOverride, deliveryId },
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
    if (!("speechSynthesis" in window)) return;
    const wasSpeaking = speechStatus === "speaking" || window.speechSynthesis.speaking;
    if (wasSpeaking) cancelSpeech(speechSessionRef.current, "stopped");
    else stopBargeListener();
  }

  async function transcribeBlob(blob: Blob) {
    setProgress(["Transcribing the complete recording…"]);
    setVoiceRetryAvailable(false);
    setVoiceDeliveryFailed(false);
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
          setVoiceDeliveryFailed(true);
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

  async function retryVoiceDelivery() {
    const transcript = voiceTranscript.trim();
    if (!transcript) return;
    if (!voiceDeliveryIdRef.current) voiceDeliveryIdRef.current = crypto.randomUUID();
    const delivered = await startPrompt(transcript, true, voiceDeliveryIdRef.current);
    if (delivered) {
      lastRecordingRef.current = null;
      voiceDeliveryIdRef.current = null;
      setVoiceRetryAvailable(false);
      setVoiceDeliveryFailed(false);
    } else {
      setVoiceRetryAvailable(true);
      setVoiceDeliveryFailed(true);
      setProgress((old) => [...old, "Delivery still failed. The transcript and recording remain in memory; nothing was duplicated."]);
    }
  }

  function runVoiceRecoveryDiagnostic() {
    const transcript = "Reply with exactly: Voice recovery passed.";
    stopSpeaking();
    setActive("Chat");
    setVoiceTranscript(transcript);
    setPrompt(transcript);
    voiceDeliveryIdRef.current = crypto.randomUUID();
    setVoiceRetryAvailable(true);
    setVoiceDeliveryFailed(true);
    setProgress([
      "Diagnostic backend rejection injected before delivery. Nothing was submitted.",
      "The exact transcript is retained in memory. Choose Retry delivery, Edit transcript, or Discard.",
    ]);
  }

  function runSpokenStopDiagnostic() {
    setActive("Chat");
    setAnswer("Spoken Stop diagnostic. Jarvis is reading a harmless local passage. Say “Stop” once; no request or recording will be submitted.");
    setProgress(["Local spoken-interruption diagnostic · no model call · no submission"]);
    speakText("This is a harmless local interruption test. Jarvis will keep reading this neutral passage while the temporary listener waits for your explicit command. Ordinary conversation is ignored. When the command is heard, speech ends immediately and the screen confirms that no replay is scheduled. This passage is intentionally long enough to make the interruption obvious. The test sends no request, submits no recording, and stores no transcript.");
  }

  async function toggleVoice() {
    if (recording && recorderRef.current) {
      clearSilenceTimer();
      if (voiceDeadlineRef.current !== null) window.clearTimeout(voiceDeadlineRef.current);
      voiceDeadlineRef.current = null;
      recognitionRef.current?.stop();
      recorderRef.current.stop();
      setRecording(false);
      setProgress(["Done speaking · transcribing the complete recording…"]);
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
      const Recognition = (window as unknown as { webkitSpeechRecognition?: new () => BrowserSpeechRecognition }).webkitSpeechRecognition;
      if (Recognition) {
        const recognition = new Recognition();
        recognition.continuous = true; recognition.interimResults = true; recognition.lang = "en-US";
        recognition.onresult = (event) => {
          const text = Array.from(event.results).map((result) => result[0]?.transcript ?? "").join(" ").trim();
          if (text) {
            liveTranscriptRef.current = text;
            setVoiceTranscript(text);
          }
          const latest = Array.from(event.results).slice(-1)[0];
          if (latest?.isFinal && text.split(/\s+/).length >= 2) scheduleNaturalVoiceFinish();
          else clearSilenceTimer();
        };
        recognition.onend = null;
        recognition.onerror = null;
        recognitionRef.current = recognition;
        try { recognition.start(); } catch { recognitionRef.current = null; }
      }
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onstop = async () => {
        clearSilenceTimer();
        if (voiceDeadlineRef.current !== null) window.clearTimeout(voiceDeadlineRef.current);
        voiceDeadlineRef.current = null;
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
      voiceDeadlineRef.current = window.setTimeout(() => {
        if (recorderRef.current?.state === "recording") {
          recognitionRef.current?.stop();
          recorderRef.current.stop();
          setRecording(false);
          setProgress(["Ten-minute recording limit reached · transcribing everything captured so far…"]);
        }
      }, 600_000);
      setRecording(true);
      if (speechStatus === "speaking") setSpeechStatus("stopped");
      setProgress(["Listening · speak naturally, then choose Done speaking. Jarvis waits 5.5 seconds through pauses before finishing automatically."]);
    } catch (error) {
      clearSilenceTimer();
      if (voiceDeadlineRef.current !== null) window.clearTimeout(voiceDeadlineRef.current);
      voiceDeadlineRef.current = null;
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
    setVoiceDeliveryFailed(false);
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

  async function repairCapability(capability: "backend" | "personal-google" | "local-state") {
    setRepairingCapability(capability);
    setLocalNotice(`Repairing ${capability} through the narrow reviewed path…`);
    try {
      await invoke("safe_repair", { capability });
      if (capability === "personal-google") await refreshPersonalActions();
      const refreshed = await invoke<JarvisState>("jarvis_state", { context });
      setLocalState(refreshed);
      const refreshedHealth = await invoke<HealthStatus>("system_status");
      setHealth(refreshedHealth);
      setLocalNotice(`${capability} recovered without changing tools, scopes, accounts, or write authority.`);
    } catch (error) {
      setLocalNotice(`${capability} repair stopped safely: ${String(error)}`);
    } finally {
      setRepairingCapability(null);
    }
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

  async function startFocus(minutes: 30 | 60 | 90 | 120) {
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
    const result = await invoke<{ summary?: { observationCount: number; applications: string[]; screenshotsRetained: number } }>("local_control", { operation: "stop-focus", request: { focusId } });
    setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    setLocalNotice(`Focus stopped · ${result.summary?.observationCount ?? 0} metadata observation(s) · ${result.summary?.applications?.join(", ") || "no app sampled"} · screenshots retained ${result.summary?.screenshotsRetained ?? 0}`);
  }

  async function controlFocus(focusId: string, action: "pause" | "resume") {
    await invoke("local_control", { operation: "focus-control", request: { focusId, action } });
    setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    setLocalNotice(action === "pause" ? "Focus paused · observation is off." : "Focus resumed · visible metadata-only observation is on.");
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

  async function createInboxTask() {
    if (!taskTitle.trim() || ["mixed", "unknown"].includes(context)) return;
    try {
      await invoke("local_control", { operation: "task-create", request: { context, title: taskTitle.trim(), taskType, priority: taskType === "blocker" ? 90 : 50, ...(taskDue ? { dueAt: new Date(taskDue).toISOString() } : {}) } });
      setTaskTitle(""); setTaskDue(""); setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
      setLocalNotice("Added locally to Jarvis Inbox. No external action occurred.");
    } catch (error) { setLocalNotice(`Inbox item was not added: ${String(error)}`); }
  }

  async function applyMeetingFollowup() {
    const evidence = localState?.meetingEvidence[0];
    if (!evidence || !meetingFollowupTitle.trim()) return;
    try {
      await invoke("local_control", { operation: "meeting-followup", request: {
        context, evidenceId: evidence.evidence_id, title: meetingFollowupTitle.trim(),
        ...(meetingProjectId ? { projectId: meetingProjectId } : {}),
      } });
      setMeetingFollowupTitle(""); setMeetingProjectId("");
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
      setLocalNotice("Reviewed meeting follow-up added locally with Zoom provenance. No external system changed.");
    } catch (error) { setLocalNotice(`Meeting follow-up was not added: ${String(error)}`); }
  }

  async function openEvidenceSource(url: string) {
    try {
      await invoke("open_evidence_source", { url, context });
      setLocalNotice("Opened the exact reviewed source in the context-matched Chrome profile. No page action occurred.");
    } catch (error) { setLocalNotice(`Source stayed closed: ${String(error)}`); }
  }

  async function controlTask(taskId: string, action: "planned" | "in-progress" | "completed" | "verified" | "snoozed" | "archived") {
    try {
      await invoke("local_control", { operation: "task-control", request: { taskId, action, days: 1 } });
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
      setLocalNotice(`Inbox item moved to ${action}.`);
    } catch (error) { setLocalNotice(`Inbox item was not changed: ${String(error)}`); }
  }

  async function controlAttention(entryId: string, action: "completed" | "snoozed" | "dismissed" | "restore" | "correct-context", correctedContext?: ContextId) {
    try {
      await invoke("local_control", { operation: "attention-control", request: { context, entryId, action, ...(correctedContext ? { correctedContext } : {}) } });
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
      setLocalNotice(action === "correct-context" ? `Evidence moved to ${correctedContext}. Provenance was preserved.` : `Today item ${action}. This local action is reversible in Activity.`);
    } catch (error) { setLocalNotice(`Today item was not changed: ${String(error)}`); }
  }

  function askAboutEvidence(summary: string) {
    setPrompt(`Why does this matter, what should I do next, and what source evidence supports it? ${summary}`);
    setActive("Chat");
  }

  function prepareSchedule(summary: string) {
    setTaskTitle(summary);
    setTaskType("reminder");
    setTaskDue(nextLocalHour());
    setActive("Inbox");
    setLocalNotice("Review the suggested due time, then add the reminder locally. No Calendar event has been created.");
  }

  async function saveCheckpoint(projectId: string) {
    const evidenceId = localState?.recentLedger.find((item) => item.evidence_ids.length)?.evidence_ids[0];
    if (!evidenceId || !checkpointSummary.trim() || !checkpointNext.trim()) {
      setLocalNotice("Save My Place needs a summary, exact next step, and one current-context evidence link."); return;
    }
    try {
      await invoke("local_control", { operation: "project-checkpoint", request: {
        context, projectId, evidenceId, summary: checkpointSummary.trim(), nextStep: checkpointNext.trim(),
        changed: "Owner checkpoint recorded from the current project state", unresolved: "Review on resume", resources: [],
      } });
      setCheckpointProjectId(null); setCheckpointSummary(""); setCheckpointNext("");
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
      setLocalNotice("Place saved with same-context evidence. No source or external system was changed.");
    } catch (error) { setLocalNotice(`Checkpoint was not saved: ${String(error)}`); }
  }

  async function createDecision() {
    const evidenceId = localState?.recentLedger.find((item) => item.evidence_ids.length)?.evidence_ids[0];
    if (!evidenceId || !decisionText.trim() || !decisionReason.trim()) {
      setLocalNotice("A decision needs the decision, reasoning, and one current-context evidence link."); return;
    }
    try {
      await invoke("local_control", { operation: "decision-create", request: {
        context, decision: decisionText.trim(), reasoning: decisionReason.trim(), evidenceId,
        alternatives: [], expectedOutcome: "Review whether the expected result occurred",
      } });
      setDecisionText(""); setDecisionReason(""); setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
      setLocalNotice("Decision recorded locally with evidence.");
    } catch (error) { setLocalNotice(`Decision was not recorded: ${String(error)}`); }
  }

  async function saveDecisionOutcome(decisionId: string) {
    if (!decisionOutcome.trim()) return;
    try {
      await invoke("local_control", { operation: "decision-outcome", request: { decisionId, outcome: decisionOutcome.trim() } });
      setDecisionOutcome(""); setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
      setLocalNotice("Actual outcome added to the decision journal.");
    } catch (error) { setLocalNotice(`Outcome was not saved: ${String(error)}`); }
  }

  async function evaluateRadar(radarId: string) {
    try {
      const result = await invoke<{ materialChange: boolean; evidenceCount: number }>("local_control", { operation: "radar-evaluate", request: { radarId } });
      setLocalNotice(result.materialChange ? `Meaningful change detected from ${result.evidenceCount} approved evidence items; queued for the local digest.` : `No meaningful change across ${result.evidenceCount} approved evidence items. No alert generated.`);
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
    } catch (error) { setLocalNotice(`Radar check unavailable: ${String(error)}`); }
  }

  async function reviewMemory(memoryId: string, action: "confirmed" | "rejected" | "superseded") {
    try {
      await invoke("local_control", { operation: "memory-control", request: { memoryId, action } });
      setLocalState(await invoke<JarvisState>("jarvis_state", { context }));
      setLocalNotice(`Learned item marked ${action}.`);
    } catch (error) { setLocalNotice(`Learned item was not changed: ${String(error)}`); }
  }

  function startMeetingWorkflow(kind: "before" | "after" | "absent") {
    const promptByKind = {
      before: "Prepare a source-backed briefing for my next authorized meeting: prior decisions, open questions, commitments, project changes, and agenda suggestions.",
      after: "Review my latest authorized meeting evidence and extract decisions, owners, follow-ups, contradictions, and proposed Inbox or Project updates. Do not make external changes.",
      absent: "Catch me up on the latest authorized meeting I missed: what changed, what affects me, what requires action, and what is general information.",
    };
    setPrompt(promptByKind[kind]); setActive("Chat");
  }

  async function refreshPersonalActions() {
    try { setPersonalActions(await invoke<PersonalActionStatus>("personal_action_status")); }
    catch (error) { setLocalNotice(`Personal action status unavailable: ${String(error)}`); }
  }

  async function connectPersonalActions() {
    setLocalNotice("Opening the exact personal Google consent page in Chrome Profile 1…");
    try {
      await invoke("authorize_personal_google_actions");
      await refreshPersonalActions();
      setLocalNotice("Personal Calendar and unsent-draft grant connected. Gmail sending and work-account writes remain absent.");
    } catch (error) { setLocalNotice(`Personal Google connection not completed: ${String(error)}`); }
  }

  async function togglePersonalActions(enabled: boolean) {
    try {
      await invoke("set_personal_actions_enabled", { enabled });
      await refreshPersonalActions();
      setPersonalPreview(null); setPersonalResult(null);
      setLocalNotice(enabled
        ? "Natural personal Calendar and unsent-draft requests are enabled. Ambiguous requests still stop for review; generic and company/client writes remain killed."
        : "Personal Calendar and unsent-draft execution disabled. Existing personal resources were not changed.");
    } catch (error) { setLocalNotice(`Personal action setting was not changed: ${String(error)}`); }
  }

  async function previewCalendarEvent() {
    const start = new Date(eventStart);
    if (Number.isNaN(start.getTime())) { setLocalNotice("Choose a valid event start."); return; }
    const end = new Date(start.getTime() + Number(eventDuration) * 60_000);
    try {
      const value = await invoke<PersonalActionPreview>("personal_action_preview", { request: {
        action: "calendar", title: eventTitle, start: start.toISOString(), end: end.toISOString(),
        reminderMinutes: 10, colorId: "9",
      }});
      setPersonalPreview(value); setPersonalResult(null);
      setLocalNotice("Exact event staged only. Review title, time, 10-minute reminder, blue color, account, hash, and expiry before creating it.");
    } catch (error) { setLocalNotice(`Calendar preview not staged: ${String(error)}`); }
  }

  async function previewGmailDraft() {
    try {
      const value = await invoke<PersonalActionPreview>("personal_action_preview", { request: {
        action: "gmail-draft", recipient: draftRecipient, subject: draftSubject, body: draftBody,
      }});
      setPersonalPreview(value); setPersonalResult(null);
      setLocalNotice("Exact unsent draft staged only. Review the recipient, subject, body, account, hash, and expiry before creating it.");
    } catch (error) { setLocalNotice(`Draft preview not staged: ${String(error)}`); }
  }

  async function executePersonalPreview() {
    if (!personalPreview) return;
    try {
      const value = await invoke<{ providerId: string; resourceKind: string; undoAvailable: boolean }>(
        "personal_action_execute", { proposalId: personalPreview.proposalId, previewHash: personalPreview.previewHash });
      setPersonalResult(value); setPersonalPreview(null); await refreshPersonalActions();
      setLocalNotice(value.resourceKind === "gmail-draft"
        ? "Unsent personal draft created and opened in Chrome Profile 1. Jarvis cannot send it."
        : "Personal event created exactly as previewed. Undo is available below.");
    } catch (error) { setLocalNotice(`Personal action stopped safely: ${String(error)}`); }
  }

  async function undoCalendarEvent(providerId = personalResult?.providerId) {
    if (!providerId) return;
    try {
      await invoke("personal_calendar_undo", { providerId });
      setPersonalResult(null); await refreshPersonalActions();
      setLocalNotice("Jarvis-created event was undone. No other calendar item was changed.");
    } catch (error) { setLocalNotice(`Undo stopped safely: ${String(error)}`); }
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

  async function readGuidedPublicResults() {
    if (!navigationPlan || navigationPlan.destination !== "public-search") return;
    setLocalNotice("Reading the same public query through the no-session evidence adapter…");
    try {
      const result = await invoke<GuidedReadResult>("guided_navigation_read", {
        request: { destination: navigationPlan.destination, context: navigationPlan.context, query: navigationPlan.query },
      });
      setGuidedRead(result);
      setLocalNotice("Scrollable cited results loaded in Jarvis. No logged-in page, account, or form was read or changed.");
    } catch (error) { setGuidedRead(null); setLocalNotice(`Guided read stopped safely: ${String(error)}`); }
  }

  if (isHud) return <div className="hud-shell">
    <div className="hud-title"><span className="orb"/><span>Ask Jarvis</span><small>{contextLabel}</small></div>
    <form className="hud-composer" onSubmit={submit}>
      <input autoFocus value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="What needs your attention?"/>
      <button type="button" className={recording ? "danger" : "quiet"} onClick={() => void toggleVoice()}>{recording ? "Done speaking" : "Talk"}</button>
      <button type="submit">Ask</button>
    </form>
    {voiceTranscript && <div className="live-transcript">{voiceTranscript}</div>}
    {progress[0] && <div className="hud-status">{progress[0]}</div>}
  </div>;

  return <div className="shell">
    {showTour && <section className="tour" role="dialog" aria-label="Welcome to Jarvis"><div><p className="eyebrow">Jarvis UX 2.0</p><h2>Your evidence-backed operating system</h2><ol><li><strong>Today</strong> shows what deserves attention and why.</li><li><strong>Chat</strong> keeps durable conversations; Talk waits through natural pauses.</li><li><strong>Inbox and Projects</strong> close loops and save your place without changing external systems.</li><li><strong>Actions</strong> remains personal, narrow, reversible, and fail-closed.</li></ol><button onClick={finishTour}>Show me Jarvis</button></div></section>}
    <aside>
      <div className="brand"><span className="orb"/><div><strong>JARVIS</strong><small>Hermes intelligence</small></div></div>
      <nav>{EVERYDAY_NAV.map((item) => <button key={item} className={active === item ? "active" : ""} onClick={() => setActive(item)}>{item}</button>)}
        <button className={ADVANCED_NAV.includes(active) ? "active nav-more" : "nav-more"} onClick={() => setShowAdvancedNav(!showAdvancedNav)}>{showAdvancedNav ? "Hide Build & Automate" : "Build & Automate"}</button>
        {showAdvancedNav && <div className="advanced-nav">{ADVANCED_NAV.map((item) => <button key={item} className={active === item ? "active" : ""} onClick={() => setActive(item)}>{item}</button>)}</div>}
      </nav>
      <section className="thread-list" aria-label="Recent conversations">
        <div><strong>Conversations</strong><button className="thread-new" onClick={newConversation} aria-label="New conversation">+</button></div>
        <input className="thread-search" aria-label="Search conversations" value={conversationSearch} onChange={(event) => setConversationSearch(event.target.value)} placeholder="Search"/>
        <button className="thread-archive-toggle" onClick={() => setShowArchivedConversations(!showArchivedConversations)}>{showArchivedConversations ? "← Recent" : "Archived"}</button>
        {visibleConversations.slice(0, 12).map((item) => <article className={`thread-row ${currentSessionId === item.id ? "selected" : ""}`} key={item.id}>
          {renamingSessionId === item.id ? <form onSubmit={(event) => { event.preventDefault(); void controlConversation(item.id, "rename", conversationTitle.trim()); }}>
            <input autoFocus value={conversationTitle} maxLength={100} onChange={(event) => setConversationTitle(event.target.value)}/><button type="submit" disabled={!conversationTitle.trim()}>Save</button><button type="button" className="quiet" onClick={() => setRenamingSessionId(null)}>Cancel</button>
          </form> : <>
            <button className="thread-open" onClick={() => void loadConversation(item.id)}>
              <span>{Boolean(item.pinned) ? "◆ " : ""}{item.title || item.preview || "Untitled"}</span><small>{sessionContext(item.id) || "unknown"} · {item.message_count ?? 0} messages</small>
            </button>
            <div className="thread-controls"><button title="Rename" onClick={() => { setRenamingSessionId(item.id); setConversationTitle(item.title || item.preview || ""); }}>Rename</button><button title={Boolean(item.pinned) ? "Unpin" : "Pin"} onClick={() => void controlConversation(item.id, Boolean(item.pinned) ? "unpin" : "pin")}>{Boolean(item.pinned) ? "Unpin" : "Pin"}</button><button title={Boolean(item.archived) ? "Restore" : "Archive"} onClick={() => void controlConversation(item.id, Boolean(item.archived) ? "unarchive" : "archive")}>{Boolean(item.archived) ? "Restore" : "Archive"}</button></div>
          </>}
        </article>)}
        {!visibleConversations.length && !conversationNotice && <small>{showArchivedConversations ? "No archived conversations" : "No matching conversations"}</small>}
        {conversationNotice && <small>{conversationNotice}</small>}
      </section>
      <div className="sidebar-foot">
        <span className={`health-dot ${health.state}`}/><span>{health.state === "ready" ? "Jarvis core ready" : health.message}</span>
      </div>
    </aside>
    <main>
      <header>
        <div><p className="eyebrow">{active}</p><h1>{active === "Today" ? "Good evening, Syed." : active}</h1></div>
        <div className="header-actions"><button type="button" className={recording ? "danger" : "quiet"} onClick={() => void toggleVoice()}>{recording ? "Done speaking" : "Talk"}</button>{voiceSettling && <span className="voice-settling">Waiting for the rest…</span>}<div className="context-control"><small>{contextReason}</small><button type="button" className="context-badge" onClick={() => setShowContextCorrection(!showContextCorrection)}>{contextBadgeText}</button>{showContextCorrection && <label className="context-correction"><span>Correct context</span><select aria-label="Current context" value={context} onChange={(event) => { const value = event.target.value as ContextId; setContext(value); setContextReason("Corrected by you"); setShowContextCorrection(false); newConversation(); }}>
          {CONTEXTS.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}
        </select></label>}</div></div>
      </header>

      {active === "Today" && <>
        <section className="hero card">
          <div><p className="eyebrow">Current attention</p><h2>Ready when you are.</h2><p>{health.message}</p></div>
          <div className="pulse"><span/><span/><span/></div>
        </section>
        <section className="today-board">
          <article className="card"><p className="eyebrow">Top evidence</p><h3>What changed recently</h3>{visibleTodayEvidence.slice(0, 3).map((item) => { const source = (item.evidence_sources ?? []).find((candidate) => candidate.uri && sourceCards(candidate.uri)[0]?.openable); return <div className="attention-item" key={item.entry_id}><strong>{item.summary}</strong><small>{item.local_date} · {item.confidence_state} · {item.evidence_ids.length} source link(s)</small><p>Why it matters: this is fresh, context-scoped evidence that may affect your current priorities.</p><div className="focus-controls">{source?.uri && <button className="quiet" onClick={() => void openEvidenceSource(source.uri!)}>Open evidence</button>}<button className="quiet" onClick={() => askAboutEvidence(item.summary)}>Ask Jarvis</button><button className="quiet" onClick={() => void controlAttention(item.entry_id, "completed")}>Complete</button><button className="quiet" onClick={() => void controlAttention(item.entry_id, "snoozed")}>Snooze</button><button className="quiet" onClick={() => prepareSchedule(item.summary)}>Schedule</button><button className="quiet" onClick={() => void controlAttention(item.entry_id, "dismissed")}>Dismiss</button><select aria-label={`Correct context for ${item.summary}`} value={context} onChange={(event) => void controlAttention(item.entry_id, "correct-context", event.target.value as ContextId)}>{CONTEXTS.filter((candidate) => !["mixed", "unknown"].includes(candidate.id)).map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.label}</option>)}</select></div></div>; })}{!visibleTodayEvidence.length && <p>No current-context evidence yet. Ask Jarvis for a bounded refresh.</p>}</article>
          <article className="card"><p className="eyebrow">Waiting & blockers</p><h3>{localState?.inboxItems.filter((item) => item.waiting_on || item.task_type === "blocker").length ?? 0} need review</h3>{localState?.inboxItems.filter((item) => item.waiting_on || item.task_type === "blocker").slice(0, 3).map((item) => <div className="attention-item" key={item.task_id}><strong>{item.title}</strong><small>{item.waiting_on ? `Waiting on ${item.waiting_on}` : "Blocker"} · {item.status}</small><p>Why it matters: this item is waiting, blocked, or at risk of being forgotten.</p><div className="focus-controls"><button className="quiet" onClick={() => askAboutEvidence(item.title)}>Ask Jarvis</button>{item.task_type !== "commitment" && <button className="quiet" onClick={() => void controlTask(item.task_id, "completed")}>Complete</button>}<button className="quiet" onClick={() => void controlTask(item.task_id, "snoozed")}>Snooze</button><button className="quiet" onClick={() => prepareSchedule(item.title)}>Schedule</button><button className="quiet" onClick={() => void controlTask(item.task_id, "archived")}>Dismiss</button></div></div>)}<button className="quiet" onClick={() => setActive("Inbox")}>Open Inbox</button></article>
          <article className="card"><p className="eyebrow">Meeting lifecycle</p><h3>{localState?.meetingEvidence[0]?.title || "No recent authorized Zoom evidence"}</h3><p>{localState?.meetingEvidence[0] ? `${localState.meetingEvidence[0].confidence_state} · ${localState.meetingEvidence[0].source_timestamp?.slice(0, 10) || localState.meetingEvidence[0].indexed_at.slice(0, 10)}` : "The meeting view stays empty rather than inventing one."}</p><div className="focus-controls"><button className="quiet" onClick={() => startMeetingWorkflow("before")}>Before</button><button className="quiet" onClick={() => startMeetingWorkflow("after")}>After</button><button className="quiet" onClick={() => startMeetingWorkflow("absent")}>I was absent</button><button className="quiet" onClick={() => void loadProjection("end-of-day")}>Draft DLOA · local only</button></div>{localState?.meetingEvidence[0] && <><small>Authorized Zoom evidence · {localState.meetingEvidence[0].account_id || "account recorded"}</small><details className="meeting-followup"><summary>Add a reviewed follow-up</summary><input value={meetingFollowupTitle} onChange={(event) => setMeetingFollowupTitle(event.target.value)} placeholder="Exact follow-up for Jarvis Inbox"/><select aria-label="Meeting follow-up project" value={meetingProjectId} onChange={(event) => setMeetingProjectId(event.target.value)}><option value="">Inbox only</option>{localState.projects.map((project) => <option key={project.project_id} value={project.project_id}>{project.name}</option>)}</select><button onClick={() => void applyMeetingFollowup()} disabled={!meetingFollowupTitle.trim()}>Add locally with meeting evidence</button></details></>}</article>
        </section>
        <section className="grid">
          <article className="card"><p className="eyebrow">Today</p><h3>Attention brief</h3><p>Source-backed priorities, meetings, blockers, and people waiting—without mixing contexts.</p><button onClick={() => { setPrompt("Give me my source-backed attention brief for today."); setActive("Chat"); }}>Open brief</button></article>
          <article className="card"><p className="eyebrow">Projects</p><h3>Resume intelligently</h3><p>Continue from Codex, GitHub, decisions, tasks, and verified evidence.</p><button onClick={() => { setPrompt("Resume my most relevant active project with sources and next three actions."); setActive("Chat"); }}>Resume project</button></article>
          <article className="card"><p className="eyebrow">Awareness</p><h3>Look once</h3><p>Explicit selected-area understanding. No continuous capture or retained screenshot.</p><button onClick={lookAtArea}>Select area</button></article>
        </section>
        <section className="card intelligence-strip">
          <div><p className="eyebrow">Background intelligence</p><strong>{background === "off" ? "Off" : background === "login" ? "While logged in" : "While Jarvis runs"}</strong><small>{localState?.proactive?.source_count ?? 0} bounded ledger sources in the current brief</small></div>
          <div className="focus-controls"><button className="quiet" onClick={() => void loadProjection("start-of-day")}>Start day</button><button className="quiet" onClick={() => void loadProjection("pre-meeting")}>Pre-meeting</button><button className="quiet" onClick={() => void loadProjection("end-of-day")}>End day / DLOA</button><button className="quiet" onClick={() => void loadProjection("absence-return")}>Catch up</button>{!currentFocus && <><button className="quiet" onClick={() => void startFocus(30)}>Focus 30m</button><button className="quiet" onClick={() => void startFocus(60)}>60m</button><button className="quiet" onClick={() => void startFocus(90)}>90m</button></>}{currentFocus && <><button className="quiet" onClick={() => void controlFocus(currentFocus.focus_id, currentFocus.mode === "paused" ? "resume" : "pause")}>{currentFocus.mode === "paused" ? "Resume focus" : "Pause focus"}</button><button className="danger" onClick={() => void stopFocus(currentFocus.focus_id)}>Stop focus</button></>}</div>
        </section>
        {projection && <section className="card surface"><p className="eyebrow">Ledger projection · local only</p><pre>{String((projection.dloa as { text?: string } | undefined)?.text ?? JSON.stringify(projection, null, 2))}</pre><button className="quiet" onClick={() => setProjection(null)}>Dismiss</button></section>}
        {currentFocus && <section className="card focus-timeline">
          <p className="eyebrow">Focus {currentFocus.mode === "paused" ? "paused" : "active"} · visible metadata only</p>
          <strong>{currentFocus.observations?.[0]?.app_id ?? "Waiting for the first app sample"}</strong>
          <small>Profile/domain remain unknown unless proven; Jarvis never guesses. Screenshots retained: 0.</small>
        </section>}
        {localNotice && <p className="notice">{localNotice}</p>}
        <section className="card state-strip"><strong>{localState?.ledgerCount ?? "—"}</strong><span>ledger entries in {contextLabel}</span><strong>{localState?.openTaskCount ?? "—"}</strong><span>open local tasks</span><strong>{localState?.budget?.level ?? "checking"}</strong><span>model budget</span></section>
        <section className="card capability-summary"><div><p className="eyebrow">Capability health</p><strong>{health.state === "ready" ? "Core ready" : "Needs attention"}</strong><small>{health.backend} · build {health.buildCommit?.slice(0, 8) || "development"}</small></div><div><strong>{Object.keys(localState?.integrations ?? {}).length}</strong><small>registered read-only evidence sources</small></div><div><strong>{personalActions?.connected && personalActions.refreshable ? "Refreshable" : "Check grant"}</strong><small>Personal Google exact-scope grant</small></div><button className="quiet" onClick={() => setActive("Diagnostics")}>Diagnostics</button></section>
      </>}

      {active === "Inbox" && <section className="card surface">
        <p className="eyebrow">Jarvis Inbox</p><h2>Detected → confirmed → planned → completed → verified</h2>
        <p>Requests, promises, waiting-on items, deadlines, blockers, and uncertain obligations stay in one context-scoped triage view. Jarvis suggests; it does not invent ownership or due dates.</p>
        <div className="inbox-create"><input value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} placeholder="Add a personal task or open loop"/><select aria-label="Inbox item type" value={taskType} onChange={(event) => setTaskType(event.target.value)}><option value="personal-task">Task</option><option value="open-loop">Open loop</option><option value="reminder">Reminder</option><option value="meeting-task">Meeting task</option><option value="blocker">Blocker</option></select><input type="datetime-local" aria-label="Optional local due time" value={taskDue} onChange={(event) => setTaskDue(event.target.value)}/><button onClick={() => void createInboxTask()} disabled={!taskTitle.trim()}>Add locally</button></div>
        <div className="inbox-groups">{["blocker", "meeting-task", "open-loop", "personal-task", "reminder"].map((kind) => {
          const items = localState?.inboxItems.filter((item) => item.task_type === kind) ?? [];
          if (!items.length) return null;
          return <section key={kind}><h3>{kind.replace("-", " ")} <span>{items.length}</span></h3>{items.map((item) => <article key={item.task_id}><strong>{item.title}</strong><span>{item.status} · owner {item.owner} · {(item.confidence * 100).toFixed(0)}%</span>{item.waiting_on && <p>Waiting on {item.waiting_on}</p>}{item.due_at && <p>Due {item.due_at.slice(0, 16)}</p>}<div className="focus-controls">{!['planned','in-progress','completed','verified'].includes(item.status) && <button className="quiet" onClick={() => void controlTask(item.task_id, "planned")}>Plan</button>}{item.status !== "in-progress" && !['completed','verified'].includes(item.status) && <button className="quiet" onClick={() => void controlTask(item.task_id, "in-progress")}>Start</button>}{item.task_type !== "commitment" && !['completed','verified'].includes(item.status) && <button className="quiet" onClick={() => void controlTask(item.task_id, "completed")}>Complete</button>}<button className="quiet" onClick={() => void controlTask(item.task_id, "snoozed")}>Snooze 1 day</button><button className="quiet" onClick={() => void controlTask(item.task_id, "archived")}>Archive</button></div></article>)}</section>;
        })}</div>
        <h3>Sourced commitments</h3>
        <div className="setting"><input value={commitmentTitle} onChange={(event) => setCommitmentTitle(event.target.value)} placeholder="Exact commitment to track"/><span className="pill">Evidence required</span></div>
        {localState?.commitments?.map((item) => <article key={item.task_id}>
          <strong>{item.title}</strong><span>{item.status} · {item.evidence_ids.length} evidence link(s)</span>
          {item.status === "open" && <button className={selectedCommitment === item.task_id ? "danger" : "quiet"} onClick={() => setSelectedCommitment(selectedCommitment === item.task_id ? null : item.task_id)}>{selectedCommitment === item.task_id ? "Cancel completion" : "Select for completion proof"}</button>}
        </article>)}
        <details><summary>Activity evidence for opening or verifying a commitment</summary><div className="item-list">{localState?.recentLedger?.map((item) => <article key={item.entry_id}>
          <strong>{item.summary}</strong><span>{item.local_date} · {item.confidence_state}</span>
          <p>{item.kind} · actor {item.actor_state} · fresh {item.freshness_at.slice(0, 10)}</p>
          {item.evidence_ids[0] && (selectedCommitment
            ? <button className="quiet" onClick={() => void completeCommitment(item.evidence_ids[0])}>Use as completion proof</button>
            : <button className="quiet" onClick={() => void openCommitment(item.evidence_ids[0])}>Open commitment from this evidence</button>)}
        </article>)}</div></details>
        {localNotice && <small>{localNotice}</small>}
      </section>}

      {active === "Actions" && <section className="card surface">
        <p className="eyebrow">Action firewall</p><h2>External writes remain fail-closed</h2>
        <p>Ask naturally for simple personal events or unsent drafts. Company/client writes are unavailable, Gmail sending is absent, and ambiguous requests stop for review.</p>
        <span className="pill">Global kill switch on</span>
        <h3>Personal action acceptance</h3>
        <div className="setting"><span>{personalActions?.connected ? `Connected · ${personalActions.account}` : "Separate personal grant not connected"}<small>{personalActions?.mode === "auto-explicit" ? "Auto Explicit Request · ask naturally in Chat" : "Calendar owned-events and Gmail compose scopes only"} · Gmail send is structurally absent</small></span><button className="quiet" onClick={() => void refreshPersonalActions()}>Refresh</button>{!personalActions?.connected && <button onClick={() => void connectPersonalActions()}>Connect personal actions</button>}{personalActions?.connected && <button className={personalActions.personalCapabilitiesEnabled ? "danger" : "quiet"} onClick={() => void togglePersonalActions(!personalActions.personalCapabilitiesEnabled)}>{personalActions.personalCapabilitiesEnabled ? "Turn personal actions off" : "Enable Auto Explicit Request"}</button>}</div>
        {personalActions?.connected && !personalActions.personalCapabilitiesEnabled && <p className="notice">The grant is stored owner-only, but execution remains off until you visibly enable these two personal capabilities.</p>}
        {personalActions?.personalCapabilitiesEnabled && <article className="navigation-preview"><strong>Use natural language in Chat</strong><span>Unambiguous personal requests run immediately; ambiguous or consequential requests preview.</span><p>Try: Create a personal calendar event called Focus block tomorrow at 3 PM for 30 minutes.</p><p>Or: Create an unsent personal Gmail draft with subject Follow up and body Thanks for your time today.</p></article>}
        {personalActions?.resources?.filter((item) => item.state === "active").map((item) => <article className="navigation-preview" key={item.resource_id}><strong>{item.capability_id === "personal-calendar-owned" ? "Jarvis-created calendar event" : "Jarvis-created unsent draft"}</strong><span>{item.capability_id === "personal-calendar-owned" ? String(item.metadata?.summary || "Personal event") : "Unsent Gmail draft"} · {item.updated_at.slice(0, 16)}</span>{item.capability_id === "personal-calendar-owned" && <button className="danger" onClick={() => { setPersonalResult({ providerId: item.provider_id, resourceKind: "calendar-event", undoAvailable: true }); void undoCalendarEvent(item.provider_id); }}>Undo this exact event</button>}</article>)}
        {personalActions?.personalCapabilitiesEnabled && <button className="quiet" onClick={() => setShowAdvancedActions(!showAdvancedActions)}>{showAdvancedActions ? "Hide advanced exact preview" : "Advanced exact preview"}</button>}
        {personalActions?.personalCapabilitiesEnabled && showAdvancedActions && <div className="permission-matrix item-list">
          <article><strong>Create one simple personal event</strong><span>Personal · primary calendar · Profile 1</span><input value={eventTitle} onChange={(event) => setEventTitle(event.target.value)} placeholder="Exact event title"/><div className="setting"><input type="datetime-local" value={eventStart} onChange={(event) => setEventStart(event.target.value)}/><select aria-label="Event duration" value={eventDuration} onChange={(event) => setEventDuration(event.target.value)}><option value="15">15 minutes</option><option value="30">30 minutes</option><option value="60">60 minutes</option></select></div><p>10-minute popup · blue color · no attendee · no recurrence · no invitations</p><button onClick={() => void previewCalendarEvent()}>Preview event</button></article>
          <article><strong>Create one unsent personal draft</strong><span>Personal Gmail · Profile 1 · sending absent</span><input value={draftRecipient} onChange={(event) => setDraftRecipient(event.target.value)} placeholder="One recipient or leave blank"/><input value={draftSubject} onChange={(event) => setDraftSubject(event.target.value)} placeholder="Exact subject"/><textarea value={draftBody} onChange={(event) => setDraftBody(event.target.value)} rows={4}/><button onClick={() => void previewGmailDraft()}>Preview unsent draft</button></article>
        </div>}
        {personalPreview && <article className="navigation-preview"><strong>Exact personal action preview</strong><span>{personalPreview.capabilityId} · Personal · Profile 1</span><span>Expires {new Date(personalPreview.expiresAt).toLocaleTimeString()}</span>{personalPreview.calendarStyleApplied && <span>Owner-reviewed Calendar style applied</span>}{Boolean(personalPreview.conflicts?.length) && <p className="notice">Conflict warning: {personalPreview.conflicts?.length} existing calendar item(s) overlap. This preview requires your exact confirmation.</p>}<pre>{JSON.stringify(personalPreview.payload, null, 2)}</pre><span>Preview hash {personalPreview.previewHash}</span><button onClick={() => void executePersonalPreview()}>{personalPreview.capabilityId.includes("calendar") ? "Create exactly this event" : "Create this unsent draft"}</button><button className="quiet" onClick={() => setPersonalPreview(null)}>Cancel</button></article>}
        {personalResult?.undoAvailable && !personalActions?.resources?.some((item) => item.provider_id === personalResult.providerId && item.state === "active") && <article className="navigation-preview"><strong>Event created by Jarvis</strong><span>{personalResult.providerId}</span><button className="danger" onClick={() => void undoCalendarEvent()}>Undo this exact event</button></article>}
        <button className="quiet" onClick={() => setShowActionPolicy(!showActionPolicy)}>{showActionPolicy ? "Hide safety details" : "Safety details"}</button>
        {showActionPolicy && <><h3>What Jarvis can safely do</h3>
        <div className="item-list permission-matrix">
          <article><strong>Personal Calendar</strong><span>Ask naturally · selected calendar only</span><p>A direct, unambiguous request can create a simple event immediately. Attendees, recurrence, work calendars, or ambiguity stop for review; only Jarvis-created events can be undone.</p></article>
          <article><strong>Personal Gmail drafts</strong><span>Ask naturally · unsent drafts only</span><p>A direct request can create and open an unsent draft. Gmail sending is absent, and Jarvis can update only a draft it previously created.</p></article>
          <article><strong>Work Google accounts</strong><span>Read-only · write tools absent</span><p>Work Gmail and Calendar write capabilities are not registered. The interface cannot widen scopes or substitute the personal account.</p></article>
          <article><strong>Owner authorization</strong><span>Local exact intent required</span><p>Retrieved email, Slack, web, meeting, or document text is untrusted evidence and cannot approve an action. A changed target, permission snapshot, preview hash, or expired request fails closed.</p></article>
          <article><strong>Guided navigation</strong><span>Exact preview before opening</span><p>Fixed profile, account, domain, context, and read-only action are shown first. No arbitrary URL, typing, submission, download, settings change, or generic computer control exists.</p></article>
        </div>
        <div className="item-list">{localState?.actionPreviews?.map((item) => <article key={item.proposal_id}>
          <strong>{item.state}</strong><span>{item.updated_at.slice(0, 10)}</span><p>Preview hash {item.preview_hash.slice(0, 16)}… · not executed here</p>
        </article>)}</div></>}
      </section>}

      {active === "Learning" && <section className="card surface">
        <p className="eyebrow">Inspectable learning</p><h2>Memories, preferences, and workflow proposals</h2>
        <p>Learning is context-scoped and reversible. Security policy, credentials, permissions, and write destinations cannot be self-modified.</p>
        <div className="item-list">{localState?.learningItems?.length ? localState.learningItems.map((item) => <article key={item.memory_id}>
          <strong>{item.statement}</strong><span>{item.status} · {(item.confidence * 100).toFixed(0)}%</span><p>{item.namespace} · {item.created_at.slice(0, 10)}</p><div className="focus-controls"><button className="quiet" onClick={() => void reviewMemory(item.memory_id, "confirmed")}>Keep</button><button className="quiet" onClick={() => void reviewMemory(item.memory_id, "superseded")}>Archive</button><button className="quiet" onClick={() => void reviewMemory(item.memory_id, "rejected")}>Reject</button></div>
        </article>) : <p>No local learned item is stored in this context yet.</p>}</div>
      </section>}

      {active === "Chat" && <section className="chat-layout">
        <div className="conversation card" ref={conversationViewportRef} onScroll={(event) => {
          if (currentSessionIdRef.current) scrollPositionsRef.current[currentSessionIdRef.current] = event.currentTarget.scrollTop;
        }}>
          {conversationContent.length > 0 && <div className="message-stream">{conversationContent.map((item) => { const content = item.content ?? ""; const cards = sourceCards(content); const persistedProgress = item.display_metadata?.progress ?? []; return <article className={`message ${item.role}`} key={String(item.id)}>
            <small>{item.role === "user" ? "You" : "Jarvis"}</small><div className="message-copy">{withoutRawSourceUrls(content)}</div>
            {cards.length > 0 && <div className="source-cards" aria-label="Answer sources">{cards.map((card) => <article className="source-card" key={card.url}><span><strong>{card.label}</strong><small>{card.host} · {sourceEvidenceStatus.get(card.url) ?? `${item.display_metadata?.context ?? contextLabel} · cited · freshness unknown`}</small></span>{card.openable ? <button className="quiet" onClick={() => void openEvidenceSource(card.url)}>Open source</button> : <span className="pill" title="This host is not in Jarvis's reviewed source-opening allowlist">View in bounded research</span>}</article>)}</div>}
            {persistedProgress.length > 0 && <details className="message-progress"><summary>Source progress · {persistedProgress.length} step(s)</summary>{persistedProgress.map((line) => <p key={line}>{line}</p>)}</details>}
          </article>; })}</div>}
          {technicalMessages.length > 0 && <details className="technical-details"><summary>Technical details · {technicalMessages.length} tool event(s)</summary>{technicalMessages.map((item) => <pre key={String(item.id)}>{item.tool_name ? `${item.tool_name}\n` : ""}{item.content}</pre>)}</details>}
          {progress.length > 0 && <div className="progress">{progress.map((line, index) => <div key={`${line}-${index}`}><span className={line.startsWith("Completed") ? "done" : "working"}/>{line}</div>)}</div>}
          {voiceTranscript && <div className="live-transcript"><small>Live transcript</small>{voiceTranscript}</div>}
          {speechStatus !== "idle" && <div className={`speech-status ${speechStatus}`} role="status">{speechStatus === "speaking" ? "Speaking · Talk or Stop speaking interrupts immediately" : speechStatus === "stopped" ? "Speech stopped · no replay scheduled" : "Spoken reply completed"}</div>}
          {answer && (busy || !conversationContent.some((item) => item.role === "assistant" && item.content === answer)) ? <div className="answer">{answer}</div> : conversationContent.length === 0 && <div className="empty">Ask naturally. Jarvis will show what it checks and cite the result.</div>}
          {conversationContent.length > 3 && <button className="quiet jump-latest" onClick={() => { if (conversationViewportRef.current) conversationViewportRef.current.scrollTop = conversationViewportRef.current.scrollHeight; }}>Jump to latest</button>}
        </div>
        <form className="composer" onSubmit={submit}>
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="What needs your attention?" rows={2}/>
          <div><select aria-label="Model routing" value={modelOverride} onChange={(event) => setModelOverride(event.target.value as typeof modelOverride)}><option value="auto">Model · Auto</option><option value="routine">Flash</option><option value="difficult">Pro</option><option value="review">Pro + Terra review</option></select><button type="button" className={recording ? "danger" : "quiet"} onClick={() => void toggleVoice()}>{recording ? "Done speaking" : "Talk"}</button>{voiceDeliveryFailed && voiceTranscript && <button type="button" onClick={() => void retryVoiceDelivery()}>Retry delivery</button>}{voiceRetryAvailable && lastRecordingRef.current && <button type="button" className="quiet" onClick={() => void transcribeBlob(lastRecordingRef.current!)}>Retry transcription</button>}{voiceRetryAvailable && voiceTranscript && <button type="button" className="quiet" onClick={editVoiceTranscript}>Edit transcript</button>}{voiceRetryAvailable && (voiceTranscript || lastRecordingRef.current) && <button type="button" className="quiet" onClick={discardVoiceRecording}>Discard</button>}<button type="button" className="quiet" onClick={stopSpeaking}>Stop speaking</button>{busy ? <button type="button" className="danger" onClick={cancel}>Cancel</button> : <button type="submit">Ask Jarvis</button>}</div>
        </form>
      </section>}

      {["Projects", "Missions", "Radars", "Teach Jarvis", "Decisions"].includes(active) && <section className="card surface">
        <p className="eyebrow">{active}</p><h2>{active === "Teach Jarvis" ? "Teach Jarvis a bounded capability" : `Your ${active.toLowerCase()}`}</h2>
        <p>{active === "Projects" && "Living objectives, verified progress, decisions, blockers, and the next three actions."}
          {active === "Missions" && "Persistent goals with completion contracts, evidence, questions, and review cadence."}
          {active === "Radars" && "Meaningful-change monitoring from approved sources—digest-first, never notification spam."}
          {active === "Teach Jarvis" && "Describe a workflow. Jarvis validates tools, context, permissions, dry-runs it, and cannot widen its own authority."}
          {active === "Decisions" && "Consequential choices, alternatives, reasons, evidence, and later outcomes."}</p>
        {active === "Projects" && <div className="item-list project-list">{localState?.projects.length ? localState.projects.map((item) => <article key={item.project_id}><strong>{item.name}</strong><span>{item.phase} · {item.lifecycle} · fresh {item.freshness_at?.slice(0, 10) || "unknown"}</span><p>{item.objective}</p><p><b>Completion contract:</b> {item.completion_contract || "Not yet defined"}</p>{(item.recent_progress ?? []).length > 0 && <details open><summary>Recent verified progress</summary>{item.recent_progress.map((progressItem) => <p key={progressItem.entry_id}>{progressItem.local_date} · {progressItem.summary} · {progressItem.confidence_state}</p>)}</details>}{(item.decisions ?? []).length > 0 && <details><summary>Important decisions · {item.decisions.length}</summary>{item.decisions.map((decision) => <p key={decision.decision_id}><b>{decision.decision}</b> — {decision.reasoning}</p>)}</details>}{(item.blockers ?? []).length > 0 && <details open><summary>Blockers</summary>{item.blockers.map((blocker) => <p key={blocker}>{blocker}</p>)}</details>}{(item.next_actions ?? []).length > 0 && <details open><summary>Next actions</summary>{item.next_actions.slice(0, 3).map((next) => <p key={next}>{next}</p>)}</details>}{(item.resources ?? []).length > 0 && <details><summary>Relevant resources</summary>{item.resources.map((resource) => <p key={resource}>{resource}</p>)}</details>}{item.latest_snapshot && <details><summary>Last saved place · {item.latest_snapshot.created_at.slice(0, 16)}</summary><pre>{JSON.stringify(item.latest_snapshot.state, null, 2)}</pre></details>}<button className="quiet" onClick={() => setCheckpointProjectId(checkpointProjectId === item.project_id ? null : item.project_id)}>Save My Place</button>{checkpointProjectId === item.project_id && <div className="checkpoint-form"><textarea value={checkpointSummary} onChange={(event) => setCheckpointSummary(event.target.value)} placeholder="Where things stand now"/><input value={checkpointNext} onChange={(event) => setCheckpointNext(event.target.value)} placeholder="Exact next step"/><button onClick={() => void saveCheckpoint(item.project_id)}>Save evidence-backed checkpoint</button></div>}</article>) : <p>No living project is stored in this context yet.</p>}</div>}
        {active === "Missions" && <div className="item-list">{localState?.missions.map((item) => <article key={item.mission_id}><strong>{item.goal}</strong><span>{item.status} · {item.lifecycle}</span><p>{item.completion_contract}</p></article>)}</div>}
        {active === "Radars" && <div className="item-list">{localState?.radars.map((item) => <article key={item.radar_id}><strong>{item.question}</strong><span>{item.cadence} · {item.notification_policy}</span><button className="quiet" onClick={() => void evaluateRadar(item.radar_id)}>Check now · approved evidence only</button></article>)}</div>}
        {active === "Teach Jarvis" && <div className="item-list">{localState?.capabilities.map((item) => <article key={item.capability_id}><strong>{item.name}</strong><span>{item.kind} · {item.status}</span><div className="focus-controls"><button className="quiet" onClick={() => void capabilityControl(item.capability_id, "useful")}>Useful · shadow</button><button className="quiet" onClick={() => void capabilityControl(item.capability_id, "not-useful")}>Not useful · disable</button>{item.status === "disabled" || item.status === "archived" ? <button className="quiet" onClick={() => void capabilityControl(item.capability_id, "draft")}>Restore draft</button> : <button className="quiet" onClick={() => void capabilityControl(item.capability_id, "disabled")}>Disable</button>}<button className="quiet" onClick={() => void capabilityControl(item.capability_id, "archived")}>Archive</button></div></article>)}</div>}
        {active === "Teach Jarvis" && localState?.automationProposals?.map((item) => <article className="automation-proposal" key={item.proposal_id}><strong>Automation opportunity: {item.signature}</strong><span>{item.status} · {item.occurrence_count} observations · ~{item.estimated_time_saved_minutes.toFixed(0)} minutes potential savings</span><div className="focus-controls"><button className="quiet" onClick={() => void recordAutomationOutcome(item.proposal_id, "accepted")}>Accept</button><button className="quiet" onClick={() => void recordAutomationOutcome(item.proposal_id, "rejected")}>Reject</button><button className="quiet" onClick={() => void recordAutomationOutcome(item.proposal_id, "undone")}>Undo</button></div></article>)}
        {["Missions", "Radars", "Teach Jarvis"].includes(active) && <div className="local-create">
          <input value={localTitle} onChange={(event) => setLocalTitle(event.target.value)} placeholder={active === "Missions" ? "Goal" : active === "Radars" ? "Question to watch" : "Capability name"}/>
          <textarea value={localDetails} onChange={(event) => setLocalDetails(event.target.value)} placeholder={active === "Missions" ? "What proves this is complete?" : active === "Radars" ? "What would count as a meaningful change?" : "Describe the low-risk workflow"}/>
          {active === "Teach Jarvis" && <label className="setting"><span>Requires new code or integration <small>Generate a Codex spec only; never self-modify or deploy</small></span><input aria-label="Requires new code or integration" type="checkbox" checked={capabilityRequiresCode} onChange={(event) => setCapabilityRequiresCode(event.target.checked)}/></label>}
          <button onClick={() => void createLocal(active === "Missions" ? "mission" : active === "Radars" ? "radar" : "capability")}>Validate and save locally</button>
          {active === "Teach Jarvis" && codexSpec && <article className="navigation-preview"><strong>Codex-ready implementation specification</strong><span>Context: {String(codexSpec.context_id)}</span><span>Requested tools: {Array.isArray(codexSpec.tools) ? codexSpec.tools.join(", ") : "none"}</span><span>No code change · no activation · no deployment</span><pre>{JSON.stringify(codexSpec, null, 2)}</pre></article>}
          {localNotice && <small>{localNotice}</small>}
        </div>}
        {active === "Decisions" && <><div className="item-list">{localState?.recentDecisions.length ? localState.recentDecisions.map((item) => <article key={item.decision_id}><strong>{item.decision}</strong><span>{item.decided_at.slice(0, 10)}</span><p>{item.reasoning}</p>{item.actual_outcome ? <p><b>Actual outcome:</b> {item.actual_outcome}</p> : <div className="checkpoint-form"><input value={decisionOutcome} onChange={(event) => setDecisionOutcome(event.target.value)} placeholder="What actually happened?"/><button onClick={() => void saveDecisionOutcome(item.decision_id)}>Record outcome</button></div>}</article>) : <p>No decision is recorded in this context yet.</p>}</div><div className="local-create"><input value={decisionText} onChange={(event) => setDecisionText(event.target.value)} placeholder="Decision"/><textarea value={decisionReason} onChange={(event) => setDecisionReason(event.target.value)} placeholder="Reasoning and expected result"/><button onClick={() => void createDecision()}>Record with current evidence</button>{localNotice && <small>{localNotice}</small>}</div></>}
      </section>}

      {active === "Activity" && <section className="card surface"><p className="eyebrow">Activity</p><h2>Source-backed work ledger</h2><p>Immutable evidence remains separate from memory and tasks. Content is context-scoped, dated, confidence-labelled, and never treated as an instruction.</p><div className="item-list">{localState?.recentLedger.map((item) => <article key={item.entry_id}><strong>{item.summary}</strong><span>{item.local_date} · {item.confidence_state}</span><p>{item.kind} · actor {item.actor_state} · {item.evidence_ids.length} provenance link(s)</p></article>)}</div></section>}

      {active === "Diagnostics" && <section className="settings-grid"><article className="card diagnostics"><h3>Runtime diagnostics</h3><dl><div><dt>Jarvis core</dt><dd>{health.state} · {health.backend}</dd></div><div><dt>Hermes</dt><dd>{health.hermesVersion}</dd></div><div><dt>Build</dt><dd>{health.buildCommit || "development"}</dd></div><div><dt>Runtime marker</dt><dd>{health.runtimeMarker ? "verified" : "missing"}</dd></div><div><dt>Default route</dt><dd>{health.modelRoute} · connectivity checked when used</dd></div><div><dt>Budget</dt><dd>{health.budget}</dd></div><div><dt>Codex checkpoint</dt><dd>{localState?.codexSync.last_updated_at?.slice(0, 16) || "not yet recorded"}</dd></div><div><dt>Personal Google</dt><dd>{personalActions?.connected ? personalActions.refreshable ? `connected · refreshable · access token ${Math.max(0, Math.floor((personalActions.seconds_remaining ?? 0) / 60))}m` : "connected · reauthorization required" : "not connected · reauthorization required"}</dd></div></dl><div className="repair-row"><button className="quiet" disabled={repairingCapability !== null} onClick={() => void repairCapability("backend")}>Restart owned backend</button><button className="quiet" disabled={repairingCapability !== null} onClick={() => void repairCapability("personal-google")}>Refresh Google grant</button><button className="quiet" disabled={repairingCapability !== null} onClick={() => void repairCapability("local-state")}>Reload local state</button></div><p>Core readiness does not claim every provider is live. Connector registration and model routes below are checked on demand. No repair can add tools, widen OAuth scopes, change accounts, or enable external writes.</p>{localNotice && <small>{localNotice}</small>}</article><article className="card diagnostics"><h3>Capability health</h3><div className="health-list"><div><span>Personal Calendar</span><strong>{personalActions?.connected && personalActions.personalCapabilitiesEnabled ? "connected · create enabled" : "needs attention"}</strong></div><div><span>Personal Gmail</span><strong>{personalActions?.connected && personalActions.personalCapabilitiesEnabled ? "read · draft enabled · send blocked" : "needs attention"}</strong></div><div><span>Work Google</span><strong>read only</strong></div><div><span>Inside Success Slack</span><strong>read only</strong></div><div><span>GitHub personal / company</span><strong>read only</strong></div><div><span>Zoom</span><strong>{localState?.integrations.zoom_readonly === "read-only" ? "4 reviewed reads registered" : "not registered"}</strong></div><div><span>ChatGPT backfill</span><strong>{localState?.backfillStats.chatgpt_export?.count ?? 0} records</strong></div><div><span>Gemini backfill</span><strong>{localState?.backfillStats.gemini_export?.count ?? 0} records</strong></div><div><span>Codex evidence</span><strong>{localState?.backfillStats.codex?.count ?? 0} records</strong></div></div></article><article className="card diagnostics"><h3>Model routes</h3><p>Configured routes are policy, not a continuous provider-health claim. Each run reports its actual success or failure. Sol is builder-only and never appears here.</p><div className="health-list">{(localState?.modelRoutes ?? []).map((route) => <div key={route.id}><span>{route.id} · {route.purpose}</span><strong>{route.enabled ? `${route.provider} · ${route.model}` : "disabled"}</strong></div>)}</div><p>Monthly budget: ${localState?.budget.spent_usd.toFixed(2) ?? "—"} of ${localState?.budget.hard_usd.toFixed(2) ?? "—"} hard limit.</p></article><article className="card diagnostics"><h3>Evidence source registry</h3><p>These entries prove reviewed read-only registration, not a fresh provider query. A task reports live source failures separately.</p><div className="health-list">{Object.entries(localState?.integrations ?? {}).map(([name, status]) => <div key={name}><span>{name.replaceAll("_", " ")}</span><strong>{status}</strong></div>)}</div></article></section>}

      {active === "Settings" && <section className="settings-grid">
        <article className="card"><h3>Activation</h3><p><kbd>⌘</kbd><kbd>⇧</kbd><kbd>Space</kbd> opens Quick Entry.</p><p><kbd>⌃</kbd><kbd>⌥</kbd><kbd>Space</kbd> starts Talk to Jarvis.</p><div className="setting"><span>Wake phrase <small>Off by default · local only</small></span><button disabled>Off</button></div></article>
        <article className="card"><h3>Voice recovery</h3><p>Run a private diagnostic rejection to prove a failed delivery preserves the transcript and exposes Retry delivery, Edit, and Discard. It records and submits nothing until Retry is chosen.</p><button className="quiet" onClick={runVoiceRecoveryDiagnostic}>Stage recovery check</button></article>
        <article className="card"><h3>Spoken interruption</h3><p>Play a harmless local passage and listen only for an explicit Stop command. No dictation or model request is submitted.</p><button className="quiet" onClick={runSpokenStopDiagnostic}>Test spoken Stop</button></article>
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
        </select>{navigationDestination === "public-search" && <input value={navigationQuery} onChange={(event) => { setNavigationQuery(event.target.value); setNavigationPlan(null); setGuidedRead(null); }} placeholder="Public search query"/>}<div className="setting"><button className="quiet" onClick={() => void previewNavigation()}>Preview exact navigation</button></div>{navigationPlan && <div className="navigation-preview"><strong>{navigationPlan.action} · {navigationPlan.label}</strong><span>{navigationPlan.profile} · {navigationPlan.account}</span><span>{navigationPlan.domain} · {navigationPlan.context}</span><span>No mutation</span><button onClick={() => void openNavigation()}>Open this exact page</button>{navigationPlan.destination === "public-search" && <button onClick={() => void readGuidedPublicResults()}>Read cited results in Jarvis</button>}<button className="quiet" onClick={() => setNavigationPlan(null)}>Cancel</button></div>}{guidedRead && <div className="guided-reader" tabIndex={0}><strong>Scrollable public evidence · no account session</strong>{guidedRead.results.map((item) => <article key={item.content_hash}><strong>{item.title}</strong><p>{item.excerpt}</p><small>{new URL(item.url).hostname} · {item.retrieved_at.slice(0, 10)}{item.injection_flags.length ? " · prompt-injection warning" : ""}</small></article>)}</div>}{localNotice && <small>{localNotice}</small>}</article>
      </section>}
    </main>
  </div>;
}

export default App;
