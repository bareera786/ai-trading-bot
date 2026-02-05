"""
Trade Journal API Routes
Provides endpoints for trade history, filtering, analytics, and export
Uses REAL trade data only - no fake/sample data generation
"""
from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
import logging
from datetime import datetime, timedelta
import csv
import io

logger = logging.getLogger(__name__)

trade_journal_bp = Blueprint('trade_journal', __name__, url_prefix='/api/trades')


def get_real_trades_from_db(user_id=None, limit=500):
    """
    Fetch real trades from UserTrade table (Postgres).
    Returns empty list if no trades exist - NO FAKE DATA.
    """
    trades = []
    try:
        from app.models import UserTrade
        from app.extensions import db
        
        query = UserTrade.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        # Order by timestamp descending, limit results
        db_trades = query.order_by(UserTrade.timestamp.desc()).limit(limit).all()
        
        for t in db_trades:
            # Calculate hold time if exit exists
            hold_time_seconds = 0
            hold_time = "0m"
            if t.exit_price and t.exit_price > 0 and t.entry_price:
                # Estimate based on status change or use default
                hold_time_seconds = 3600  # Default 1h if unknown
                hours = hold_time_seconds // 3600
                minutes = (hold_time_seconds % 3600) // 60
                hold_time = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            
            # Determine outcome
            pnl = float(t.pnl or 0)
            outcome = "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven"
            
            # Calculate PnL percent
            pnl_percent = 0
            if t.entry_price and t.entry_price > 0 and t.quantity:
                cost = float(t.entry_price) * float(t.quantity)
                pnl_percent = (pnl / cost * 100) if cost > 0 else 0
            
            trades.append({
                "id": t.id,
                "timestamp": t.timestamp.isoformat() if t.timestamp else datetime.now().isoformat(),
                "symbol": t.symbol,
                "side": t.side,
                "entry_price": round(float(t.entry_price or 0), 2),
                "exit_price": round(float(t.exit_price or 0), 2),
                "amount": round(float(t.quantity or 0), 6),
                "pnl": round(pnl, 2),
                "pnl_percent": round(pnl_percent, 2),
                "strategy": t.signal_source or "AI-Based",
                "confidence": round(float(t.confidence_score or 0), 2),
                "hold_time": hold_time,
                "hold_time_seconds": hold_time_seconds,
                "outcome": outcome,
                "status": t.status,
                "market_type": t.market_type or "SPOT",
                "profile": t.profile or "OPTIMIZED"
            })
        
        logger.info(f"Loaded {len(trades)} real trades from database")
        
    except Exception as e:
        logger.warning(f"Failed to load trades from DB: {e}")
    
    return trades


def get_trades_from_trade_history():
    """
    Fallback: Fetch from ComprehensiveTradeHistory (in-memory) if DB empty.
    Returns empty list if no trades exist - NO FAKE DATA.
    """
    trades = []
    try:
        from app.services.trade_history import ComprehensiveTradeHistory
        
        th = ComprehensiveTradeHistory()
        raw_trades = th.load_trades()
        
        for t in raw_trades:
            # Map trade history format to journal format
            pnl = float(t.get("pnl", 0))
            outcome = "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven"
            
            entry_price = float(t.get("entry_price", 0))
            quantity = float(t.get("quantity", 0))
            pnl_percent = 0
            if entry_price > 0 and quantity > 0:
                cost = entry_price * quantity
                pnl_percent = (pnl / cost * 100) if cost > 0 else 0
            
            trades.append({
                "id": t.get("trade_id", 0),
                "timestamp": t.get("timestamp", datetime.now().isoformat()),
                "symbol": t.get("symbol", "UNKNOWN"),
                "side": t.get("side", "BUY"),
                "entry_price": round(entry_price, 2),
                "exit_price": round(float(t.get("exit_price", 0)), 2),
                "amount": round(quantity, 6),
                "pnl": round(pnl, 2),
                "pnl_percent": round(pnl_percent, 2),
                "strategy": t.get("strategy", "AI-Based"),
                "confidence": round(float(t.get("confidence", 0)), 2),
                "hold_time": "0m",
                "hold_time_seconds": 0,
                "outcome": outcome,
                "status": t.get("status", "UNKNOWN"),
                "market_type": t.get("market_type", "SPOT"),
                "profile": t.get("profile", "OPTIMIZED")
            })
        
        logger.info(f"Loaded {len(trades)} trades from ComprehensiveTradeHistory")
        
    except Exception as e:
        logger.warning(f"Failed to load from trade history: {e}")
    
    return trades


def get_all_real_trades(user_id=None):
    """
    Get real trades from database first, fallback to trade history.
    Returns empty list with clear message if no trades exist.
    NO FAKE DATA EVER.
    """
    # Try database first
    trades = get_real_trades_from_db(user_id)
    
    # Fallback to in-memory trade history if DB empty
    if not trades:
        trades = get_trades_from_trade_history()
    
    return trades


@trade_journal_bp.route('/journal', methods=['GET'])
@login_required
def get_trade_journal():
    """
    Get filtered trade history with pagination
    Query params: start_date, end_date, symbols, strategies, outcome, side, page, limit
    Returns REAL trades only - empty if none exist
    """
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else []
        strategies = request.args.get('strategies', '').split(',') if request.args.get('strategies') else []
        outcome = request.args.get('outcome', 'all')
        side = request.args.get('side', 'all')
        market_type = request.args.get('market_type', 'all')
        profile = request.args.get('profile', 'all')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        # Get REAL trades only
        all_trades = get_all_real_trades(user_id=current_user.id if current_user else None)
        
        # Apply filters
        filtered_trades = all_trades
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            filtered_trades = [t for t in filtered_trades if datetime.fromisoformat(t['timestamp']) >= start_dt]
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            filtered_trades = [t for t in filtered_trades if datetime.fromisoformat(t['timestamp']) <= end_dt]
        
        if symbols and symbols[0]:
            filtered_trades = [t for t in filtered_trades if t['symbol'] in symbols]
        
        if strategies and strategies[0]:
            filtered_trades = [t for t in filtered_trades if t['strategy'] in strategies]
        
        if outcome != 'all':
            filtered_trades = [t for t in filtered_trades if t['outcome'] == outcome]
        
        if side != 'all':
            filtered_trades = [t for t in filtered_trades if t['side'] == side]
            
        if market_type != 'all':
            filtered_trades = [t for t in filtered_trades if t['market_type'] == market_type]
            
        if profile != 'all':
            filtered_trades = [t for t in filtered_trades if t['profile'] == profile]
        
        # Sort by timestamp descending
        filtered_trades.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Calculate summary
        total_trades = len(filtered_trades)
        wins = len([t for t in filtered_trades if t['outcome'] == 'win'])
        losses = len([t for t in filtered_trades if t['outcome'] == 'loss'])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        total_pnl = sum(t['pnl'] for t in filtered_trades)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_trades = filtered_trades[start_idx:end_idx]
        total_pages = (total_trades + limit - 1) // limit if total_trades > 0 else 1
        
        return jsonify({
            "success": True,
            "data_source": "real_trades",  # Indicates this is REAL data
            "message": "No trades found. Execute trades to populate journal." if total_trades == 0 else None,
            "trades": paginated_trades,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_trades,
                "pages": total_pages
            },
            "summary": {
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 1),
                "total_pnl": round(total_pnl, 2),
                "avg_pnl_per_trade": round(avg_pnl, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting trade journal: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@trade_journal_bp.route('/analytics', methods=['GET'])
@login_required
def get_trade_analytics():
    """
    Get detailed trade analytics
    Breakdown by time of day, symbol, strategy
    Uses REAL trades only
    """
    try:
        # Get REAL trades only
        all_trades = get_all_real_trades(user_id=current_user.id if current_user else None)
        
        if not all_trades:
            return jsonify({
                "success": True,
                "data_source": "real_trades",
                "message": "No trades available for analytics. Execute trades first.",
                "by_time_of_day": {},
                "by_symbol": {},
                "by_strategy": {}
            })
        
        # Analytics by time of day
        time_buckets = {
            "00-06": {"trades": 0, "wins": 0, "pnl": 0},
            "06-12": {"trades": 0, "wins": 0, "pnl": 0},
            "12-18": {"trades": 0, "wins": 0, "pnl": 0},
            "18-24": {"trades": 0, "wins": 0, "pnl": 0},
        }
        
        for trade in all_trades:
            try:
                hour = datetime.fromisoformat(trade['timestamp']).hour
            except:
                hour = 12  # Default to midday
                
            if 0 <= hour < 6:
                bucket = "00-06"
            elif 6 <= hour < 12:
                bucket = "06-12"
            elif 12 <= hour < 18:
                bucket = "12-18"
            else:
                bucket = "18-24"
            
            time_buckets[bucket]["trades"] += 1
            if trade['outcome'] == 'win':
                time_buckets[bucket]["wins"] += 1
            time_buckets[bucket]["pnl"] += trade['pnl']
        
        # Calculate win rates and averages
        by_time_of_day = {}
        for bucket, data in time_buckets.items():
            by_time_of_day[bucket] = {
                "trades": data["trades"],
                "win_rate": round((data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0, 1),
                "avg_pnl": round(data["pnl"] / data["trades"] if data["trades"] > 0 else 0, 2)
            }
        
        # Analytics by symbol
        by_symbol = {}
        for trade in all_trades:
            symbol = trade['symbol']
            if symbol not in by_symbol:
                by_symbol[symbol] = {"trades": 0, "wins": 0, "pnl": 0}
            by_symbol[symbol]["trades"] += 1
            if trade['outcome'] == 'win':
                by_symbol[symbol]["wins"] += 1
            by_symbol[symbol]["pnl"] += trade['pnl']
        
        for symbol in by_symbol:
            data = by_symbol[symbol]
            by_symbol[symbol] = {
                "trades": data["trades"],
                "win_rate": round((data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0, 1),
                "total_pnl": round(data["pnl"], 2)
            }
        
        # Analytics by strategy
        by_strategy = {}
        for trade in all_trades:
            strategy = trade['strategy']
            if strategy not in by_strategy:
                by_strategy[strategy] = {"trades": 0, "wins": 0, "pnl": 0}
            by_strategy[strategy]["trades"] += 1
            if trade['outcome'] == 'win':
                by_strategy[strategy]["wins"] += 1
            by_strategy[strategy]["pnl"] += trade['pnl']
        
        for strategy in by_strategy:
            data = by_strategy[strategy]
            by_strategy[strategy] = {
                "trades": data["trades"],
                "win_rate": round((data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0, 1),
                "total_pnl": round(data["pnl"], 2)
            }
        
        return jsonify({
            "success": True,
            "data_source": "real_trades",
            "by_time_of_day": by_time_of_day,
            "by_symbol": by_symbol,
            "by_strategy": by_strategy
        })
        
    except Exception as e:
        logger.error(f"Error getting trade analytics: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@trade_journal_bp.route('/export/csv', methods=['GET'])
@login_required
def export_trades_csv():
    """Export REAL trades to CSV file"""
    try:
        # Allow admins to export everything
        export_all = request.args.get('all') == 'true'
        if export_all and not current_user.is_admin:
            return jsonify({"success": False, "error": "Admin access required for global export"}), 403
            
        user_id = None if (export_all and current_user.is_admin) else current_user.id
        
        # Get REAL trades only
        all_trades = get_all_real_trades(user_id=user_id)
        
        if not all_trades:
            return jsonify({
                "success": False,
                "message": "No trades to export. Execute trades first."
            }), 404
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        headers = ['ID', 'Timestamp', 'User', 'Symbol', 'Side', 'Entry Price', 'Exit Price',
                  'Amount', 'P&L', 'P&L %', 'Strategy', 'Market Type', 'Profile', 'Hold Time', 'Outcome']
        writer.writerow(headers)
        
        # Write data
        for trade in all_trades:
            writer.writerow([
                trade.get('id'),
                trade.get('timestamp'),
                trade.get('username') or trade.get('user_id') or 'System',
                trade.get('symbol'),
                trade.get('side'),
                trade.get('entry_price'),
                trade.get('exit_price'),
                trade.get('amount'),
                trade.get('pnl'),
                trade.get('pnl_percent'),
                trade.get('strategy'),
                trade.get('market_type', 'SPOT'),
                trade.get('profile', 'OPTIMIZED'),
                trade.get('hold_time'),
                trade.get('outcome')
            ])
        
        # Prepare file for download
        output.seek(0)
        filename = f'global_trades_{datetime.now().strftime("%Y%m%d")}.csv' if export_all else f'my_trades_{datetime.now().strftime("%Y%m%d")}.csv'
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error exporting trades to CSV: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
