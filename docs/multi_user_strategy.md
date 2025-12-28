# Multi-User Capability Assessment

_Last updated: 2025-11-02_

## 1. Current Architecture Snapshot

| Area | Observation | Multi-User Impact |
| --- | --- | --- |
| Runtime singletons | Global instances (`ultimate_trader`, `optimized_trader`, ML systems, persistence scheduler) are created once at import time in `ai_ml_auto_bot_final.py`. | All users would share balances, open positions, ML models, and runtime caches. No isolation. |
| Persistence layout | State is saved under a single `bot_persistence/` tree, including `bot_state.json`, backups, logs, and credential files. | Saves for one user overwrite another; restores are global. |
| Credential storage | `BinanceCredentialStore` maintains one credential payload per account type (`spot`, `futures`). | Only one API key pair can be actively configured for each account type. |
| HTTP routes & dashboard | Flask endpoints expose a single dashboard (`/`), API proxies, and websocket-like polling built around the global traders. | There is no concept of `user_id` or tenant scoping in requests or templates. |
| Scheduler & background threads | Persistence scheduler, training loops, futures collector use global threads. | Threads mix workflows for all users and assume a single configuration namespace. |

## 2. Risk Summary

1. **Account Leakage** – API credentials, balances, and trade history are shared; one user can view or trade with another user’s keys.
2. **State Corruption** – Competing saves/loads overwrite each other’s positions and ML models.
3. **Regulatory/Compliance** – Shared logs and persistence violate data separation requirements for hosted services.
4. **Operational Complexity** – Debugging becomes impossible when multiple tenants share the same log stream and background threads.

## 3. Recommended Multi-User Strategy

### 3.1 Tenant Isolation Model

| Layer | Recommendation |
| --- | --- |
| Process boundary | Run one bot instance per user (process- or container-level isolation). The simplest path is to provision a dedicated bot container/VM per customer. |
| Configuration | Generate a per-user `BOT_HOME` directory (e.g., `/var/lib/ai-bot/<tenant-id>/`) that holds persistence, logs, credentials, and model artifacts. |
| Networking | Front the bots with a lightweight API gateway (NGINX, Traefik) that routes `tenant-id` subdomains to the correct container.
| Secret management | Store Binance keys in a secrets manager (Vault, AWS Secrets Manager) scoped to the tenant. Inject at runtime via environment variables.

### 3.2 In-App Refactor (if single process must support multiple users)

1. **Session Layer** – Introduce a `TenantContext` object that encapsulates trader, ML system, persistence manager, and logs for a given `tenant_id`.
2. **Factory Functions** – Replace global singletons with factories such as `get_trader(tenant_id)` that create or retrieve isolated instances.
3. **Scoped Persistence** – Parameterize persistence paths (`bot_persistence/<tenant-id>/…`) and pass them through every component.
4. **Credential Store** – Extend `BinanceCredentialStore` to key entries by `(tenant_id, account_type)` and encrypt at rest.
5. **API Layer** – Add authentication plus tenant resolution to each Flask route (`request.headers['X-Tenant-ID']`, JWT claims, etc.) and dispatch actions via the `TenantContext`.
6. **Background Jobs** – Run per-tenant schedulers using an async queue (e.g., `APScheduler`, `Celery`) so that long-running jobs can be isolated and restarted independently.

> **Note:** This refactor is significant; evaluate ROI versus simply running one bot per customer.

## 4. Minimal Viable Improvements (Short Term)

1. Allow the process to start with a `BOT_PROFILE=<tenant-id>` environment variable that changes the persistence/logging/credential directories.
2. Inject Binance credentials via env vars (`BINANCE_API_KEY`, `BINANCE_API_SECRET`) for immutable deployments.
3. Document the need to deploy dedicated instances per user until full tenant isolation lands.

## 5. Implementation Roadmap

| Phase | Scope | Notes |
| --- | --- | --- |
| Phase 0 (Now) | Add `BOT_PROFILE` env var, parameterize directories, ensure log handlers respect the profile. | Low risk; keeps legacy single-user flow. |
| Phase 1 | Introduce `TenantContext`, refactor factories, support per-tenant persistence + schedulers. | Moderate refactor; add integration tests. |
| Phase 2 | Add request authentication/authorization, update UI to display tenant-aware data. | Requires frontend changes and session management. |
| Phase 3 | Externalize secrets & configs, add provisioning scripts for tenant onboarding. | Align with deployment automation. |

### Phase 0 Work Breakdown (in progress)

- [x] Read `BOT_PROFILE` (default `default`) at bootstrap and derive dedicated storage paths:
	- Persistence root: `bot_persistence/<BOT_PROFILE>/`
	- Log directory: `logs/<BOT_PROFILE>/`
	- Credential vault: `credentials/<BOT_PROFILE>.json`
- [x] Update `setup_application_logging` to accept dynamic directories without double-initializing handlers.
- [x] Thread profile-aware paths through `ProfessionalPersistence`, `BinanceCredentialStore`, ML model caches, and dashboard state snapshots.
- [x] Provide a migration helper that relocates existing single-tenant data into `bot_persistence/default` on first boot after upgrade.
- [x] Extend deployment docs with instructions to export `BOT_PROFILE` per instance/container.

> Completion of Phase 0 is a prerequisite for meaningful multi-tenant tests. Each checkbox should land in source control with accompanying smoke verification before moving to Phase 1.

## 6. Testing & Validation Checklist

- [x] Unit tests for `BinanceCredentialStore` multi-tenant lookups (`tests/test_profile_pathing.py::test_binance_store_isolates_multiple_profiles`).
 - [x] Unit tests for `BinanceCredentialStore` multi-tenant lookups (`tests/test_profile_pathing.py::test_binance_store_isolates_multiple_profiles`).
 - [ ] Migration helper: `scripts/migrate_credentials_to_users.py` (move legacy `spot`/`futures` entries into `users/<user_id>/` mapping)
- [x] Integration test: start two tenant contexts, ensure trades/persistence remain isolated (`tests/test_profile_pathing.py::test_profile_paths_isolate_persistence`).
- [ ] Load test with concurrent tenant requests (Gunicorn + workers).
- [ ] Security review for credential storage and log redaction per tenant.

Run the completed checks locally with:

```bash
source .venv/bin/activate
pytest tests/test_profile_pathing.py
```

## 7. Decision Log

- **2025-11-02** – Logged that current architecture is single-tenant; multi-user support requires either per-tenant deployment or significant refactor.

---

_This document should accompany deployment notes and be revisited once tenant isolation work begins._
