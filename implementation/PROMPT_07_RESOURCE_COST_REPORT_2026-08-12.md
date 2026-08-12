# Prompt 7 Resource and Cost Report

**Mac:** Apple Silicon, 8 GB profile, macOS 26.5.2

- Current static frontend bundle: about 238 KB JavaScript and 8.0 KB CSS before gzip.
- Installed Jarvis plus its exact owned Hermes gateway used about 66 MiB combined RSS at healthy idle and 89.1 MiB immediately after a completed Terra review. The final voice-recovery build sampled at about 88 MiB combined shortly after launch; startup CPU was transiently higher while connectors initialized and steady samples returned near idle.
- Hermes gateway is a separately owned child bound only to loopback. Visible Flash, Pro, and Terra runs completed through it; no custom daemon remains after full Quit.
- Wake phrase is absent/off, so it consumes no wake-listener RAM/CPU.
- The fixed-destination navigation build sampled after settling at about 64.8 MiB combined RSS (15.0 MiB Jarvis plus 49.8 MiB owned Hermes gateway), with Jarvis at 0.0% instantaneous CPU and the gateway at 0.3%. This is a point sample, not a sustained benchmark.
- The Work Ledger now holds 11,424 rows behind a durable cursor; it is not a resident worker or broad periodic rescan.
- Model costs are shown per completed run from returned token usage and checked route prices. Optional background model work remains subject to the project’s $40 soft / $50 hard monthly policy.
- No local LLM, Docker, Postgres, development server, hidden daemon, or custom launch agent was added.
