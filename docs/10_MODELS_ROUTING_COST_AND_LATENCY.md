# Models, Routing, Cost, and Latency

## Build-time versus runtime models

Codex uses **GPT-5.6 Sol at Medium reasoning** for implementation. The finished Hermes assistant uses the direct-API runtime baseline below. Do not interpret the Codex model as permission to route routine Hermes traffic through Sol.


## Approved baseline

Use direct provider API keys.

| Work class | Baseline |
|---|---|
| Routine conversation, classification, extraction, routing, ordinary tool use | DeepSeek V4 Flash |
| Difficult reasoning and important analysis | DeepSeek V4 Pro, after current support is verified |
| Screenshots and image understanding | GPT-5.6 Luna |
| Rare high-stakes independent review | GPT-5.6 Terra |
| Not used for routine Hermes runtime | GPT-5.6 Sol; Codex itself intentionally uses Sol/Medium for implementation |

Do not route Hermes runtime work through Syed’s ChatGPT/Codex subscription by default. His Codex allowance is already constrained and reserved for development work. Codex is intentionally configured to use GPT-5.6 Sol at Medium effort while building this project; that build-time choice is separate from the runtime router.

## Routing dimensions

The router should consider:

- modality;
- task complexity;
- stakes;
- source sensitivity;
- tool-call reliability;
- required latency;
- cost remaining;
- context length;
- provider health;
- specialist policy.

## Evaluation before changing baseline

There is market hype around Luna as a low-cost general model. The architecture should permit a change, but decisions must use a representative benchmark.

Create a private synthetic/redacted evaluation set covering:

- context classification;
- task/commitment extraction;
- source-grounded Slack/email synthesis;
- Codex project resumption;
- tool-call JSON reliability;
- contradiction detection;
- daily report quality;
- shopping comparison;
- screenshot interpretation;
- tax/financial evidence review.

Measure:

- factual accuracy;
- citation correctness;
- missed commitments;
- false task rate;
- context leakage;
- tool success;
- latency;
- input/output tokens;
- total cost.

## High-stakes workflow

For tax/finance/security/important decisions:

1. retrieve current primary sources;
2. use deterministic calculations;
3. run the specialist;
4. run an independent reviewer;
5. expose assumptions and uncertainty;
6. leave submission/action to Syed.

Terra is a rare reviewer, not the everyday agent.

## Cost controls

- configurable monthly budget;
- suggested warning at USD 25;
- suggested soft ceiling at USD 40;
- hard stop for optional/background calls at USD 50;
- manual override up to USD 100;
- per-provider and per-feature ledger;
- predicted call cost before very large jobs;
- caching and incremental summarization;
- no automatic “retry storm”;
- limit background scanning frequency and evidence volume;
- batch low-priority extraction where efficient.

## Latency UX

- local acknowledgement target: approximately 1–2 seconds where technically feasible;
- stream text/status immediately;
- speak sentence-by-sentence;
- show which source is being checked;
- return partial evidence before a long synthesis;
- cache source metadata and recent project state;
- keep live retrieval bounded;
- use the default fast model for routing and only escalate when justified.

Do not trade accuracy for a cosmetic first-token benchmark. The user accepts longer deep work when the system communicates progress.

## Provider resilience

- independent fallback for routine model, vision, and auxiliary tasks;
- circuit breaker and exponential backoff;
- no silent model downgrade for high-stakes work;
- record actual model/provider/version in audit metadata;
- test degraded behavior when a provider is unavailable.
