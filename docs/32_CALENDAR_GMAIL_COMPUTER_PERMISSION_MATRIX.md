# Calendar, Gmail, and Computer Permission Matrix

| Capability | Personal | Work/company | Current state |
|---|---:|---:|---|
| Calendar read | allowed | read-only allowed | existing connectors |
| Calendar create | exact existing primary calendar only | impossible | Auto Explicit for direct unambiguous Personal requests; separate exact OAuth grant; ambiguity/attendees/recurrence/work requests require review |
| Calendar update/undo | Jarvis-created IDs only | impossible | exact provider-backed owner-visible create/Undo cycle passed |
| Attendees, recurrence, conference data | preview required | impossible | auto path rejects |
| Gmail read | allowed | read-only allowed | existing connectors |
| Gmail draft create/update/get | exact drafts endpoints only | impossible | Auto Explicit for direct Personal unsent-draft requests; separate exact OAuth grant; one explicit recipient or empty; sending absent |
| Gmail send | impossible | impossible | no method/tool/endpoint exists |
| One-shot screen | explicit selected region | explicit selected region | Luna; pixels discarded |
| Focus metadata | bounded app/window/domain/profile metadata | fail closed if profile cannot be proven | owner-visible bounded Focus lifecycle passed; unknown profile/domain remained unknown |
| Guided navigation | fixed reviewed destinations and public search only, with exact Profile 1/Profile 2, account, domain, context, and action preview | no arbitrary URL, typing, submission, setting change, download, company mutation, shell, or generic computer control | native preview/open plus owner-visible scrollable no-session cited public reader passed |
| Generic click/type/submit | unavailable | unavailable | deliberately absent |

Personal action wrappers enforce exact account/context/target locks, `sendUpdates=none`, no bulk recipients, no attendee/recurrence auto path, Jarvis-created resource ownership, permission hashes, crash-safe attempts, idempotency, and global/per-capability kill switches. The generic company/client kill switch remains on. A distinct local setting must enable only the two personal capabilities after OAuth, and the owner may visibly disable them again without mutating existing resources. Retrieved content cannot mint owner intent.
