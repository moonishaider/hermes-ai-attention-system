# Prompt 7 Resource and Cost Report

**Mac:** Apple Silicon, 8 GB profile, macOS 26.5.2

- Final static frontend bundle: about 231 KB JavaScript and 7.5 KB CSS before gzip.
- Installed Jarvis plus its exact owned Hermes gateway used about 66 MiB combined RSS at healthy idle and 89.1 MiB immediately after a completed Terra review; sampled steady CPU was approximately 0–0.2%, with a brief post-run sample at 0.6% combined.
- Hermes gateway is a separately owned child bound only to loopback. Visible Flash, Pro, and Terra runs completed through it; no custom daemon remains after full Quit.
- Wake phrase is absent/off, so it consumes no wake-listener RAM/CPU.
- The Work Ledger now holds 11,424 rows behind a durable cursor; it is not a resident worker or broad periodic rescan.
- Model costs are shown per completed run from returned token usage and checked route prices. Optional background model work remains subject to the project’s $40 soft / $50 hard monthly policy.
- No local LLM, Docker, Postgres, development server, hidden daemon, or custom launch agent was added.
