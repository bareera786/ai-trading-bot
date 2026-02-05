#!/usr/bin/env python3
"""
Migration script to populate TimescaleDB with historical candle data from Binance.

This script fetches historical candlestick data from Binance and inserts it into
the 'candles' hypertable in TimescaleDB for efficient time-series storage.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import logging

# Third-party imports
try:
    from binance.client import Client as BinanceClient
    from binance.exceptions import BinanceAPIException
except ImportError:
    print("❌ python-binance not installed. Install with: pip install python-binance")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TimescaleDBMigrator:
    """Handles migration of historical data to TimescaleDB."""

    def __init__(
        self,
        db_host: str = "localhost",
        db_port: int = 5434,
        db_name: str = "timescaledb",
        db_user: str = "timescale",
        db_password: str = "timescale_pass",
        binance_api_key: Optional[str] = None,
        binance_secret_key: Optional[str] = None,
    ):
        self.db_config = {
            "host": db_host,
            "port": db_port,
            "database": db_name,
            "user": db_user,
            "password": db_password,
        }

        # Initialize Binance client (historical klines work without API keys)
        self.binance_client = None
        if binance_api_key and binance_secret_key:
            self.binance_client = BinanceClient(binance_api_key, binance_secret_key)
        else:
            # Try environment variables
            api_key = os.getenv("BINANCE_API_KEY")
            secret_key = os.getenv("BINANCE_SECRET_KEY")
            if api_key and secret_key:
                self.binance_client = BinanceClient(api_key, secret_key)
            else:
                # Initialize client without credentials for public endpoints
                logger.info(
                    "🔓 Initializing Binance client for public endpoints (no API keys required for historical data)"
                )
                self.binance_client = BinanceClient(api_key="", api_secret="")

    def connect_db(self):
        """Establish database connection."""
        try:
            conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Connected to TimescaleDB")
            return conn
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise

    def fetch_binance_klines(
        self,
        symbol: str,
        interval: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Tuple]:
        """
        Fetch historical klines from Binance.

        Returns list of tuples: (time, symbol, interval, open, high, low, close, volume)
        """
        if not self.binance_client:
            raise ValueError("Binance client not initialized")

        try:
            # Convert datetime to string
            start_str = start_date.strftime("%d %b, %Y")

            # Fetch klines
            klines = self.binance_client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_str,
                end_str=end_date.strftime("%d %b, %Y") if end_date else None,
                limit=limit,
            )

            # Convert to our format
            candles = []
            for kline in klines:
                # Binance kline format: [open_time, open, high, low, close, volume, ...]
                timestamp = datetime.fromtimestamp(
                    kline[0] / 1000
                )  # Convert ms to datetime
                candles.append(
                    (
                        timestamp,
                        symbol,
                        interval,
                        float(kline[1]),  # open
                        float(kline[2]),  # high
                        float(kline[3]),  # low
                        float(kline[4]),  # close
                        float(kline[5]),  # volume
                    )
                )

            logger.info(f"📊 Fetched {len(candles)} {interval} candles for {symbol}")
            return candles

        except BinanceAPIException as e:
            logger.error(f"❌ Binance API error for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return []

    def insert_candles(self, conn, candles: List[Tuple]) -> int:
        """Insert candles into the database."""
        if not candles:
            return 0

        query = """
        INSERT INTO candles (time, symbol, interval, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (time, symbol, interval) DO NOTHING
        """

        try:
            with conn.cursor() as cursor:
                execute_values(cursor, query, candles)
                conn.commit()
                logger.info(f"✅ Inserted {len(candles)} candles")
                return len(candles)
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to insert candles: {e}")
            raise

    def migrate_symbol(
        self,
        symbol: str,
        interval: str = "1m",
        days_back: int = 30,
        batch_size: int = 1000,
    ) -> int:
        """
        Migrate historical data for a single symbol.

        Returns number of candles inserted.
        """
        logger.info(
            f"🚀 Starting migration for {symbol} {interval} ({days_back} days back)"
        )

        conn = self.connect_db()
        total_inserted = 0

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Fetch and insert in batches
            current_start = start_date
            while current_start < end_date:
                current_end = min(current_start + timedelta(days=1), end_date)

                candles = self.fetch_binance_klines(
                    symbol=symbol,
                    interval=interval,
                    start_date=current_start,
                    end_date=current_end,
                    limit=batch_size,
                )

                if candles:
                    inserted = self.insert_candles(conn, candles)
                    total_inserted += inserted

                current_start = current_end

            logger.info(
                f"✅ Migration completed for {symbol}: {total_inserted} candles inserted"
            )
            return total_inserted

        finally:
            conn.close()

    def migrate_multiple_symbols(
        self, symbols: List[str], interval: str = "1m", days_back: int = 30
    ) -> dict:
        """Migrate data for multiple symbols."""
        results = {}
        for symbol in symbols:
            try:
                inserted = self.migrate_symbol(symbol, interval, days_back)
                results[symbol] = {"success": True, "inserted": inserted}
            except Exception as e:
                logger.error(f"❌ Migration failed for {symbol}: {e}")
                results[symbol] = {"success": False, "error": str(e)}

        return results


def main():
    """Main migration function."""
    # Configuration - adjust as needed
    DB_HOST = os.getenv("TIMESCALE_HOST", "localhost")
    DB_PORT = int(os.getenv("TIMESCALE_PORT", "5434"))
    DB_PASSWORD = os.getenv("TIMESCALE_PASSWORD", "")

    # Symbols to migrate
    SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
    INTERVAL = "1m"  # 1 minute candles
    DAYS_BACK = 7  # Last 7 days

    # Initialize migrator
    migrator = TimescaleDBMigrator(
        db_host=DB_HOST, db_port=DB_PORT, db_password=DB_PASSWORD
    )

    # Run migration
    logger.info("🗄️ Starting TimescaleDB migration...")
    results = migrator.migrate_multiple_symbols(SYMBOLS, INTERVAL, DAYS_BACK)

    # Summary
    total_inserted = sum(
        r.get("inserted", 0) for r in results.values() if r.get("success")
    )
    successful = sum(1 for r in results.values() if r.get("success"))

    logger.info(
        f"📈 Migration summary: {successful}/{len(SYMBOLS)} symbols successful, {total_inserted} total candles inserted"
    )

    # Print results
    for symbol, result in results.items():
        status = "✅" if result["success"] else "❌"
        if result["success"]:
            print(f"{status} {symbol}: {result['inserted']} candles")
        else:
            print(f"{status} {symbol}: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
