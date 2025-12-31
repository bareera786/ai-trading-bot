# Project Plan & Todo List ✅

This file captures the prioritized plan, tasks, owners, acceptance criteria, and a short timeline for stabilizing the bot and preparing for Binance API approval.

---

## Goals 🎯
- Make the application reliably usable (spot & futures trading, admin features) in development and staging environments.
- Ensure reproducible tests and evidence for Binance review and testnet approval.
- Harden dev helpers for safe testing and auditing.

---

## Priorities (short-term → long-term) 🔥
1. Stabilize authentication/session/CSRF flows (blocker for E2E and dashboard).  
2. Ensure spot & futures trading flows operate reliably on testnet (end-to-end).  
3. Harden dev helpers and credential handling (token/IP allowlist, encryption at rest).  
4. Add regression tests and CI smoke jobs to prevent regressions.  
5. Prepare Binance approval package (docs, test evidence, demo steps).

---

## Master Todo List (high-level) 📋
- [x] Run full test suite and collect failing tests (initial health check)
- [ ] Reproduce & fix auth/login/session/CSRF issues (IN-PROGRESS)
  - Acceptance criteria: manual login via UI and JSON login both establish session cookie; Playwright capture shows Set-Cookie and redirect to /dashboard.
- [ ] Harden dev-only helpers (/ _whoami and / _ensure_testadmin)
  - Add API token or IP allowlist; log invocations; add tests asserting disabled by default.
  - Acceptance criteria: helpers usable only with ENABLE_DEV_ENDPOINTS=1 and a dev token OR from localhost when enabled.
- [ ] Verify and fix spot & futures trading flows (integration + UI smoke)
  - Acceptance criteria: spot/futures credential creation, testnet order placement, and order lifecycle succeed in test runs.
- [ ] Restore and validate admin features & APIs (user management, toggles)
  - Acceptance criteria: admin pages and API endpoints return 200 and perform intended actions with admin auth.
- [ ] Harden credential storage (encrypt at rest) and access control
  - Acceptance criteria: API keys stored encrypted; tests confirm read/write cycle with encryption enabled.
- [ ] Implement rate-limit/backoff tests and safety limits
  - Acceptance criteria: when mocked API returns 429, the system backoffs and retries per policy.
- [ ] Add regression tests and CI jobs (targeted — keep minimal/reproducible)
  - Acceptance criteria: CI runs smoke E2E on PRs for critical flows (login, toggle, credential storage).
- [ ] Prepare Binance approval package and documentation
  - Acceptance criteria: clear docs with test steps, HARs, Playwright captures, and logs demonstrating testnet trading and safety limits.
- [ ] Deploy pre-production smoke run & monitoring
  - Acceptance criteria: smoke checks ✅ and alerting configured for major failure modes.
- [ ] Weekly wrap-up & signoff with checklist items marked complete.

---

## Short term action plan (this sprint — next 3 workdays) ⏳
1. Finish auth/login triage and fix immediate causes (CSRF token presence or session cookie misconfig). (Owner: me)
2. Hardening dev helpers with token + log and add tests. (Owner: me)
3. Re-run integration tests for trading and fix failures. (Owner: me)
4. Produce a short "Binance approval" checklist document and attach sample evidence (playwright_capture.json). (Owner: me)

---

## Notes & Safety Considerations ⚠️
- Always default to PAPER TRADING / TESTNET in CI and dev.  
- Do not add real API keys to the repo or to CI environment variables. Use secrets in GitHub or an equivalent KMS solution.  
- Dev helpers must never be enabled in production; explicit env toggle `ENABLE_DEV_ENDPOINTS=1` and a dev-only token must be required.

---

## Industry-grade safety measures (required checklist) 🛡️
Below are defensive controls and acceptance criteria we must implement before trusting the bot in a production-like environment (and to support a Binance approval package).

- **Access Control & Least Privilege**
  - Enforce RBAC for admin actions, requiring authenticated **admin** sessions for all management endpoints.
  - Acceptance: admin-only endpoints return 403 for non-admins; automated tests assert RBAC.

- **Secrets & Key Management**
  - Store API keys encrypted at rest (KMS or vault) and access them only in memory at runtime.
  - Implement key rotation tooling and an audit trail for key usage.
  - Acceptance: encryption tested via CI; accidental plaintext keys in tests fail pre-commit/static scan.

- **Paper-vs-Live Mode Safety**
  - Default to testnet/paper mode in CI and dev; require explicit environment flag (e.g., `ENABLE_LIVE_TRADING=1`) to connect to real exchanges.
  - Acceptance: smoke tests verify `ENABLE_LIVE_TRADING` is required for live endpoints.

- **Rate Limiting & Backoff**
  - Respect exchange rate limits, implement exponential backoff and jitter on 429/5xx responses.
  - Acceptance: unit tests simulate 429 and assert exponential backoff and eventual fail-safe.

- **Order & Position Safety Guards**
  - Global and per-user limits (max order size, max leverage, max open positions, per-symbol limits).
  - Pre-trade checks for sufficient collateral and post-trade reconciliation.
  - Acceptance: integration tests verify violations are rejected and logged.

- **Circuit Breakers & Kill-switch**
  - Global emergency stop (admin-only toggle) and automatic circuit breaker on repeated failures or large drawdowns.
  - Acceptance: simulated failures trip circuit and block new orders until manual reset.

- **Observability & Alerts**
  - Structured logs, metrics (orders/sec, error rates, latency), and alerts for high-severity failures.
  - Acceptance: alerts triggered by smoke anomaly script; logs include request IDs and user IDs.

- **Immutable Audit Trail**
  - Write audit logs for order placement, credential changes, admin actions, and dev-helper calls to immutable storage (or append-only files with rotation).
  - Acceptance: audit entries include actor, timestamp, and request payload (sensitive fields redacted).

- **Testing & CI Safety Gates**
  - Deterministic unit/integration tests and CI smoke job that runs paper-trading flows and login smoke tests using dev helpers.
  - Acceptance: PRs must pass smoke tests before merge.

- **Chaos & Failure Mode Testing**
  - Run fault-injection tests (simulate network partitions, API 5xx) and assert system degrades safely.
  - Acceptance: recorded test run and mitigation verification.

- **Secrets & Sensitive Data Handling in Logs and Artifacts**
  - Redact or avoid logging secrets; ensure Playwright/HAR captures do not leak API keys.
  - Acceptance: automated scan ensures no API keys in artifacts.

- **Disaster Recovery & Backups**
  - Automated DB backups, restore runbooks, and a recovery drill checklist.
  - Acceptance: periodic restore test documented and successful.

- **Vulnerability & Dependency Management**
  - Scheduled SCA (software composition analysis), CVE alerts, and regular dependency upgrades.
  - Acceptance: no critical/unresolved CVEs for production dependencies.

- **Operational Security & Network Controls**
  - Hardened hosts, minimal network exposure, IP allowlists for admin consoles, and SSH/keys management.
  - Acceptance: infra checklist and penetration test notes.

- **Privacy & Compliance**
  - Data retention policies, user data deletion flow, and compliance docs (GDPR if applicable).
  - Acceptance: documented retention policy and tests exercising deletion flow.

- **Documentation & Runbooks**
  - Clear runbooks for starting/stopping trading, incident response, and dev-helper usage with safety warnings.
  - Acceptance: runbook reviewed and stored in repo `docs/runbooks`.

---

If you want, I can begin implementing the easiest, highest-impact items (dev-helper token logging, RBAC tests, and paper-mode enforced in CI) and then move down the checklist. Let me know which items you want prioritized.

## Communication cadence 📆
- Daily short status updates in the repo's issue or PR comments if applicable.  
- Weekly wrap-up summarizing fixes, outstanding items, and blockers.

---

If this looks good I will start by finishing the auth triage and hardening dev helpers as the immediate tasks. Let me know if you want different owners/timelines.
