# TimescaleDB / Time-series storage

This repository includes an optional TimescaleDB service for efficient storage of candles and time-series data. The service is defined in `docker-compose.timeseries.yml`.

Quick start:

- Start TimescaleDB: docker compose -f docker-compose.timeseries.yml up -d
- The DB will be available on port 5433 by default (configurable in the compose file).
- An initialization SQL script (`docker/timescaledb/init_timescale.sql`) creates `ticks` and `candles` hypertables, compression policy for `candles`, and an example continuous aggregate `one_min_candles`.

Usage recommendations:

- Prefer storing pre-aggregated candles in `candles` for most dashboards and backtests.
- Keep raw ticks only for short-term replay or high-precision backtests (store in `ticks` and add a retention policy).
- Use continuous aggregates to maintain fast reads without storing all ticks long-term.
