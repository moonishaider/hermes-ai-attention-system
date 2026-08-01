# Connector activation status

Checked: 1 August 2026

| Logical connection | State | Verified boundary |
|---|---|---|
| GitHub personal `moonishaider` | Live, tested | Separate fine-grained token; provider `/readonly`; 14-tool Hermes allowlist; authenticated owner and private project metadata verified; write tool unavailable |
| GitHub company `Inside-Success` | Live, tested | Separate fine-grained token; provider `/readonly`; 14-tool allowlist; 36 authorized repositories visible; organization approval not pending; write tool unavailable |
| Slack Inside Success | App created, OAuth pending | Selected internal app `A0BMF36RS9X`; 14 required user read scopes, zero bot scopes, fixed loopback callback; client secret stored outside Git; user consent pending |
| Slack Mitchell | Prepared, disabled | Separate logical connection; app/workspace consent pending |
| Google work Gmail/Drive/Calendar | Prepared, disabled | Developer Preview endpoints; Cloud OAuth client/account consent pending |
| Google personal Gmail/Drive/Calendar | Prepared, disabled | Separate logical entries; Cloud OAuth client/account consent pending |
| Zoom | Registry only, disabled | Marketplace integration point, account scopes, product endpoint/license pending |

All remote content remains untrusted evidence. Account identity, tool inventory, provider read-only policy, Hermes include list, and a metadata-only smoke must pass separately for every activated connection.

Slack's combined manifest creation/install wizard returned a misleading installation error after creating app records. After Syed explicitly authorized exact cleanup, duplicate app IDs `A0BM9QL1KPF` and `A0BMD5A2SKC` were identity-checked and deleted. Hermes remains pinned to `A0BMF36RS9X`; the unrelated n8n and Sales FAQ apps were verified present and untouched.
