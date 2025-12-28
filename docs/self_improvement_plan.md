# Self-Improvement & Auto-Fix Roadmap

## Objectives
- Keep both `ultimate_trader` and `optimized_trader` adaptive without manual intervention.
- Detect accuracy/latency regressions automatically and trigger corrective actions.
- Feed structured telemetry back into `dashboard_data` so operators can audit each cycle.
- Provide hooks for future "auto-update" tasks (e.g., dependency refresh, model retraining, safety resets).

## Current Baseline
- `SelfImprovementWorker` executes every `self_improvement_interval_seconds` (default 3h).
- Each cycle calls `improve_bot_efficiency_ultimate()` on both traders and optionally rebuilds ensemble models.
- No early triggers, drift detection, or remediation queue integration.

## Proposed Enhancements

### 1. Telemetry & Drift Detection
- Persist last N success rates plus rolling averages inside `dashboard_data['self_improvement']`.
- Compare success rate vs thresholds defined in `TRADING_CONFIG` (e.g., `self_improvement_min_success`).
- Flag `dashboard_data['system_status']['auto_fix_required'] = True` when metrics breach thresholds.

### 2. Auto-Fix Action Queue
- Add callback registry to `SelfImprovementWorker` allowing actions such as:
  - Re-run `ultimate_ml_system.retrain_models()`.
  - Force-refresh Binance credentials via `binance_credential_service` if API errors dominate.
  - Invoke a lightweight `auto_patch_manager` script to fetch + apply approved hotfix bundles.
- Execute queued actions sequentially after the main learning cycle to keep timing predictable.

### 3. On-Demand Cycle Triggering
- Expose `SelfImprovementWorker.request_cycle(reason: str)` to trigger an immediate run (debounced).
- Wire this to the dashboard so operators can click "Run Auto-Fix".
- Allow other services (e.g., `HealthReportService`) to request cycles when health scores degrade.

### 4. Snapshotting & Rollback
- Before each cycle, snapshot key artifacts (model weights, trader configs) into `bot_persistence/self_improvement/`.
- If the cycle worsens performance, roll back automatically and mark `dashboard_data['self_improvement']['rolled_back'] = True`.

### 5. Continuous Auto-Update Hooks
- Integrate with the existing deployment scripts (`auto_update_strategy.md`) to:
  - Validate the current git revision / container digest.
  - Schedule warm restarts after a successful auto-update.
  - Record update history plus changelog links in `dashboard_data['journal_events']`.

## Implementation Phases
1. **Telemetry Foundation** – extend `SelfImprovementWorker` to publish results + thresholds.
2. **Action Registry** – add pluggable callbacks (`auto_fix_handlers`) with retry logic.
3. **Trigger APIs** – expose REST/socket endpoints to start a cycle now.
4. **Update Hooks** – integrate with deployment scripts for seamless auto-updates.
5. **Safety & Auditing** – add detailed logging, persistence snapshots, and rollback toggles.

## Acceptance Criteria
- Operators can see when the last cycle ran, its success rate, and whether auto-fixes executed.
- When accuracy falls below thresholds, the worker auto-enqueues corrective actions within one cycle.
- Manual triggers (dashboard/API) run a cycle within 1 minute unless one is already running.
- Every auto-update/fix generates a journal entry with outcome and rollback status.
