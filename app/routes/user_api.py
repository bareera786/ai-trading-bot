"""User-facing API routes for profile and portfolio data."""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import User, UserPortfolio, UserTrade
from app.runtime.symbols import get_active_trading_universe


user_api_bp = Blueprint("user_api", __name__)


def _ai_context() -> dict[str, Any]:
    return current_app.extensions.get("ai_bot_context", {})


def _ctx_callable(name: str):
    ctx = _ai_context()
    value = ctx.get(name)
    return value if callable(value) else None


@user_api_bp.route("/api/current_user")
@login_required
def api_current_user():
    """Return the authenticated user's profile metadata."""
    return jsonify(
        {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "is_admin": current_user.is_admin,
            "is_active": current_user.is_active,
            "is_premium": getattr(current_user, "is_premium", False),
            "last_login": current_user.last_login.isoformat()
            if current_user.last_login
            else None,
            "created_at": current_user.created_at.isoformat()
            if current_user.created_at
            else None,
            "custom_symbols": current_user.get_custom_symbols()
            if hasattr(current_user, "get_custom_symbols")
            else [],
        }
    )


@user_api_bp.route("/api/portfolio")
@login_required
def api_portfolio():
    """Return the authenticated user's portfolio snapshot."""
    try:
        user_portfolio = UserPortfolio.query.filter_by(user_id=current_user.id).first()
        if not user_portfolio:
            return jsonify(
                {
                    "ultimate": {},
                    "optimized": {},
                    "user_id": current_user.id,
                    "error": "Portfolio not found",
                }
            )

        user_portfolio_data = {
            "total_balance": user_portfolio.total_balance or 0,
            "available_balance": user_portfolio.available_balance or 0,
            "total_pnl": user_portfolio.total_profit_loss or 0,
            "open_positions": user_portfolio.open_positions or {},
            "user_id": current_user.id,
        }

        return jsonify(
            {
                "ultimate": user_portfolio_data,
                "optimized": user_portfolio_data,
                "user_id": current_user.id,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive logging for runtime issues
        print(f"Error in /api/portfolio: {exc}")
        return jsonify({"error": str(exc)}), 500


@user_api_bp.route("/api/portfolio/user/<int:user_id>/live_pnl")
@login_required
def api_portfolio_live_pnl(user_id: int):
    """Return live P&L data for the specified user (self or admin)."""
    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    pnl_update: dict[str, Any] = {}
    updater = _ctx_callable("update_live_portfolio_pnl")
    if updater:
        try:
            pnl_update = updater(user_id=user_id) or {}
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Error updating live P&L for user {user_id}: {exc}")
            pnl_update = {"success": False, "error": str(exc)}

    positions = UserPortfolio.query.filter_by(user_id=user_id).all()

    portfolio_data = []
    total_value = 0.0
    total_pnl = 0.0

    for position in positions:
        try:
            quantity = position.quantity or 0
            current_price = position.current_price or position.avg_price or 0
            avg_price = position.avg_price or current_price
            current_value = quantity * current_price
            pnl = position.pnl or (current_price - avg_price) * quantity
            pnl_percent = position.pnl_percent or (
                (pnl / (avg_price * quantity)) * 100 if avg_price and quantity else 0
            )

            portfolio_data.append(
                {
                    "symbol": position.symbol,
                    "quantity": quantity,
                    "avg_price": position.avg_price,
                    "current_price": current_price,
                    "current_value": current_value,
                    "pnl": pnl,
                    "pnl_percent": pnl_percent,
                    "max_position_size": position.max_position_size,
                    "stop_loss": position.stop_loss,
                    "take_profit": position.take_profit,
                    "auto_trade_enabled": position.auto_trade_enabled,
                    "risk_level": position.risk_level,
                    "created_at": position.created_at.isoformat()
                    if position.created_at
                    else None,
                    "updated_at": position.updated_at.isoformat()
                    if position.updated_at
                    else None,
                }
            )

            total_value += current_value
            total_pnl += pnl
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Error processing position {position.symbol}: {exc}")
            continue

    return jsonify(
        {
            "user_id": user_id,
            "positions": portfolio_data,
            "summary": {
                "total_positions": len(portfolio_data),
                "total_value": total_value,
                "total_pnl": total_pnl,
                "total_pnl_percent": (total_pnl / total_value) * 100
                if total_value > 0
                else 0,
            },
            "timestamp": time.time(),
            "live_pnl_updated": bool(pnl_update.get("success")),
            "last_update": pnl_update.get("timestamp"),
            "details": pnl_update,
        }
    )


@user_api_bp.route("/api/portfolio/update", methods=["POST"])
@login_required
def api_portfolio_update():
    """Create or update a user's portfolio position."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", current_user.id)

    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    symbol = str(data.get("symbol", "")).upper()
    if not symbol:
        return jsonify({"error": "Symbol required"}), 400

    try:
        position = UserPortfolio.query.filter_by(user_id=user_id, symbol=symbol).first()
        if not position:
            position = UserPortfolio(
                user_id=user_id,
                symbol=symbol,
                quantity=data.get("quantity", 0),
                avg_price=data.get("avg_price", 0),
                current_price=data.get("current_price", 0),
                pnl=0,
                pnl_percent=0,
                max_position_size=data.get("max_position_size", 1000),
                stop_loss=data.get("stop_loss"),
                take_profit=data.get("take_profit"),
                auto_trade_enabled=data.get("auto_trade_enabled", False),
                risk_level=data.get("risk_level", "medium"),
            )
            db.session.add(position)
        else:
            for field in (
                "quantity",
                "avg_price",
                "current_price",
                "max_position_size",
                "stop_loss",
                "take_profit",
                "auto_trade_enabled",
                "risk_level",
            ):
                if field in data:
                    setattr(position, field, data[field])

            if position.quantity and position.avg_price:
                current_price = position.current_price or position.avg_price
                cost_basis = position.quantity * position.avg_price
                current_value = position.quantity * current_price
                position.pnl = current_value - cost_basis
                position.pnl_percent = (
                    (position.pnl / cost_basis) * 100 if cost_basis else 0
                )

        position.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {
                "message": f"Portfolio position for {symbol} updated successfully",
                "position": {
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "avg_price": position.avg_price,
                    "current_price": position.current_price,
                    "pnl": position.pnl,
                    "pnl_percent": position.pnl_percent,
                    "max_position_size": position.max_position_size,
                    "stop_loss": position.stop_loss,
                    "take_profit": position.take_profit,
                    "auto_trade_enabled": position.auto_trade_enabled,
                    "risk_level": position.risk_level,
                    "updated_at": position.updated_at.isoformat()
                    if position.updated_at
                    else None,
                },
            }
        )
    except Exception as exc:
        db.session.rollback()
        print(f"Error in /api/portfolio/update: {exc}")
        return jsonify({"error": str(exc)}), 500


@user_api_bp.route("/api/portfolio/risk/<int:user_id>")
@login_required
def api_portfolio_risk(user_id: int):
    """Return calculated risk metrics for the specified user's portfolio."""
    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    try:
        positions = UserPortfolio.query.filter_by(user_id=user_id).all()

        if not positions:
            return jsonify(
                {
                    "user_id": user_id,
                    "risk_metrics": {
                        "total_exposure": 0,
                        "max_drawdown": 0,
                        "sharpe_ratio": 0,
                        "volatility": 0,
                        "concentration_risk": 0,
                        "risk_level": "low",
                    },
                    "positions_risk": [],
                    "timestamp": time.time(),
                }
            )

        total_exposure = 0.0
        total_pnl = 0.0
        positions_risk: list[dict[str, Any]] = []
        max_position_value = 0.0

        for position in positions:
            current_value = (position.quantity or 0) * (
                position.current_price or position.avg_price or 0
            )
            total_exposure += current_value
            total_pnl += position.pnl or 0
            max_position_value = max(max_position_value, current_value)

            positions_risk.append(
                {
                    "symbol": position.symbol,
                    "exposure": current_value,
                    "pnl": position.pnl or 0,
                    "pnl_percent": position.pnl_percent or 0,
                    "risk_level": position.risk_level,
                    "has_stop_loss": position.stop_loss is not None,
                    "has_take_profit": position.take_profit is not None,
                    "auto_trade_enabled": position.auto_trade_enabled,
                }
            )

        concentration_risk = (
            (max_position_value / total_exposure) * 100 if total_exposure > 0 else 0
        )

        if concentration_risk > 50 or any(
            p["pnl_percent"] < -20 for p in positions_risk
        ):
            overall_risk = "high"
        elif concentration_risk > 25 or any(
            p["pnl_percent"] < -10 for p in positions_risk
        ):
            overall_risk = "medium"
        else:
            overall_risk = "low"

        if len(positions_risk) > 1:
            pnl_values = [p["pnl"] for p in positions_risk]
            avg_pnl = sum(pnl_values) / len(pnl_values)
            variance = sum((x - avg_pnl) ** 2 for x in pnl_values) / len(pnl_values)
            sharpe_ratio = avg_pnl / (variance**0.5) if variance > 0 else 0
        else:
            sharpe_ratio = 0

        risk_metrics = {
            "total_exposure": total_exposure,
            "total_pnl": total_pnl,
            "max_drawdown": min((p["pnl_percent"] for p in positions_risk), default=0),
            "sharpe_ratio": sharpe_ratio,
            "volatility": abs(total_pnl / total_exposure) * 100
            if total_exposure > 0
            else 0,
            "concentration_risk": concentration_risk,
            "risk_level": overall_risk,
            "positions_count": len(positions_risk),
        }

        return jsonify(
            {
                "user_id": user_id,
                "risk_metrics": risk_metrics,
                "positions_risk": positions_risk,
                "timestamp": time.time(),
            }
        )
    except Exception as exc:
        print(f"Error in /api/portfolio/risk/{user_id}: {exc}")
        return jsonify({"error": str(exc)}), 500


@user_api_bp.route("/api/user/<int:user_id>/trades")
@login_required
def api_user_trades(user_id: int):
    """Return paginated trade history for the requested user."""
    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    try:
        page = request.args.get("page", 1, type=int)
        symbol = request.args.get("symbol")
        days = request.args.get("days", type=int)
        execution_mode = request.args.get("execution_mode")
        mode = request.args.get("mode", "ultimate").lower()

        query = UserTrade.query.filter_by(user_id=user_id)
        if symbol:
            query = query.filter(UserTrade.symbol == symbol)
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            query = query.filter(UserTrade.timestamp >= cutoff)
        if execution_mode:
            query = query.filter(UserTrade.execution_mode == execution_mode)

        query = query.order_by(UserTrade.timestamp.desc())
        total_trades = query.count()
        per_page = 20
        trades = query.offset((page - 1) * per_page).limit(per_page).all()

        trades_data = []
        for trade in trades:
            trades_data.append(
                {
                    "id": trade.id,
                    "user_id": trade.user_id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "pnl": trade.pnl,
                    "status": trade.status,
                    "trade_type": trade.trade_type,
                    # Optional columns may not exist in all deployments.
                    "execution_mode": getattr(trade, "execution_mode", None),
                    "tax_amount": getattr(trade, "tax_amount", None),
                    "fees": getattr(trade, "fees", None),
                    "timestamp": trade.timestamp.isoformat() if trade.timestamp else None,
                }
            )

        return jsonify(
            {
                "trades": trades_data,
                "total_trades": total_trades,
                "current_page": page,
                "total_pages": max(1, (total_trades + per_page - 1) // per_page),
                "per_page": per_page,
                "user_id": user_id,
                "filters": {
                    "symbol": symbol,
                    "days": days,
                    "execution_mode": execution_mode,
                    "mode": mode,
                },
                "timestamp": time.time(),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error in /api/user/{user_id}/trades: {exc}")
        return jsonify({"error": str(exc)}), 500


@user_api_bp.route("/api/user/<int:user_id>/trades/clear", methods=["POST"])
@login_required
def api_user_trades_clear(user_id: int):
    """Clear trade history for a single user.

    This intentionally only deletes rows scoped to the user_id.
    """

    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    try:
        deleted = (
            UserTrade.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        )
        db.session.commit()
        return jsonify({"success": True, "deleted": int(deleted or 0), "user_id": user_id})
    except Exception as exc:  # pragma: no cover - defensive logging
        db.session.rollback()
        print(f"Error in /api/user/{user_id}/trades/clear: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@user_api_bp.route("/api/user/<int:user_id>/risk-settings", methods=["GET", "PUT"])
@login_required
def api_user_risk_settings(user_id: int):
    """Retrieve or update risk preferences for the user's portfolio."""
    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    try:
        portfolio = UserPortfolio.query.filter_by(user_id=user_id).first()
        if not portfolio:
            return jsonify({"error": "User portfolio not found"}), 404

        if request.method == "GET":
            risk_settings = {
                "risk_level": portfolio.risk_level or "moderate",
                "max_position_size": portfolio.max_position_size or 0.1,
                "max_daily_loss": portfolio.max_daily_loss or 0.05,
                "max_total_loss": portfolio.max_total_loss or 0.2,
                "stop_loss_enabled": portfolio.stop_loss_enabled
                if portfolio.stop_loss_enabled is not None
                else True,
                "take_profit_enabled": portfolio.take_profit_enabled
                if portfolio.take_profit_enabled is not None
                else True,
                "auto_hedging": portfolio.auto_hedging
                if portfolio.auto_hedging is not None
                else False,
                "max_open_positions": portfolio.max_open_positions or 5,
                "preferred_symbols": portfolio.preferred_symbols or [],
                "trading_enabled": portfolio.trading_enabled
                if portfolio.trading_enabled is not None
                else True,
            }

            return jsonify(
                {
                    "user_id": user_id,
                    "risk_settings": risk_settings,
                    "timestamp": time.time(),
                }
            )

        payload = request.get_json() or {}
        if "risk_level" in payload:
            portfolio.risk_level = payload["risk_level"]
        if "max_position_size" in payload:
            portfolio.max_position_size = float(payload["max_position_size"])
        if "max_daily_loss" in payload:
            portfolio.max_daily_loss = float(payload["max_daily_loss"])
        if "max_total_loss" in payload:
            portfolio.max_total_loss = float(payload["max_total_loss"])
        if "stop_loss_enabled" in payload:
            portfolio.stop_loss_enabled = bool(payload["stop_loss_enabled"])
        if "take_profit_enabled" in payload:
            portfolio.take_profit_enabled = bool(payload["take_profit_enabled"])
        if "auto_hedging" in payload:
            portfolio.auto_hedging = bool(payload["auto_hedging"])
        if "max_open_positions" in payload:
            portfolio.max_open_positions = int(payload["max_open_positions"])
        if "preferred_symbols" in payload:
            portfolio.preferred_symbols = payload["preferred_symbols"]
        if "trading_enabled" in payload:
            portfolio.trading_enabled = bool(payload["trading_enabled"])

        db.session.commit()

        return jsonify(
            {
                "message": "Risk settings updated successfully",
                "user_id": user_id,
                "updated_settings": payload,
                "timestamp": time.time(),
            }
        )
    except Exception as exc:
        db.session.rollback()
        print(f"Error in /api/user/{user_id}/risk-settings: {exc}")
        return jsonify({"error": str(exc)}), 500


@user_api_bp.route("/api/user/<int:user_id>/dashboard")
@login_required
def api_user_dashboard(user_id: int):
    """Return comprehensive dashboard metrics for a specific user."""
    if current_user.id != user_id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    try:
        portfolio = UserPortfolio.query.filter_by(user_id=user_id).first()
        if not portfolio:
            return jsonify({"error": "User portfolio not found"}), 404

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        portfolio_data = {
            "total_balance": portfolio.total_balance or 0,
            "available_balance": portfolio.available_balance or 0,
            "total_pnl": portfolio.total_profit_loss or 0,
            "daily_pnl": portfolio.daily_pnl or 0,
            "open_positions": portfolio.open_positions or {},
            "risk_level": portfolio.risk_level or "moderate",
        }

        positions_data = []
        total_portfolio_value = portfolio_data["total_balance"]
        for symbol, position in (portfolio_data["open_positions"] or {}).items():
            try:
                current_price = position.get(
                    "current_price", position.get("avg_price", 0)
                )
                quantity = position.get("quantity", 0)
                avg_price = position.get("avg_price", current_price)
                position_value = quantity * current_price
                pnl = position.get("pnl", (current_price - avg_price) * quantity)
                pnl_percent = (
                    (pnl / (avg_price * quantity)) * 100
                    if avg_price and quantity
                    else 0
                )

                positions_data.append(
                    {
                        "symbol": symbol,
                        "quantity": quantity,
                        "avg_price": avg_price,
                        "current_price": current_price,
                        "position_value": position_value,
                        "pnl": pnl,
                        "pnl_percent": pnl_percent,
                    }
                )

                total_portfolio_value += position_value
            except Exception as exc:
                print(f"Error processing position {symbol}: {exc}")
                continue

        recent_trades = (
            UserTrade.query.filter_by(user_id=user_id)
            .order_by(UserTrade.timestamp.desc())
            .limit(10)
            .all()
        )
        trades_data = [
            {
                "id": trade.id,
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": trade.quantity,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "pnl": trade.pnl,
                "status": trade.status,
                "trade_type": trade.trade_type,
                "timestamp": trade.timestamp.isoformat() if trade.timestamp else None,
            }
            for trade in recent_trades
        ]

        total_exposure = sum(pos["position_value"] for pos in positions_data)
        total_pnl = sum(pos["pnl"] for pos in positions_data)
        concentration = (
            (
                max((pos["position_value"] for pos in positions_data), default=0)
                / total_exposure
                * 100
            )
            if total_exposure
            else 0
        )

        if concentration > 50 or any(
            pos["pnl_percent"] < -20 for pos in positions_data
        ):
            risk_level = "high"
        elif concentration > 25 or any(
            pos["pnl_percent"] < -10 for pos in positions_data
        ):
            risk_level = "medium"
        else:
            risk_level = "low"

        risk_metrics = {
            "total_exposure": total_exposure,
            "total_pnl": total_pnl,
            "concentration_risk": concentration,
            "risk_level": risk_level,
            "positions_count": len(positions_data),
            "max_drawdown": min(
                (pos["pnl_percent"] for pos in positions_data), default=0
            ),
        }

        total_trades = UserTrade.query.filter_by(user_id=user_id).count()
        winning_trades = (
            UserTrade.query.filter_by(user_id=user_id).filter(UserTrade.pnl > 0).count()
        )
        total_pnl_sum = sum(
            (trade.pnl or 0)
            for trade in UserTrade.query.filter_by(user_id=user_id).all()
        )

        performance_summary = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades,
            "win_rate": (winning_trades / total_trades * 100) if total_trades else 0,
            "total_pnl": total_pnl_sum,
            "avg_trade_pnl": (total_pnl_sum / total_trades) if total_trades else 0,
        }

        return jsonify(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat()
                    if user.created_at
                    else None,
                    "last_login": user.last_login.isoformat()
                    if user.last_login
                    else None,
                },
                "portfolio": portfolio_data,
                "positions": positions_data,
                "recent_trades": trades_data,
                "risk_metrics": risk_metrics,
                "performance": performance_summary,
                "portfolio_value": total_portfolio_value,
                "timestamp": time.time(),
            }
        )
    except Exception as exc:
        print(f"Error in /api/user/{user_id}/dashboard: {exc}")
        return jsonify({"error": str(exc)}), 500


@user_api_bp.route("/api/user/selected_symbols", methods=["GET", "POST"])
@login_required
def api_selected_symbols():
    try:
        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
            symbols = payload.get("symbols", [])
            if not isinstance(symbols, list):
                return jsonify({"error": "symbols must be a list"}), 400
            # Validate symbols are known
            from app.runtime import symbols as sym_mod
            known = set(sym_mod.get_all_known_symbols())
            valid_symbols = [s.upper() for s in symbols if s.upper() in known]
            current_user.set_selected_symbols(valid_symbols)
            db.session.commit()
            return jsonify({"selected_symbols": valid_symbols})
        else:
            return jsonify({"selected_symbols": current_user.get_selected_symbols()})
    except Exception as exc:
        print(f"Error in /api/user/selected_symbols: {exc}")
        return jsonify({"error": str(exc)}), 500


@user_api_bp.route("/api/user/custom_symbols", methods=["GET", "POST"])
@login_required
def api_custom_symbols():
    try:
        if not current_user.is_premium:
            return jsonify({"error": "Premium subscription required"}), 403
        
        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
            symbols = payload.get("symbols", [])
            if not isinstance(symbols, list):
                return jsonify({"error": "symbols must be a list"}), 400
            # Validate symbols are valid trading pairs (basic validation)
            valid_symbols = []
            for s in symbols:
                if isinstance(s, str) and len(s.strip()) > 0:
                    # Basic validation: should end with USDT and be uppercase
                    symbol = s.strip().upper()
                    if symbol.endswith('USDT') and len(symbol) > 4:
                        valid_symbols.append(symbol)
            current_user.set_custom_symbols(valid_symbols)
            db.session.commit()
            return jsonify({"custom_symbols": valid_symbols})
        else:
            return jsonify({"custom_symbols": current_user.get_custom_symbols()})
    except Exception as exc:
        print(f"Error in /api/user/custom_symbols: {exc}")
        return jsonify({"error": str(exc)}), 500


@user_api_bp.route("/api/user/symbol/<symbol>/auto_trade", methods=["POST"])
@login_required
def api_toggle_symbol_auto_trade(symbol):
    try:
        symbol = symbol.upper()
        if not symbol:
            return jsonify({"error": "Symbol required"}), 400
        
        # Check if user has access to this symbol (selected or custom)
        user_symbols = current_user.get_selected_symbols()
        if current_user.is_premium:
            user_symbols.extend(current_user.get_custom_symbols())
        
        if symbol not in user_symbols and symbol not in get_active_trading_universe():
            return jsonify({"error": "Symbol not available"}), 403
        
        position = UserPortfolio.query.filter_by(user_id=current_user.id, symbol=symbol).first()
        if not position:
            # Create position if it doesn't exist
            position = UserPortfolio(
                user_id=current_user.id,
                symbol=symbol,
                quantity=0,
                avg_price=0,
                current_price=0,
                pnl=0,
                pnl_percent=0,
                max_position_size=1000,
                auto_trade_enabled=True,  # Enable by default for toggle
                risk_level="medium",
            )
            db.session.add(position)
        else:
            position.auto_trade_enabled = not position.auto_trade_enabled
        
        db.session.commit()
        return jsonify({
            "symbol": symbol,
            "auto_trade_enabled": position.auto_trade_enabled
        })
    except Exception as exc:
        print(f"Error in /api/user/symbol/{symbol}/auto_trade: {exc}")
        return jsonify({"error": str(exc)}), 500
