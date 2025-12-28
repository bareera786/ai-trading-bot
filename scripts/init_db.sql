-- Database initialization script for production deployment
-- This script runs when the PostgreSQL container starts for the first time

-- Create the trading_user role if it doesn't exist
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading_user') THEN
      CREATE ROLE trading_user LOGIN PASSWORD 'secure_password_123';
   END IF;
END
$$;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE trading_bot TO trading_user;
GRANT ALL ON SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_user;

-- Also create a user role for the application (matching docker-compose env var)
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'user') THEN
      CREATE ROLE "user" LOGIN PASSWORD 'password';
   END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE trading_bot TO "user";
GRANT ALL ON SCHEMA public TO "user";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "user";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "user";

-- Enable TimescaleDB extension if available
CREATE EXTENSION IF NOT EXISTS timescaledb;