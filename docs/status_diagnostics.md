# Runtime Status Diagnostics

_Date: 2025-11-12_

The `scripts/status_diagnostics.py` helper provides a fast way to audit the bot's live
runtime health by analysing the JSON served from `/api/status` (or a stored copy of
that payload). It is designed for local troubleshooting, CI pipelines, and cron-based
monitoring on the VPS.

## Features

- Highlights model accuracy problems, stale training runs, and missing telemetry.
- Verifies that expected indicators (including SuperTrend) are active in production.
- Checks that ensembles and trading toggles are live, and flags low trade activity.
- Emits a readable summary and returns a non-zero exit code when thresholds are
  breached.

## Usage

```bash
python scripts/status_diagnostics.py http://151.243.171.80:5000/api/status
```

You may also point the tool at a saved JSON snapshot:

```bash
python scripts/status_diagnostics.py reports/status_snapshot.json
```

### Options

| Flag | Description | Default |
| ---- | ----------- | ------- |
| `--min-accuracy` | Minimum acceptable average accuracy percentage per profile. | `50.0` |
| `--max-model-age` | Maximum hours since the latest training run before a warning. | `18.0` |
| `--min-indicators` | Minimum indicator count expected in `system_status`. | `30` |
| `--min-trades` | Minimum trades expected in the performance snapshot. | `1` |
| `--timeout` | HTTP timeout (seconds) when fetching remote URLs. | `5.0` |
| `--fail-on-warnings` | Treat warnings as fatal (exit code `1`). | _Disabled_ |

Set the `BOT_STATUS_SOURCE` environment variable to make the source optional:

```bash
export BOT_STATUS_SOURCE=http://151.243.171.80:5000/api/status
python scripts/status_diagnostics.py
```

## Exit Codes

- `0`: All checks passed.
- `1`: At least one error was detected, or a warning was raised with
  `--fail-on-warnings` enabled.
- `2`: Input or configuration error (e.g., no source provided).

## Example Output

```
Profile ultimate: models=17, avg_acc=24.73, latest_training=2025-11-11 23:07
System ultimate: indicators=34, ensemble_active=False
Performance ultimate: total_trades=0, win_rate=0
Diagnostics identified the following issues:
- [ERROR] (ultimate) Average accuracy 24.73% below minimum 50.00%
- [ERROR] (ultimate) 17 models < 65%
- [WARN] (ultimate) No trades recorded yet
- [WARN] (ultimate) Only 0 trades executed (< 1)
```

Use the findings to tune training windows, adjust gating thresholds, or unblock
trading when new indicators (such as SuperTrend) are first deployed.
