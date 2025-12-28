-- Init script for TimescaleDB to be placed in docker-entrypoint-initdb.d
-- Creates example tables and enables compression and policies

-- Create schema and example tables for ticks/candles
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Ticks raw (optional)
CREATE TABLE IF NOT EXISTS ticks (
  time timestamptz NOT NULL,
  symbol text NOT NULL,
  price double precision,
  size double precision,
  side text
);
SELECT create_hypertable('ticks', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');

-- Candles table (preferred to store pre-aggregated candles)
CREATE TABLE IF NOT EXISTS candles (
  time timestamptz NOT NULL,
  symbol text NOT NULL,
  interval text NOT NULL,
  open double precision,
  high double precision,
  low double precision,
  close double precision,
  volume double precision
);
SELECT create_hypertable('candles', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '7 day');

-- Index for fast queries
CREATE INDEX IF NOT EXISTS idx_candles_symbol_time ON candles (symbol, time DESC);

-- Enable compression for candles and add policy
ALTER TABLE candles SET (timescaledb.compress = true, timescaledb.compress_segmentby = 'symbol');
SELECT add_compression_policy('candles', INTERVAL '1 day');

-- Optional: retention policy to drop old ticks (keep 90 days)
SELECT add_retention_policy('ticks', INTERVAL '90 days');

-- Continuous aggregate example (1m candles from ticks)
CREATE MATERIALIZED VIEW IF NOT EXISTS one_min_candles
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 minute', time) AS bucket,
  symbol,
  (first(price, time)) AS open,
  max(price) AS high,
  min(price) AS low,
  last(price, time) AS close,
  sum(size) AS volume
FROM ticks
GROUP BY bucket, symbol;

CREATE INDEX IF NOT EXISTS idx_one_min_candles_symbol_bucket ON one_min_candles (symbol, bucket DESC);
