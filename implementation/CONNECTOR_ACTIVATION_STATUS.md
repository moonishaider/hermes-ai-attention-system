# Connector activation status

Checked: 1 August 2026

| Logical connection | State | Verified boundary |
|---|---|---|
| GitHub personal `moonishaider` | Live, tested | Separate fine-grained token; provider `/readonly`; 14-tool Hermes allowlist; authenticated owner and private project metadata verified; write tool unavailable |
| GitHub company `Inside-Success` | Live, tested | Separate fine-grained token; provider `/readonly`; 14-tool allowlist; 36 authorized repositories visible; organization approval not pending; write tool unavailable |
| Slack Inside Success | Prepared, disabled | Official hosted endpoint; internal app/workspace consent pending |
| Slack Mitchell | Prepared, disabled | Separate logical connection; app/workspace consent pending |
| Google work Gmail/Drive/Calendar | Prepared, disabled | Developer Preview endpoints; Cloud OAuth client/account consent pending |
| Google personal Gmail/Drive/Calendar | Prepared, disabled | Separate logical entries; Cloud OAuth client/account consent pending |
| Zoom | Registry only, disabled | Marketplace integration point, account scopes, product endpoint/license pending |

All remote content remains untrusted evidence. Account identity, tool inventory, provider read-only policy, Hermes include list, and a metadata-only smoke must pass separately for every activated connection.
