# Voice, Screen, Overlay, and UX

## User experience

Hermes Desktop should feel like one product. Provider details and connectors are configuration, not separate apps Syed must operate daily.

## Voice stack

Initial candidate:

- wake/manual activation: Hermes-supported local wake-word mechanism;
- STT: Groq Whisper or the current fastest economical Hermes-supported provider;
- TTS: Edge TTS;
- fallback: another verified low-cost provider or local option if quality/availability requires it.

Benchmark real conditions:

- Pakistani English accent;
- names such as Syed, Mitchell, Inside Success;
- noisy room;
- short commands and long dictation;
- latency;
- correction rate;
- RAM/CPU use;
- monthly cost.

Do not choose ElevenLabs by default.

## Wake and interaction

Support:

- wake phrase and keyboard/menu activation;
- push-to-talk option;
- interruption/barge-in;
- cancel;
- repeat;
- “look at my screen” explicit command;
- “don’t save this”;
- “save this as a decision/task/memory”;
- “show sources.”

The microphone may listen locally for a wake word, but should not continuously stream audio to a provider before activation.

## Floating overlay

Always-on-top, compact, dismissible.

States:

- idle/listening;
- heard transcript;
- processing;
- checking a named source;
- awaiting approval;
- speaking;
- error/offline.

Content:

- recognized user text;
- confidence/correction affordance;
- streamed assistant text;
- source/context badges;
- action target;
- approve/edit/cancel;
- mute/interruption;
- expand to full Hermes Desktop.

The overlay must not obscure sensitive content during screen capture or accidentally display company/client information on another screen. Include a privacy/minimize mode.

## Personality

Use a durable personality configuration such as the current Hermes personality/SOUL mechanism.

Normal mode:

- concise;
- dry/sarcastic when appropriate;
- confident only when evidence supports it;
- willing to push back.

Serious mode:

- no sarcasm;
- explicit sources and assumptions;
- conservative action posture;
- professional wording.

## Screen understanding

- screen capture only after explicit activation;
- capture the relevant display/window where possible;
- show capture indicator;
- minimize retention;
- redact or warn about secrets;
- use GPT-5.6 Luna baseline for image understanding;
- do not grant computer-control permission solely for capture.

## Error behavior

Never remain silently “thinking.” Show:

- source unavailable;
- authentication expired;
- rate limited;
- insufficient evidence;
- ambiguous context;
- approval needed;
- cost limit reached.

## Accessibility and controls

- keyboard shortcuts;
- readable text sizing;
- transcript copy;
- clear focus for approve/cancel;
- no accidental approval through ordinary speech;
- optional confirmation phrase for voice approval, but consequential actions require visual confirmation.
