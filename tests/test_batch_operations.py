"""Tests for batch database operations optimization."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.utils.batch_processor import BatchDatabase


class TestBatchDatabase:
    """Test batch database operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_pool = Mock()
        self.mock_conn = Mock()
        self.mock_cursor = Mock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_pool.get_connection.return_value = self.mock_conn
        self.mock_pool.return_connection = Mock()

        self.batch_db = BatchDatabase(db_pool=self.mock_pool)

    def test_batch_database_initialization(self):
        """Test batch database initializes correctly."""
        assert self.batch_db is not None
        assert hasattr(self.batch_db, 'save_trades_batch')
        assert hasattr(self.batch_db, 'save_market_data_batch')
        assert hasattr(self.batch_db, 'get_performance_metrics')

    def test_save_trades_batch_success(self):
        """Test successful batch trade saving."""
        # Mock cursor operations
        self.mock_cursor.rowcount = 3
        self.mock_cursor.execute_values = Mock()

        trades = [
            {
                'symbol': 'BTCUSDT',
                'side': 'buy',
                'quantity': 0.01,
                'price': 50000,
                'timestamp': datetime.now(),
                'fee': 0.001,
                'fee_asset': 'USDT',
                'order_id': 'order_1',
                'trade_id': 'trade_1',
                'is_maker': False
            },
            {
                'symbol': 'ETHUSDT',
                'side': 'sell',
                'quantity': 1.0,
                'price': 3000,
                'timestamp': datetime.now(),
                'fee': 0.002,
                'fee_asset': 'USDT',
                'order_id': 'order_2',
                'trade_id': 'trade_2',
                'is_maker': True
            }
        ]

        result = self.batch_db.save_trades_batch(trades)

        assert result['success'] is True
        assert result['inserted'] == 3
        assert result['total'] == 2
        assert 'time' in result
        assert 'rate' in result

        # Verify execute_values was called
        self.mock_cursor.execute_values.assert_called_once()

    def test_save_trades_batch_empty(self):
        """Test batch saving with empty trade list."""
        result = self.batch_db.save_trades_batch([])

        assert result['success'] is True
        assert result['inserted'] == 0
        assert result['total'] == 0

    def test_save_trades_batch_database_error(self):
        """Test batch saving with database error."""
        self.mock_cursor.execute_values.side_effect = Exception("Database connection failed")

        trades = [{'symbol': 'BTCUSDT', 'side': 'buy', 'quantity': 0.01, 'price': 50000, 'timestamp': datetime.now()}]

        result = self.batch_db.save_trades_batch(trades)

        assert result['success'] is False
        assert 'error' in result
        assert 'Database connection failed' in result['error']

    def test_save_market_data_batch(self):
        """Test batch market data saving."""
        self.mock_cursor.rowcount = 5
        self.mock_cursor.execute_values = Mock()

        market_data = [
            {
                'symbol': 'BTCUSDT',
                'timestamp': datetime.now(),
                'open': 49000,
                'high': 51000,
                'low': 48500,
                'close': 50000,
                'volume': 100.5,
                'quote_asset_volume': 5025000,
                'number_of_trades': 1000,
                'taker_buy_base_asset_volume': 50.2,
                'taker_buy_quote_asset_volume': 2510000
            }
        ]

        result = self.batch_db.save_market_data_batch(market_data)

        assert result['success'] is True
        assert result['affected'] == 5
        assert result['total'] == 1

    def test_save_indicators_batch(self):
        """Test batch indicators saving."""
        self.mock_cursor.rowcount = 2
        self.mock_cursor.execute_values = Mock()

        indicators_data = [
            {
                'symbol': 'BTCUSDT',
                'timestamp': datetime.now(),
                'timeframe': '1h',
                'indicators': {'sma_20': 50000, 'rsi_14': 65}
            }
        ]

        result = self.batch_db.save_indicators_batch(indicators_data)

        assert result['success'] is True
        assert result['affected'] == 2
        assert result['total'] == 1

    def test_update_positions_batch(self):
        """Test batch position updates."""
        self.mock_cursor.rowcount = 1

        positions = [
            {
                'quantity': 0.5,
                'entry_price': 48000,
                'current_price': 50000,
                'pnl': 1000,
                'pnl_percentage': 4.17,
                'symbol': 'BTCUSDT',
                'user_id': 'user_1'
            }
        ]

        result = self.batch_db.update_positions_batch(positions)

        assert result['success'] is True
        assert result['updated'] == 1
        assert result['total'] == 1

    def test_batch_execute(self):
        """Test arbitrary batch execution."""
        operations = [
            ("INSERT INTO test_table VALUES (%s, %s)", (1, 'test1')),
            ("UPDATE test_table SET value = %s WHERE id = %s", ('updated', 1))
        ]

        result = self.batch_db.batch_execute(operations)

        assert result['success'] is True
        assert result['executed'] == 2
        assert result['total'] == 2

    def test_performance_metrics(self):
        """Test performance metrics tracking."""
        # Perform some operations to generate metrics
        self.batch_db.save_trades_batch([])

        metrics = self.batch_db.get_performance_metrics()

        assert isinstance(metrics, dict)
        assert 'batches_processed' in metrics
        assert 'total_operations' in metrics
        assert 'total_time' in metrics

    def test_metrics_reset(self):
        """Test metrics reset functionality."""
        # Add some fake metrics
        self.batch_db.metrics['batches_processed'] = 5
        self.batch_db.metrics['total_operations'] = 100

        # Reset
        self.batch_db.reset_metrics()

        assert self.batch_db.metrics['batches_processed'] == 0
        assert self.batch_db.metrics['total_operations'] == 0

    def test_batch_size_optimization(self):
        """Test batch size optimization."""
        # Set up some fake performance data
        self.batch_db.metrics['batches_processed'] = 10
        self.batch_db.metrics['total_operations'] = 1000
        self.batch_db.metrics['total_time'] = 5.0  # 5 seconds total

        # Optimize batch size
        optimal_size = self.batch_db.optimize_batch_size(target_time=1.0)

        # Should return a reasonable batch size
        assert isinstance(optimal_size, int)
        assert 10 <= optimal_size <= 10000

    def test_connection_pooling(self):
        """Test connection pooling behavior."""
        # Verify connection is requested and returned
        self.batch_db.save_trades_batch([])

        self.mock_pool.get_connection.assert_called()
        self.mock_pool.return_connection.assert_called_with(self.mock_conn)

    def test_transaction_context(self):
        """Test transaction context management."""
        with patch.object(self.batch_db, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__ = Mock(return_value=self.mock_conn)
            mock_get_conn.return_value.__exit__ = Mock(return_value=None)

            self.batch_db.save_trades_batch([])

            # Should use context manager
            mock_get_conn.assert_called_once()

    def test_large_batch_performance(self):
        """Test performance with large batches."""
        import time

        # Create a large batch
        large_trades = []
        for i in range(100):
            large_trades.append({
                'symbol': f'BTCUSDT_{i}',
                'side': 'buy' if i % 2 == 0 else 'sell',
                'quantity': 0.01,
                'price': 50000 + i,
                'timestamp': datetime.now(),
                'fee': 0.001,
                'fee_asset': 'USDT',
                'order_id': f'order_{i}',
                'trade_id': f'trade_{i}',
                'is_maker': i % 3 == 0
            })

        self.mock_cursor.rowcount = len(large_trades)
        self.mock_cursor.execute_values = Mock()

        start_time = time.time()
        result = self.batch_db.save_trades_batch(large_trades)
        end_time = time.time()

        assert result['success'] is True
        assert result['total'] == 100

        # Should complete in reasonable time
        duration = end_time - start_time
        assert duration < 1.0  # Less than 1 second for 100 trades

    def test_error_recovery(self):
        """Test error recovery and partial success handling."""
        # Test that errors are properly tracked
        self.mock_cursor.execute_values.side_effect = Exception("Connection timeout")

        trades = [{'symbol': 'BTCUSDT', 'side': 'buy', 'quantity': 0.01, 'price': 50000, 'timestamp': datetime.now()}]

        result = self.batch_db.save_trades_batch(trades)

        assert result['success'] is False
        assert 'error' in result

        # Check that error is tracked in metrics
        assert self.batch_db.metrics['errors'] > 0

    def test_concurrent_batch_operations(self):
        """Test concurrent batch operations (simulated)."""
        import threading
        import queue

        results = queue.Queue()

        def worker(worker_id):
            try:
                trades = [{
                    'symbol': f'BTCUSDT_{worker_id}',
                    'side': 'buy',
                    'quantity': 0.01,
                    'price': 50000,
                    'timestamp': datetime.now()
                }]
                result = self.batch_db.save_trades_batch(trades)
                results.put((worker_id, result))
            except Exception as e:
                results.put((worker_id, e))

        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        collected_results = []
        while not results.empty():
            collected_results.append(results.get())

        assert len(collected_results) == 3

        # All should have succeeded (in mock environment)
        for worker_id, result in collected_results:
            if isinstance(result, Exception):
                pytest.fail(f"Worker {worker_id} failed: {result}")
            else:
                assert result['success'] is True