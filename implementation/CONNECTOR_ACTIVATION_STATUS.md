# Connector activation status

Checked: 2 August 2026

Activation does not equal real-data acceptance. `implementation/CURRENT_OPERATIONAL_STATE.md` is authoritative for that distinction.

| Logical connection | State | Verified boundary |
|---|---|---|
| GitHub personal `moonishaider` | Live, bounded real acceptance passed | Separate fine-grained token; provider `/readonly`; accepted project-resumption retrieval; write tool unavailable |
| GitHub company `Inside-Success` | Live, bounded real acceptance passed | Separate token and `/readonly` provider; accepted source-backed report draft; no company write tool |
| Slack Inside Success | Live, bounded cross-context/report acceptance passed | Exact read scopes/tools; no bot or send tool; accepted cross-context and report-draft use |
| Slack Mitchell | Live, mixed acceptance | Participated in accepted cross-context use; a separate focused query timed out at 180 seconds; no send tool |
| Google work Gmail/Drive/Calendar | Reauthorization required | Prior metadata smokes and exact read allowlists stand, but all three access tokens expired without refresh tokens |
| Google personal Gmail/Drive/Calendar | Reauthorization required | Prior isolated metadata smokes stand; all three access tokens expired without refresh tokens |
| Zoom | Normal TLS healthy; OAuth pending; disabled | Official endpoint returned HTTP 401 over normal verified TLS on retry; exact work-account OAuth and post-auth inventory remain |

All remote content remains untrusted evidence. Account identity, tool inventory, provider read-only policy, Hermes include list, and a metadata-only smoke must pass separately for every activated connection.

Slack's combined manifest creation/install wizard returned a misleading installation error after creating app records. After Syed explicitly authorized exact cleanup, duplicate app IDs `A0BM9QL1KPF` and `A0BMD5A2SKC` were identity-checked and deleted. Hermes remains pinned to `A0BMF36RS9X`; the unrelated n8n and Sales FAQ apps were verified present and untouched.

The first generic Hermes OAuth attempt inherited every scope advertised by Slack, including writes. That grant was revoked before use, its three local state files were preserved mode-600 under ignored quarantine, and the active files were recreated by the fail-closed strict-scope adapter. The live grant contains exactly the 14 reviewed read scopes. No Slack content was printed and no message, channel, reaction, canvas, list, or file write was attempted.

Mitchell uses a distinct Slack app, client credential, token set, callback port, Hermes server name, and Profile 1 browser boundary. The live zero-match `slack_search_channels` smoke succeeded without printing source content. The write tool is absent from the discovered inventory and blocked by project policy before any external request.

Work Google uses the organization-owned `hermes-ai-attention-work` Cloud project and a Web OAuth client stored outside Git with owner-only permissions. The three official Developer Preview MCP resources were authorized separately. Stored token scopes are exactly `gmail.readonly`, `drive.readonly`, and the two Calendar read-only scopes. Metadata-only probes passed for Gmail labels, recent Drive files, and Calendar lists without printing source content. Raw provider inventories include write-capable Gmail, Drive, and Calendar tools; Hermes exposes only the reviewed local read allowlists.

Personal Google uses the separate no-organization `hermes-ai-attention-personal` Cloud project, external testing audience, and `Hermes AI Attention - Personal Read Only` app. Credentials and token files remain outside Git with owner-only permissions. The previous Gmail, Drive, and Calendar metadata smokes passed, but they are historical evidence until reauthorization. No write tool was invoked.
