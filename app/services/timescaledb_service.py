"""TimescaleDB service for efficient candle data storage and retrieval."""
from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Any, TYPE_CHECKING
from contextlib import contextmanager

if TYPE_CHECKING:
    import pandas as pd

try:
    import psycopg2
    from psycopg2.extras import execute_values, RealDictCursor
    import pandas as pd

    TIMESCALEDB_AVAILABLE = True
except ImportError:
    TIMESCALEDB_AVAILABLE = False
    psycopg2 = None
    pd = None
    execute_values = None
    RealDictCursor = None


class TimescaleDBService:
    """Service for storing and retrieving candle data in TimescaleDB."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = int(os.getenv("TIMESCALE_PORT", "5434")),
        database: str = "timescaledb",
        user: str = "timescale",
        password: str = "",
        logger: Optional[logging.Logger] = None,
    ):
        # Use environment variables if password not provided
        if not password:
            password = os.getenv("TIMESCALE_PASSWORD", "timescale_pass")

        self.db_config = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
        }
        self.logger = logger or logging.getLogger(__name__)
        self._connection = None

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        if not TIMESCALEDB_AVAILABLE:
            raise RuntimeError("TimescaleDB dependencies not available")

        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)  # type: ignore
            yield conn
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def is_available(self) -> bool:
        """Check if TimescaleDB is available and accessible."""
        if not TIMESCALEDB_AVAILABLE:
            return False

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
        except Exception as e:
            self.logger.debug(f"TimescaleDB not available: {e}")
            return False

    def insert_candles(self, candles: List[Tuple]) -> int:
        """
        Insert candles into the database.

        Args:
            candles: List of tuples (time, symbol, interval, open, high, low, close, volume)

        Returns:
            Number of candles inserted
        """
        if not candles:
            return 0

        query = """
        INSERT INTO candles (time, symbol, interval, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (time, symbol, interval) DO NOTHING
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    execute_values(cursor, query, candles)  # type: ignore
                    conn.commit()
                    self.logger.debug(f"✅ Inserted {len(candles)} candles")
                    return len(candles)
        except Exception as e:
            self.logger.error(f"❌ Failed to insert candles: {e}")
            return 0

    def get_candles(
        self,
        symbol: str,
        interval: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> Optional[Any]:
        """
        Retrieve candles from database.

        Returns DataFrame with columns: date, open, high, low, close, volume
        """
        if not TIMESCALEDB_AVAILABLE:
            return None

        end_date = end_date or datetime.now()

        query = """
        SELECT time as date, open, high, low, close, volume
        FROM candles
        WHERE symbol = %s
          AND interval = %s
          AND time >= %s
          AND time <= %s
        ORDER BY time ASC
        """

        params = [symbol, interval, start_date, end_date]

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)  # type: ignore
                if not df.empty:
                    # Ensure proper datetime conversion
                    df["date"] = pd.to_datetime(df["date"])  # type: ignore
                    self.logger.debug(
                        f"📊 Retrieved {len(df)} candles from DB for {symbol}"
                    )
                    return df
        except Exception as e:
            self.logger.debug(f"Failed to query candles from DB: {e}")

        return None

    def get_latest_candle_time(self, symbol: str, interval: str) -> Optional[datetime]:
        """Get the timestamp of the most recent candle for a symbol/interval."""
        query = """
        SELECT time
        FROM candles
        WHERE symbol = %s AND interval = %s
        ORDER BY time DESC
        LIMIT 1
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:  # type: ignore
                    cursor.execute(query, (symbol, interval))
                    result = cursor.fetchone()
                    if result:
                        return result["time"]
        except Exception as e:
            self.logger.debug(f"Failed to get latest candle time: {e}")

        return None

    def store_historical_data(self, symbol: str, interval: str, df: Any) -> int:
        """
        Store historical candle data from DataFrame into TimescaleDB.

        Args:
            symbol: Trading symbol
            interval: Candle interval
            df: DataFrame with columns: date, open, high, low, close, volume

        Returns:
            Number of candles stored
        """
        if df.empty:
            return 0

        # Convert DataFrame to list of tuples
        candles = []
        for _, row in df.iterrows():
            # Ensure datetime is timezone-aware
            timestamp = row["date"]
            if timestamp.tz is None:
                timestamp = timestamp.tz_localize("UTC")

            candles.append(
                (
                    timestamp,
                    symbol,
                    interval,
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row["volume"]),
                )
            )

        return self.insert_candles(candles)

    def get_candles_count(self, symbol: str, interval: str) -> int:
        """Get total count of candles for a symbol/interval."""
        query = """
            SELECT COUNT(*) as count FROM candles WHERE symbol = %s AND interval = %s
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:  # type: ignore
                    cursor.execute(query, (symbol, interval))
                    result = cursor.fetchone()
                    return result["count"] if result else 0
        except Exception as e:
            self.logger.debug(f"Failed to get candles count: {e}")

        return 0
