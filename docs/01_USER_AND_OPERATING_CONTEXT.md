# User and Operating Context

## User

**Name:** Syed Moonis Haider  
**Country/time zone:** Pakistan / Asia-Karachi  
**Communication:** dictated messages may contain transcription errors; interpret intent.  
**Output preference:** concise, direct, non-repetitive, but complete.  
**Decision preference:** honest pushback backed by evidence; no reflexive agreement or manufactured disagreement.

## Current work domains

### Inside Success

Syed’s company/job. Company colleagues generally call him **Syed**. Zoom may transcribe the name as **Sid**. The system should treat those variants as likely references to him when context supports it.

High-priority sources may include company Slack, work email, department Zoom meetings, calendar, Codex activity, and company projects.

### Mitchell

Mitchell is a separate Upwork client, not part of Inside Success. Mitchell has a separate Slack and Zoom/project context.

### Personal

Personal email, finances, tax work, shopping, side projects, planning, and personal tasks.

### Future clients and projects

The architecture must support new clients, employers, ventures, and temporary projects through configuration rather than code changes.

### Mixed and unknown

A ChatGPT conversation, Codex session, document, or action can legitimately span domains. Ambiguity should be preserved as `mixed` or `unknown` rather than forced into an incorrect category.

## Existing browser organization

- Company Chrome profile: Inside Success.
- “Profile 1”: personal, Upwork, Mitchell, and other client activity.

Do not create a third Hermes-controlled Chrome profile. Browser automation must select and expose the intended existing profile and account before side effects.

## Hardware

Apple Silicon MacBook with 8 GB RAM. API-hosted intelligence is preferred. Keep local state lightweight and avoid unnecessary background processes.

## Budget

Normal target: **under USD 50/month**.  
Possible stretch: **up to USD 100/month** only for a measured, meaningful benefit.

## User trust posture

Syed is relatively open about provider data handling. His primary concern is unauthorized, harmful, malicious, destructive, or embarrassing action by an agent.

He is comfortable experimenting, including controlled browser/computer access, but wants technical boundaries, previews, and approvals rather than a promise that the model will “be careful.”

## Additional implementation preference

Syed explicitly prefers Codex Full Access and GPT-5.6 Sol at Medium effort for this build so implementation can move quickly without repeated approval prompts. He accepts the higher risk but expects strong command blocks, backups, Git checkpoints, no destructive operations, and strict external destinations. He also wants Hermes to understand both his personal GitHub owner `moonishaider` and the company owner `inside-success` through read-only access.

