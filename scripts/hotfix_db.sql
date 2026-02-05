-- Hotfix: Add missing strategy_id to ml_model
-- Required for Watchdog to query MLModel correctly

ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS strategy_id INTEGER REFERENCES strategy(id);
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS symbol VARCHAR(20);
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS type VARCHAR(50) DEFAULT 'LSTM';

-- Ensure Phase 6 columns also exist (just in case)
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS health_state VARCHAR(20) DEFAULT 'HEALTHY';
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS last_health_check TIMESTAMP;
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS auto_paused BOOLEAN DEFAULT FALSE;
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS auto_pause_reason TEXT;
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP;

-- Create tables if not exist
CREATE TABLE IF NOT EXISTS model_performance_metric (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES ml_model(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    win_rate_7d FLOAT,
    win_rate_30d FLOAT,
    avg_confidence_7d FLOAT,
    avg_confidence_30d FLOAT,
    max_drawdown_pct FLOAT,
    current_drawdown_pct FLOAT,
    consecutive_losses INTEGER DEFAULT 0,
    signal_bias_long_pct FLOAT,
    signal_bias_short_pct FLOAT,
    signal_bias_flat_pct FLOAT,
    inference_latency_ms FLOAT,
    heartbeat_age_seconds INTEGER,
    health_state VARCHAR(20) NOT NULL,
    health_score FLOAT,
    total_signals_7d INTEGER DEFAULT 0,
    total_signals_30d INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS watchdog_event (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    model_id INTEGER REFERENCES ml_model(id),
    trigger_reason TEXT NOT NULL,
    trigger_metrics JSONB,
    action_taken VARCHAR(100),
    auto_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100)
);

-- Verify
SELECT column_name FROM information_schema.columns WHERE table_name='ml_model';
