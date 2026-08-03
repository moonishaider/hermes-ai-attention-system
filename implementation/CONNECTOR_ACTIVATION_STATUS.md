# Connector activation status

Checked: 4 August 2026

Activation does not equal real-data acceptance. `implementation/CURRENT_OPERATIONAL_STATE.md` is authoritative for that distinction.

| Logical connection | State | Verified boundary |
|---|---|---|
| GitHub personal `moonishaider` | Live, bounded real acceptance passed | Separate fine-grained token; provider `/readonly`; accepted project-resumption retrieval; write tool unavailable |
| GitHub company `Inside-Success` | Live, bounded real acceptance passed | Separate token and `/readonly` provider; accepted source-backed report draft; no company write tool |
| Slack Inside Success | Live, bounded cross-context/report acceptance passed | Exact read scopes/tools; no bot or send tool; accepted cross-context and report-draft use |
| Slack Mitchell | Live, bounded real acceptance passed | Participated in accepted cross-context use; the closeout focused run returned 8/8 exact-reference claims across 10 sources; no send tool |
| Google work Gmail/Drive/Calendar | Live; bounded acceptance passed | Separately reauthorized with exact read-only scopes; metadata probes passed; Gmail/Calendar participated in accepted work brief and same-day attribution cases; provider writes remain excluded |
| Google personal Gmail/Drive/Calendar | Live through standard direct read-only APIs; bounded acceptance passed | Profile 1 exact-scope authorization; hosted Workspace MCP disabled because consumer accounts are provider-rejected; three host-locked GET-only project tools; 6/6 cited personal-obligation claims with no reported leakage |
| Zoom work | Live and bounded usefulness-tested | Profile 2 user-managed public-client PKCE app; exactly four read scopes; shared-access widening unchecked; refreshable owner-only token; 12 raw tools discovered but only four reviewed reads exposed; a recent work-meeting case passed with 3/3 cited confirmed claims and no reported leakage |

All remote content remains untrusted evidence. Account identity, tool inventory, provider read-only policy, Hermes include list, and a metadata-only smoke must pass separately for every activated connection.

Slack's combined manifest creation/install wizard returned a misleading installation error after creating app records. After Syed explicitly authorized exact cleanup, duplicate app IDs `A0BM9QL1KPF` and `A0BMD5A2SKC` were identity-checked and deleted. Hermes remains pinned to `A0BMF36RS9X`; the unrelated n8n and Sales FAQ apps were verified present and untouched.

The first generic Hermes OAuth attempt inherited every scope advertised by Slack, including writes. That grant was revoked before use, its three local state files were preserved mode-600 under ignored quarantine, and the active files were recreated by the fail-closed strict-scope adapter. The live grant contains exactly the 14 reviewed read scopes. No Slack content was printed and no message, channel, reaction, canvas, list, or file write was attempted.

Mitchell uses a distinct Slack app, client credential, token set, callback port, Hermes server name, and Profile 1 browser boundary. The live zero-match `slack_search_channels` smoke succeeded without printing source content. The write tool is absent from the discovered inventory and blocked by project policy before any external request.

Work Google uses the organization-owned `hermes-ai-attention-work` Cloud project and a Web OAuth client stored outside Git with owner-only permissions. On 3 August 2026 the three official Developer Preview MCP resources were reauthorized separately. Stored token scopes are exactly `gmail.readonly`, `drive.readonly`, and the two Calendar read-only scopes. Metadata-only probes passed for Gmail labels, recent Drive files, and Calendar lists without printing source content. A bounded work brief used Gmail and Calendar with 9/9 cited claims, and the same-day attribution case used Calendar with 6/6 cited claims; neither reported leakage. Raw provider inventories include write-capable Gmail, Drive, and Calendar tools; Hermes exposes only the reviewed local read allowlists.

Personal Google uses the separate no-organization `hermes-ai-attention-personal` Cloud project, external testing audience, and `Hermes AI Attention - Personal Read Only` app. Credentials and token files remain outside Git with owner-only permissions. The exact scopes were reauthorized in Profile 1. Because Google's hosted Workspace MCP Developer Preview requires Workspace program access and returns provider permission errors for this consumer account, those three personal MCP servers are disabled. Host-locked GET-only standard Gmail, Drive, and Calendar API tools passed metadata smokes and bounded personal-obligations acceptance. No write method is implemented or exposed.

Zoom uses the private user-managed `Hermes Work Zoom Read Only` General App in Profile 2. A public client ID plus PKCE avoids retaining or using a confidential client secret. The exact grant is `meeting:read:search`, `meeting:read:assets`, `cloud_recording:read:list_user_recordings`, and `cloud_recording:read:content`; the optional shared-access permission remained unchecked. Live `tools/list` returned 12 tools, including two provider write tools, but the runtime include list exposes only `search_meetings`, `get_meeting_assets`, `recordings_list`, and `get_recording_resource`. A one-record metadata-only recording-list smoke passed without printing provider content, followed by a bounded usefulness case with three cited confirmed claims and no reported leakage.
