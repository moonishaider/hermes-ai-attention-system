# Data and security design

SQLite WAL mode and FTS5 keep the footprint suitable for the 8 GB Mac. The schema separates immutable evidence provenance, proposed memory, tasks/open loops, action previews, audit events, model usage, and ingestion checkpoints. Real data belongs only in gitignored `runtime-data/`, `imports/`, or `context-inbox/private/`.

Retrieved content is untrusted. Credential-shaped strings are redacted before storage and common instruction-injection forms are flagged. Neither retrieved text nor model output can enable tools, change context, or count as approval. Tool inventory and action policy are checked in code.

GitHub connections are logically split between `moonishaider` and `Inside-Success`. Both have independent owner boundaries and read-only allowlists. Evidence retains owner, repository, visibility, ref/branch, commit SHA, path/line, and issue/PR number where available. Runtime create/update/delete/merge/push tools are excluded; negative tests reject them. Inside Success mutation is prohibited.

Deletion is represented as an evidence tombstone, not broad filesystem removal. Backups use the SQLite online-backup API, refuse overwrite, and target an explicit destination. Restore is manual so the current database is never silently replaced.

Known limitations: lexical FTS rather than embeddings; deterministic classification needs calibration; connector tool names may drift; no configured OAuth yet; no real-data acceptance test; no external action executor; no continuous ChatGPT-history API; overlay does not itself capture the screen; provider API calls are not implemented until credentials and exact SDK/API paths are selected.
