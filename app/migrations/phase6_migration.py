"""
Phase 6: Performance Governance & Model Watchdog
Database migration script

Run this with: flask db upgrade
Or manually execute the SQL commands
"""

# SQL Migration Script for Phase 6

MIGRATION_SQL = """
-- Add health tracking columns to ml_model table
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS health_state VARCHAR(20) DEFAULT 'HEALTHY';
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS last_health_check TIMESTAMP;
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS auto_paused BOOLEAN DEFAULT FALSE;
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS auto_pause_reason TEXT;
ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP;

-- Create model_performance_metric table
CREATE TABLE IF NOT EXISTS model_performance_metric (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES ml_model(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Performance Metrics
    win_rate_7d FLOAT,
    win_rate_30d FLOAT,
    avg_confidence_7d FLOAT,
    avg_confidence_30d FLOAT,
    max_drawdown_pct FLOAT,
    current_drawdown_pct FLOAT,
    
    -- Risk Metrics
    consecutive_losses INTEGER DEFAULT 0,
    signal_bias_long_pct FLOAT,
    signal_bias_short_pct FLOAT,
    signal_bias_flat_pct FLOAT,
    
    -- System Metrics
    inference_latency_ms FLOAT,
    heartbeat_age_seconds INTEGER,
    
    -- Health State
    health_state VARCHAR(20) NOT NULL,
    health_score FLOAT,
    
    -- Metadata
    total_signals_7d INTEGER DEFAULT 0,
    total_signals_30d INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_perf_model_timestamp ON model_performance_metric(model_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_perf_health_state ON model_performance_metric(health_state);
CREATE INDEX IF NOT EXISTS idx_perf_timestamp ON model_performance_metric(timestamp DESC);

-- Create watchdog_event table
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

CREATE INDEX IF NOT EXISTS idx_watchdog_timestamp ON watchdog_event(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_watchdog_event_type ON watchdog_event(event_type);
CREATE INDEX IF NOT EXISTS idx_watchdog_severity ON watchdog_event(severity);

-- Grant permissions (if using specific user)
-- GRANT ALL PRIVILEGES ON model_performance_metric TO your_db_user;
-- GRANT ALL PRIVILEGES ON watchdog_event TO your_db_user;
"""

ROLLBACK_SQL = """
-- Rollback script (use with caution)
DROP TABLE IF EXISTS watchdog_event CASCADE;
DROP TABLE IF NOT EXISTS model_performance_metric CASCADE;

ALTER TABLE ml_model DROP COLUMN IF EXISTS health_state;
ALTER TABLE ml_model DROP COLUMN IF EXISTS last_health_check;
ALTER TABLE ml_model DROP COLUMN IF EXISTS auto_paused;
ALTER TABLE ml_model DROP COLUMN IF EXISTS auto_pause_reason;
ALTER TABLE ml_model DROP COLUMN IF EXISTS activated_at;
"""


if __name__ == "__main__":
    print("Phase 6 Migration SQL:")
    print("=" * 80)
    print(MIGRATION_SQL)
    print("\n" + "=" * 80)
    print("\nTo apply migration:")
    print("1. SSH to VPS: ssh aibot@151.243.171.80")
    print("2. Enter PostgreSQL: docker exec -it trading-bot-postgres psql -U aibot -d trading_bot")
    print("3. Copy and paste the SQL above")
    print("\nOr use Flask-Migrate:")
    print("flask db migrate -m 'Phase 6: Performance Governance'")
    print("flask db upgrade")
