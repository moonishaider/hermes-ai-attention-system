# Prompt 1 — Understand, Verify Access, Acknowledge, and Stop

You are the implementation agent for the **Hermes AI Attention & Intelligence System** in this repository. This first prompt is a **read-only understanding and access check**. Do not implement or modify anything.

The intended Codex build settings are **GPT-5.6 Sol**, **Medium reasoning**, and **Full Access with no routine approval prompts**. Those settings apply only to Codex building the project; they do not change the Hermes runtime model routing. Full Access is intentional, but every boundary in `AGENTS.md`, the project hooks/rules, and `docs/15_CODEX_EXECUTION_SAFETY.md` remains mandatory.

Do the following:

1. Read `README.md`, `AGENTS.md`, `FULL_CONTEXT_HANDOFF.md`, `MANIFEST.md`, every numbered file in `docs/`, every file in `templates/`, and the complete `.codex/`, `config/`, and `scripts/` safety setup.
2. Confirm that you understand the full product and the user’s priorities, concerns, contexts, model choices, safety posture, GitHub requirements, extensibility requirements, and desired implementation behavior—not merely the headline features.
3. Non-destructively inspect the real project path, marker, symlinks, current Git state/remotes, configuration, hooks, and command rules. Run `scripts/preflight_safety.sh` and `scripts/verify_safety_controls.sh`. Never execute a forbidden command merely to test whether it is blocked.
4. State whether the active Codex session appears to be Sol / Medium / Full Access. If any setting is not observable, say so rather than guessing.
5. Run `scripts/verify_github_access.sh` and report, without exposing credentials:
   - the authenticated GitHub identity;
   - whether `moonishaider` and `inside-success` are reachable;
   - whether access is only public or also includes authorized private repositories;
   - any SSO, scope, authentication, or repository-visibility gaps;
   - whether a new private project repository could likely be created under `moonishaider`, **without creating it**.
6. Check only the minimum current official documentation needed to flag a material compatibility problem. Save full compatibility research for Prompt 2.

In Prompt 1, do **not** create or edit files, initialize Git, install anything, clone repositories, create or push a repository, open issues or pull requests, connect OAuth, request macOS permissions, control the browser/computer, or perform any external write.

Reply concisely with exactly these headings:

- **Understood**
- **Environment and safety**
- **GitHub access**
- **Issues**
- **Ready**

Explicitly state whether you are ready for Prompt 2, then stop. Do not begin implementation until the second prompt is supplied in this same session.
