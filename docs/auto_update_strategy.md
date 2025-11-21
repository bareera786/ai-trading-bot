# Auto-Update Strategy

_Last updated: 2025-11-03_

## 1. Objectives

- **Reliability:** Deliver bot fixes/features to VPS deployments quickly without manual SSH sessions.
- **Safety:** Ensure updates are authenticated, resumable, and can be rolled back.
- **Observability:** Capture metrics/logs around update attempts and surface success/failure states in the dashboard.

## 2. Operational Constraints

| Item | Notes |
| --- | --- |
| Deployment target | Ubuntu 22.04 LTS VPS instances with systemd-managed bot service |
| Source of truth | Git repository (GitHub) with protected main branch |
| Network policies | Outbound HTTPS allowed; inbound limited to dashboard/API ports |
| Runtime guardrails | Bot must quiesce trading loops before restart to prevent partial state writes |

## 3. Update Workflow (Happy Path)

1. **Version discovery**
   - Scheduler (e.g., hourly) queries Git remote for latest tagged release `vX.Y.Z` or commit hash.
   - Current running version stored in `bot_persistence/<profile>/meta/version.json`.
2. **Eligibility checks**
   - Skip update if local git tree dirty or newer version already applied.
   - Ensure persistence scheduler completed a save in the last N minutes.
3. **Acquire update package**
   - `git fetch --all --prune`
   - Resolve target ref (`origin/main` or tagged release) and validate signature (GPG or signed tags).
4. **Pre-flight snapshot**
   - Trigger manual persistence save.
   - Archive current code + `bot_persistence/<profile>` to `backups/<timestamp>` for rollback.
5. **Apply update**
   - `git checkout <target>` (detached HEAD) or `git pull --ff-only` for mainline deployments.
   - Run `python -m compileall ai_ml_auto_bot_final.py` and test hooks (future: unit tests).
6. **Restart service**
   - For systemd: `systemctl restart aibot.service`.
   - Monitor health endpoint until green.
7. **Report status**
   - Record success/failure, new version, and timestamp in `version.json`.
   - Emit dashboard banner + journal entry for transparency.

## 4. Failure & Rollback Handling

| Failure Point | Mitigation |
| --- | --- |
| Git fetch/checkout fails | Revert to previous commit; leave service running. Log warning. |
| Compile/test fails | Restore backed-up code directory, restart bot, emit critical alert. |
| Bot fails health check post-restart | Auto-restore from backup, restart service, mark update as failed. |
| Repeated failures | Disable auto-update and require manual intervention. |

## 5. Security Considerations

- Use deploy key with read-only scope for git operations.
- Verify signed tags or commits before trusting remote versions.
- Run updater under the same Unix user as the bot to avoid permission issues.
- Rate-limit update attempts (e.g., max 3/day) to avoid thrash.

## 6. Implementation Roadmap

| Phase | Deliverable | Notes |
| --- | --- | --- |
| Phase 0 | Manual update script `scripts/bot_update.py` that runs steps 1–6 interactively. | Low risk; reuses existing deployment guide. |
| Phase 1 | Scheduler integration (systemd timer or APScheduler job) with version tracking. | Requires config entries for update cadence. |
| Phase 2 | Health-check + rollback automation, dashboard status surface. | Adds endpoints and UI signals. |
| Phase 3 | Signed-release enforcement and optional staged rollout (canary). | Needs CI/CD support. |

## 7. Configuration Additions (proposed)

```ini
# config/update.toml
[update]
channel = "main"        # or "stable"
interval_minutes = 60
auto_restart = true
require_signed_tags = true
max_failures_per_day = 2
```

- Environment overrides: `BOT_AUTO_UPDATE=1`, `BOT_UPDATE_INTERVAL=60`, `BOT_UPDATE_CHANNEL=main`.
- Persisted state: `bot_persistence/<profile>/meta/update_state.json` with last run, result, failure count.

## 8. Testing Checklist

- [ ] Dry-run script that performs git fetch + diff without applying update.
- [ ] Simulated failure of compile step triggers rollback.
- [ ] Successful update logs journal entry and dashboard banner.
- [ ] Concurrent trading cycle pauses/resumes cleanly around restart.

## 9. Open Questions

1. Should we support self-contained release tarballs for air-gapped installs?
2. Do we need signed binary wheels for dependencies, or is pip install off-limits in auto-update?
3. How to present update availability in the UI without encouraging constant restarts?

---

_This document guides the upcoming implementation tasks. Update it as the auto-update system evolves._
