# Handoff Manifest and Required Reading Order

Codex should check off this list in `implementation/CONTEXT_AUDIT.md`.

## Root documents and build safety

- [ ] `README.md`
- [ ] `CHANGELOG_V2.md`
- [ ] `AGENTS.md`
- [ ] `CODEX_BOOTSTRAP_PROMPT.md`
- [ ] `CODEX_PROMPT_01_CONTEXT_ACKNOWLEDGEMENT.md`
- [ ] `CODEX_PROMPT_02_IMPLEMENTATION.md`
- [ ] `FULL_CONTEXT_HANDOFF.md`
- [ ] `MANIFEST.md`
- [ ] `PACKAGE_VALIDATION_REPORT.md`
- [ ] `.hermes-ai-attention-project`
- [ ] `.codex/config.toml`
- [ ] `.codex/config.toml.example`
- [ ] `.codex/hooks.json`
- [ ] `.codex/hooks/pre_tool_use_policy.py`
- [ ] `.codex/hooks/subagent_context.py`
- [ ] `.codex/hooks/test_pre_tool_use_policy.py`
- [ ] `.codex/rules/safety.rules`
- [ ] `config/github_scope.example.json`
- [ ] `scripts/preflight_safety.sh`
- [ ] `scripts/verify_safety_controls.sh`
- [ ] `scripts/test_safety_hook.py`
- [ ] `scripts/validate_handoff_package.sh`
- [ ] `scripts/verify_github_access.sh`
- [ ] `scripts/safe_create_private_repo.sh`
- [ ] `scripts/safe_git_push.sh`
- [ ] `CHECKSUMS.md`

## Architecture and requirements

- [ ] `docs/00_EXECUTIVE_SUMMARY.md`
- [ ] `docs/01_USER_AND_OPERATING_CONTEXT.md`
- [ ] `docs/02_PRODUCT_VISION_SCOPE_AND_NON_GOALS.md`
- [ ] `docs/03_REQUIREMENTS_CATALOG.md`
- [ ] `docs/04_TARGET_ARCHITECTURE.md`
- [ ] `docs/05_CONTEXT_PROVENANCE_AND_ROUTING.md`
- [ ] `docs/06_MEMORY_TASKS_AND_EVIDENCE.md`
- [ ] `docs/07_SPECIALISTS_AND_EXTENSIBILITY.md`
- [ ] `docs/08_INTEGRATIONS_AND_SOURCE_CONNECTORS.md`
- [ ] `docs/09_CHATGPT_AND_CODEX_HISTORY.md`
- [ ] `docs/10_MODELS_ROUTING_COST_AND_LATENCY.md`
- [ ] `docs/11_VOICE_SCREEN_OVERLAY_AND_UX.md`
- [ ] `docs/12_BROWSER_COMPUTER_ACTIONS_AND_APPROVALS.md`
- [ ] `docs/13_ATTENTION_TASKS_REPORTING_AND_AUTOMATION.md`
- [ ] `docs/14_SECURITY_THREAT_MODEL.md`
- [ ] `docs/15_CODEX_EXECUTION_SAFETY.md`
- [ ] `docs/16_DATA_MODEL_AND_STORAGE.md`
- [ ] `docs/17_IMPLEMENTATION_ROADMAP.md`
- [ ] `docs/18_ACCEPTANCE_TESTS_AND_EVALUATION.md`
- [ ] `docs/19_OPERATIONS_BACKUPS_UPDATES_AND_VPS.md`
- [ ] `docs/20_MANUAL_SETUP_RUNBOOK.md`
- [ ] `docs/21_DECISION_LOG_AND_OPEN_ITEMS.md`
- [ ] `docs/22_REQUIREMENTS_TRACEABILITY.md`
- [ ] `docs/23_OFFICIAL_REFERENCE_SOURCES.md`
- [ ] `docs/24_REPOSITORY_BLUEPRINT_AND_ENGINEERING_STANDARDS.md`
- [ ] `docs/25_CURRENT_LIMITATIONS_AND_FALLBACKS.md`
- [ ] `docs/26_WHO_DOES_WHAT.md`
- [ ] `docs/27_GITHUB_INTEGRATION_AND_REPOSITORY_CONTEXT.md`
- [ ] `docs/28_TWO_PROMPT_CODEX_EXECUTION.md`

## Reusable templates

- [ ] `templates/SPECIALIST_MODULE_TEMPLATE.md`
- [ ] `templates/INTEGRATION_ADAPTER_TEMPLATE.md`
- [ ] `templates/ACTION_APPROVAL_TEMPLATE.md`
- [ ] `templates/MILESTONE_EXECUTION_TEMPLATE.md`
- [ ] `templates/SECURITY_REVIEW_TEMPLATE.md`
- [ ] `templates/TEST_EVIDENCE_TEMPLATE.md`

## Interpretation rule

The modular documents are authoritative for their domain. `FULL_CONTEXT_HANDOFF.md` preserves user intent and sentiment. If a contradiction appears:

1. prefer the most recent explicit decision in `docs/21_DECISION_LOG_AND_OPEN_ITEMS.md`;
2. distinguish Codex build permissions/models from Hermes runtime permissions/models;
3. preserve immutable source provenance and product action controls;
4. verify time-sensitive technical facts;
5. record conflicts rather than silently discarding requirements;
6. ask Syed only when a genuine product decision cannot safely be made configurable.
