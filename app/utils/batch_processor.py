"""Batch database operations for high-performance data processing."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple, Generator

import psycopg2
import psycopg2.extras

from .database_pool import DatabasePool

logger = logging.getLogger(__name__)


class BatchDatabase:
    """
    High-performance batch database operations using connection pooling.

    Features:
    - Batch INSERT/UPDATE/DELETE operations
    - Transaction management with rollback support
    - Performance metrics and monitoring
    - Connection pooling integration
    - Error handling with partial success tracking
    """

    def __init__(self, db_pool: Optional[DatabasePool] = None):
        self.db_pool = db_pool or DatabasePool()
        self.batch_size = 1000  # Default batch size
        self.metrics = {
            "batches_processed": 0,
            "total_operations": 0,
            "total_time": 0.0,
            "errors": 0,
        }

    @contextmanager
    def get_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        """Get database connection from pool."""
        with self.db_pool.get_connection() as conn:
            yield conn

    def save_trades_batch(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save multiple trades in a single batch operation.

        Args:
            trades: List of trade dictionaries with keys: symbol, side, quantity, price, timestamp

        Returns:
            Operation results with success count and timing
        """
        if not trades:
            return {"success": True, "inserted": 0, "time": 0.0}

        start_time = time.time()

        try:
            # Prepare data for batch insert
            values = []
            for trade in trades:
                values.append((
                    trade.get("symbol"),
                    trade.get("side"),
                    trade.get("quantity"),
                    trade.get("price"),
                    trade.get("timestamp"),
                    trade.get("fee", 0),
                    trade.get("fee_asset"),
                    trade.get("order_id"),
                    trade.get("trade_id"),
                    trade.get("is_maker", False),
                ))

            query = """
            INSERT INTO trades
            (symbol, side, quantity, price, timestamp, fee, fee_asset, order_id, trade_id, is_maker)
            VALUES %s
            ON CONFLICT (trade_id) DO NOTHING
            """

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    psycopg2.extras.execute_values(cursor, query, values)
                    inserted_count = cursor.rowcount

            elapsed = time.time() - start_time
            self._update_metrics(len(trades), elapsed)

            logger.info(f"✅ Batch inserted {inserted_count}/{len(trades)} trades in {elapsed:.3f}s")
            return {
                "success": True,
                "inserted": inserted_count,
                "total": len(trades),
                "time": elapsed,
                "rate": len(trades) / elapsed if elapsed > 0 else 0,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            self.metrics["errors"] += 1
            logger.error(f"❌ Batch trade insert failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "time": elapsed,
            }

    def save_market_data_batch(self, market_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save multiple market data points in batch.

        Args:
            market_data: List of OHLCV data dictionaries

        Returns:
            Operation results
        """
        if not market_data:
            return {"success": True, "inserted": 0, "time": 0.0}

        start_time = time.time()

        try:
            values = []
            for data in market_data:
                values.append((
                    data.get("symbol"),
                    data.get("timestamp"),
                    data.get("open"),
                    data.get("high"),
                    data.get("low"),
                    data.get("close"),
                    data.get("volume"),
                    data.get("quote_asset_volume", 0),
                    data.get("number_of_trades", 0),
                    data.get("taker_buy_base_asset_volume", 0),
                    data.get("taker_buy_quote_asset_volume", 0),
                ))

            query = """
            INSERT INTO market_data
            (symbol, timestamp, open, high, low, close, volume,
             quote_asset_volume, number_of_trades, taker_buy_base_asset_volume, taker_buy_quote_asset_volume)
            VALUES %s
            ON CONFLICT (symbol, timestamp) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                quote_asset_volume = EXCLUDED.quote_asset_volume,
                number_of_trades = EXCLUDED.number_of_trades,
                taker_buy_base_asset_volume = EXCLUDED.taker_buy_base_asset_volume,
                taker_buy_quote_asset_volume = EXCLUDED.taker_buy_quote_asset_volume
            """

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    psycopg2.extras.execute_values(cursor, query, values)
                    affected_count = cursor.rowcount

            elapsed = time.time() - start_time
            self._update_metrics(len(market_data), elapsed)

            logger.info(f"✅ Batch inserted/updated {affected_count} market data points in {elapsed:.3f}s")
            return {
                "success": True,
                "affected": affected_count,
                "total": len(market_data),
                "time": elapsed,
                "rate": len(market_data) / elapsed if elapsed > 0 else 0,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            self.metrics["errors"] += 1
            logger.error(f"❌ Batch market data insert failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "time": elapsed,
            }

    def save_indicators_batch(self, indicators_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save multiple technical indicators in batch.

        Args:
            indicators_data: List of indicator dictionaries

        Returns:
            Operation results
        """
        if not indicators_data:
            return {"success": True, "inserted": 0, "time": 0.0}

        start_time = time.time()

        try:
            values = []
            for data in indicators_data:
                values.append((
                    data.get("symbol"),
                    data.get("timestamp"),
                    data.get("timeframe"),
                    data.get("indicators"),  # JSONB field for all indicators
                ))

            query = """
            INSERT INTO technical_indicators
            (symbol, timestamp, timeframe, indicators)
            VALUES %s
            ON CONFLICT (symbol, timestamp, timeframe) DO UPDATE SET
                indicators = EXCLUDED.indicators
            """

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    psycopg2.extras.execute_values(cursor, query, values)
                    affected_count = cursor.rowcount

            elapsed = time.time() - start_time
            self._update_metrics(len(indicators_data), elapsed)

            logger.info(f"✅ Batch saved {affected_count} indicator sets in {elapsed:.3f}s")
            return {
                "success": True,
                "affected": affected_count,
                "total": len(indicators_data),
                "time": elapsed,
                "rate": len(indicators_data) / elapsed if elapsed > 0 else 0,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            self.metrics["errors"] += 1
            logger.error(f"❌ Batch indicators save failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "time": elapsed,
            }

    def update_positions_batch(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update multiple positions in batch.

        Args:
            positions: List of position update dictionaries

        Returns:
            Operation results
        """
        if not positions:
            return {"success": True, "updated": 0, "time": 0.0}

        start_time = time.time()

        try:
            # Use individual updates for positions (more complex logic)
            updated_count = 0

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for position in positions:
                        query = """
                        UPDATE positions
                        SET quantity = %s, entry_price = %s, current_price = %s,
                            pnl = %s, pnl_percentage = %s, updated_at = NOW()
                        WHERE symbol = %s AND user_id = %s
                        """

                        cursor.execute(query, (
                            position.get("quantity"),
                            position.get("entry_price"),
                            position.get("current_price"),
                            position.get("pnl"),
                            position.get("pnl_percentage"),
                            position.get("symbol"),
                            position.get("user_id"),
                        ))

                        if cursor.rowcount > 0:
                            updated_count += 1

            elapsed = time.time() - start_time
            self._update_metrics(len(positions), elapsed)

            logger.info(f"✅ Batch updated {updated_count}/{len(positions)} positions in {elapsed:.3f}s")
            return {
                "success": True,
                "updated": updated_count,
                "total": len(positions),
                "time": elapsed,
                "rate": len(positions) / elapsed if elapsed > 0 else 0,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            self.metrics["errors"] += 1
            logger.error(f"❌ Batch position update failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "time": elapsed,
            }

    def batch_execute(self, operations: List[Tuple[str, Tuple]]) -> Dict[str, Any]:
        """
        Execute multiple arbitrary SQL operations in batch.

        Args:
            operations: List of (query, params) tuples

        Returns:
            Operation results
        """
        if not operations:
            return {"success": True, "executed": 0, "time": 0.0}

        start_time = time.time()

        try:
            executed_count = 0

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for query, params in operations:
                        cursor.execute(query, params)
                        executed_count += 1

            elapsed = time.time() - start_time
            self._update_metrics(len(operations), elapsed)

            logger.info(f"✅ Batch executed {executed_count} operations in {elapsed:.3f}s")
            return {
                "success": True,
                "executed": executed_count,
                "total": len(operations),
                "time": elapsed,
                "rate": len(operations) / elapsed if elapsed > 0 else 0,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            self.metrics["errors"] += 1
            logger.error(f"❌ Batch execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "time": elapsed,
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get batch operation performance metrics.

        Returns:
            Dictionary with performance statistics
        """
        metrics = self.metrics.copy()

        if metrics["total_time"] > 0:
            metrics["avg_time_per_operation"] = metrics["total_time"] / metrics["total_operations"]
            metrics["operations_per_second"] = metrics["total_operations"] / metrics["total_time"]
        else:
            metrics["avg_time_per_operation"] = 0
            metrics["operations_per_second"] = 0

        return metrics

    def reset_metrics(self):
        """Reset performance metrics."""
        self.metrics = {
            "batches_processed": 0,
            "total_operations": 0,
            "total_time": 0.0,
            "errors": 0,
        }

    def _update_metrics(self, operations_count: int, elapsed_time: float):
        """Update internal performance metrics."""
        self.metrics["batches_processed"] += 1
        self.metrics["total_operations"] += operations_count
        self.metrics["total_time"] += elapsed_time

    def optimize_batch_size(self, target_time: float = 1.0) -> int:
        """
        Dynamically optimize batch size based on performance.

        Args:
            target_time: Target time per batch in seconds

        Returns:
            Recommended batch size
        """
        metrics = self.get_performance_metrics()

        if metrics["batches_processed"] == 0:
            return self.batch_size

        avg_time_per_op = metrics["avg_time_per_operation"]
        if avg_time_per_op == 0:
            return self.batch_size

        # Calculate optimal batch size for target time
        optimal_size = int(target_time / avg_time_per_op)

        # Constrain to reasonable bounds
        optimal_size = max(10, min(10000, optimal_size))

        logger.info(f"🎯 Optimized batch size: {optimal_size} (was {self.batch_size})")
        self.batch_size = optimal_size

        return optimal_size