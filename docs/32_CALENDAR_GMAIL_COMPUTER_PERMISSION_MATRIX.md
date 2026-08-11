# Calendar, Gmail, and Computer Permission Matrix

| Capability | Personal | Work/company | Current state |
|---|---:|---:|---|
| Calendar read | allowed | read-only allowed | existing connectors |
| Calendar create | exact selected calendar only | impossible | wrapper implemented; live execution disabled by project safety rules |
| Calendar update/undo | Jarvis-created IDs only | impossible | wrapper implemented; synthetic/negative tested |
| Attendees, recurrence, conference data | preview required | impossible | auto path rejects |
| Gmail read | allowed | read-only allowed | existing connectors |
| Gmail draft create/update/get | exact drafts endpoints only | impossible | wrapper implemented; live execution disabled by project safety rules |
| Gmail send | impossible | impossible | no method/tool/endpoint exists |
| One-shot screen | explicit selected region | explicit selected region | Luna; pixels discarded |
| Focus metadata | bounded app/window/domain/profile metadata | fail closed if profile cannot be proven | local policy implemented; full native profile acceptance pending |
| Guided navigation | open/search/scroll/read only | no company mutation | not enabled in Jarvis release |
| Generic click/type/submit | unavailable | unavailable | deliberately absent |

Personal action wrappers enforce exact account/context/target locks, `sendUpdates=none`, no bulk recipients, no attendee/recurrence auto path, Jarvis-created resource ownership, permission hashes, idempotency, and global/per-capability kill switches. Retrieved content cannot mint owner intent.
