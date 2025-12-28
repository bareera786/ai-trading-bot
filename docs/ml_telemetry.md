# ML Telemetry Dashboard

Date: 2025-11-03

## Overview

The bot now captures and surfaces rich model telemetry for both the **Ultimate** and **Optimized** profiles. Telemetry snapshots are stored atomically during every training cycle and exposed through the dashboard, REST APIs, and JSON persistence.

## Data Sources

- `ultimate_models/ultimate_training_metrics.json`
- `optimized_models/ultimate_training_metrics.json`
- In-memory model registry (`ultimate_ml_system.models`, `optimized_ml_system.models`)

Each training run appends to a bounded history (last 8 entries per symbol) with:

- Ensemble accuracy per training session
- Feature usage counts and top contributing indicators
- Model metadata (type, data source, data points)
- Timestamped training context

## New Telemetry Endpoint

```
GET /api/ml_telemetry
```

Response schema:

- `ultimate` / `optimized`
  - `summary`
    - `model_count`, `avg_accuracy_percent`, `median_accuracy_percent`
    - `stale_models` (older than 18h), `low_accuracy_models` (<65%)
    - `latest_training_display`, `latest_training_age_display`
    - `alerts[]` human-readable health warnings
  - `models[]`
    - `symbol`, `accuracy_percent`, `trend_percent`
    - `age_display`, `features_used`, `feature_utilization_percent`
    - `top_features[]` (importance-ranked)
    - `stale`, `low_accuracy`, `source`, `model_type`
  - `history[]` (bounded chronological list)

## Dashboard Updates

- Statistics tab now includes an **ML Telemetry** card with:
  - Summary health badges (stale/low-accuracy counts)
  - Current averages and best/worst accuracy markers
  - Top five symbols with accuracy delta, model age, and feature highlights
- Telemetry auto-refreshes when the Statistics tab is active and caches for fast redraws.

## Operational Notes

- History retention per symbol defaults to 8 entries and trims older data automatically.
- Atomic writes prevent JSON corruption; corrupted files are backed up with timestamped names.
- Re-training immediately refreshes telemetry via the existing performance update loop.

## Next Steps

- Persist telemetry endpoint output for offline analytics (e.g., CSV export).
- Stream telemetry deltas to the dashboard without tab polling.
- Add alert hooks (email/Slack) for stale or underperforming models.
