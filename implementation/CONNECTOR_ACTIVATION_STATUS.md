# Connector activation status

Checked: 1 August 2026

| Logical connection | State | Verified boundary |
|---|---|---|
| GitHub personal `moonishaider` | Live, tested | Separate fine-grained token; provider `/readonly`; 14-tool Hermes allowlist; authenticated owner and private project metadata verified; write tool unavailable |
| GitHub company `Inside-Success` | Live, tested | Separate fine-grained token; provider `/readonly`; 14-tool allowlist; 36 authorized repositories visible; organization approval not pending; write tool unavailable |
| Slack Inside Success | Live, inventory tested | Internal app `A0BMF36RS9X`; strict OAuth granted exactly 14 user read scopes; seven exact read/search MCP tools; zero bot scopes; Slack MCP enabled while agent-app experience remains off |
| Slack Mitchell | Prepared, disabled | Separate logical connection; app/workspace consent pending |
| Google work Gmail/Drive/Calendar | Prepared, disabled | Developer Preview endpoints; Cloud OAuth client/account consent pending |
| Google personal Gmail/Drive/Calendar | Prepared, disabled | Separate logical entries; Cloud OAuth client/account consent pending |
| Zoom | Registry only, disabled | Marketplace integration point, account scopes, product endpoint/license pending |

All remote content remains untrusted evidence. Account identity, tool inventory, provider read-only policy, Hermes include list, and a metadata-only smoke must pass separately for every activated connection.

Slack's combined manifest creation/install wizard returned a misleading installation error after creating app records. After Syed explicitly authorized exact cleanup, duplicate app IDs `A0BM9QL1KPF` and `A0BMD5A2SKC` were identity-checked and deleted. Hermes remains pinned to `A0BMF36RS9X`; the unrelated n8n and Sales FAQ apps were verified present and untouched.

The first generic Hermes OAuth attempt inherited every scope advertised by Slack, including writes. That grant was revoked before use, its three local state files were preserved mode-600 under ignored quarantine, and the active files were recreated by the fail-closed strict-scope adapter. The live grant contains exactly the 14 reviewed read scopes. No Slack content was printed and no message, channel, reaction, canvas, list, or file write was attempted.
