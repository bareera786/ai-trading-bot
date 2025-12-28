# TimescaleDB / Time-series storage

This repository includes an optional TimescaleDB service for efficient storage of candles and time-series data. The service is defined in `docker-compose.timeseries.yml`.

## Quick start

- Start TimescaleDB: `docker compose -f docker-compose.timeseries.yml up -d`
- The DB will be available on port 5434 by default (configurable in the compose file).
- An initialization SQL script (`docker/timescaledb/init_timescale.sql`) creates `ticks` and `candles` hypertables, compression policy for `candles`, and an example continuous aggregate `one_min_candles`.

## Migration

To populate the database with historical data from Binance, use the migration script:

```bash
# Set environment variables (optional, can be hardcoded)
export BINANCE_API_KEY="your_api_key"
export BINANCE_SECRET_KEY="your_secret_key"
export TIMESCALE_HOST="localhost"  # or your VPS IP
export TIMESCALE_PORT="5434"
export TIMESCALE_PASSWORD=""  # set if password required

# Run migration
python migrate_to_timescaledb.py
```

The script will fetch 1-minute candles for the last 7 days for BTCUSDT, ETHUSDT, BNBUSDT, and ADAUSDT.

## Usage recommendations

- Prefer storing pre-aggregated candles in `candles` for most dashboards and backtests.
- Keep raw ticks only for short-term replay or high-precision backtests (store in `ticks` and add a retention policy).
- Use continuous aggregates to maintain fast reads without storing all ticks long-term.
