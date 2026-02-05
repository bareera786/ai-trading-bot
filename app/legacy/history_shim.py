from typing import Optional
import logging
from app.services.trade_history import ComprehensiveTradeHistory

# ==================== ENHANCED TRADE HISTORY WITH CLEAR HISTORY ====================
# Note: This class is now replaced by ComprehensiveTradeHistory but kept for compatibility
class EnhancedTradeHistory:
    def __init__(self, data_dir="trade_data", log_callback=None):
        """
        Initialize EnhancedTradeHistory shim.
        
        Args:
            data_dir: Directory for trade data
            log_callback: Function to call for logging events. 
                         If None, uses standard logging.
        """
        self.log_callback = log_callback or self._default_logger
        self.comprehensive_history = ComprehensiveTradeHistory(
            data_dir,
            log_callback=self.log_callback,
        )

    def _default_logger(self, component, message, level=logging.INFO, details=None):
        logging.getLogger("EnhancedTradeHistory").log(level, f"[{component}] {message}")

    def add_trade(self, trade_data):
        """Add trade - compatibility method"""
        return self.comprehensive_history.add_trade(trade_data)

    def load_trades(self):
        """Load trades - compatibility method"""
        return self.comprehensive_history.load_trades()

    def save_trades(self, trades):
        """Save trades - compatibility method"""
        return self.comprehensive_history.save_trades(trades)

    def clear_history(self):
        """Clear history - compatibility method"""
        return self.comprehensive_history.clear_history()

    def get_trades(self, days=None, symbol=None, page=1, per_page=20):
        """Get trades with pagination - compatibility method"""
        filters = {}
        if days:
            filters["days"] = days
        if symbol:
            filters["symbol"] = symbol

        trades = self.comprehensive_history.get_trade_history(filters)

        # Pagination
        total_trades = len(trades)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_trades = trades[start_idx:end_idx]

        return {
            "trades": paginated_trades,
            "total_trades": total_trades,
            "current_page": page,
            "total_pages": (total_trades + per_page - 1) // per_page,
            "per_page": per_page,
        }

    def get_performance_summary(self):
        """Get performance summary - compatibility method"""
        stats = self.comprehensive_history.get_trade_statistics()
        return (
            stats["summary"]
            if "summary" in stats
            else {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0,
                "win_rate": 0,
                "avg_profit": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "best_trade": 0,
                "worst_trade": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
            }
        )

    def create_performance_chart(self, days=30):
        """Create performance chart - compatibility method"""
        # Implementation would go here
        return None

    def export_to_csv(self):
        """Export to CSV - compatibility method"""
        return self.comprehensive_history.export_to_csv()
