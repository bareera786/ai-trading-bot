import os
import logging
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from app.core.logging import log_component_event
from app.runtime.symbols import MARKET_CAP_WEIGHTS

class UltimateEnsembleSystem:
    def __init__(self, models_dir="ultimate_models"):
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
        self.ensemble_models = {}
        self.meta_model = None
        self.correlation_matrix = {}
        self.market_regime = "NEUTRAL"
        self.ensemble_logs = []
        self.last_rebuild_time = None
        self.rebuild_interval_hours = 24  # Daily rebuilding

    def log_ensemble(self, message, level="INFO"):
        """Log ensemble activities"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
        }
        self.ensemble_logs.append(log_entry)
        level_upper = str(level).upper()
        level_mapping = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        log_component_event(
            "ENSEMBLE", message, level=level_mapping.get(level_upper, logging.INFO)
        )
        if level_mapping.get(level_upper, logging.INFO) <= logging.INFO:
            print(f"🎯 ULTIMATE ENSEMBLE [{level_upper}]: {message}")

        # Keep only last 50 logs
        if len(self.ensemble_logs) > 50:
            self.ensemble_logs.pop(0)

    def should_rebuild_ensemble(self):
        """Check if ensemble should be rebuilt based on time"""
        if not self.last_rebuild_time:
            return True

        hours_since_rebuild = (
            datetime.now() - self.last_rebuild_time
        ).total_seconds() / 3600
        return hours_since_rebuild >= self.rebuild_interval_hours

    def periodic_ensemble_rebuilding(self, historical_predictions, actual_movements):
        """Periodic ensemble rebuilding system"""
        if not self.should_rebuild_ensemble():
            return False

        self.log_ensemble("Starting periodic ensemble rebuilding...")

        try:
            success = self.build_meta_model(historical_predictions, actual_movements)
            if success:
                self.last_rebuild_time = datetime.now()
                self.log_ensemble(
                    "✅ Periodic ensemble rebuilding completed successfully"
                )
                return True
            else:
                self.log_ensemble("❌ Periodic ensemble rebuilding failed", "ERROR")
                return False

        except Exception as e:
            self.log_ensemble(f"❌ Ensemble rebuilding error: {e}", "ERROR")
            return False

    def build_meta_model(self, historical_predictions, actual_movements):
        """Build meta-model that learns from ensemble predictions"""
        try:
            if len(historical_predictions) < 50:
                return False

            # Prepare features from historical predictions
            X = []
            y = []

            for i in range(len(historical_predictions) - 1):
                features = []

                # Aggregate prediction features
                pred_data = historical_predictions[i]
                actual_move = actual_movements[i + 1]

                # Feature engineering
                buy_signals = sum(
                    1
                    for p in pred_data.values()
                    if p.get("signal") in ["BUY", "STRONG_BUY"]
                )
                total_signals = len(pred_data)
                buy_ratio = buy_signals / total_signals if total_signals > 0 else 0.5
                features.append(buy_ratio)

                avg_confidence = np.mean(
                    [p.get("confidence", 0.5) for p in pred_data.values()]
                )
                features.append(avg_confidence)

                confidences = [p.get("confidence", 0.5) for p in pred_data.values()]
                conf_variance = np.var(confidences) if len(confidences) > 1 else 0
                features.append(conf_variance)

                strong_signals = sum(
                    1 for p in pred_data.values() if p.get("confidence", 0) > 0.7
                )
                strong_ratio = (
                    strong_signals / total_signals if total_signals > 0 else 0
                )
                features.append(strong_ratio)

                aligned = (
                    sum(
                        1
                        for p in pred_data.values()
                        if p.get("signal") in ["BUY", "STRONG_BUY"]
                    )
                    / total_signals
                )
                consensus_strength = abs(aligned - 0.5) * 2
                features.append(consensus_strength)

                X.append(features)
                y.append(1 if actual_move > 0 else 0)

            if len(X) < 20:
                return False

            # Train meta-model with cross-validation
            meta_model = RandomForestClassifier(n_estimators=100, random_state=42)
            scores = cross_val_score(meta_model, np.array(X), y, cv=5)
            avg_score = np.mean(scores)

            meta_model.fit(X, y)
            self.meta_model = meta_model

            self.log_ensemble(
                f"Meta-model rebuilt with CV accuracy: {avg_score:.4f} on {len(X)} samples"
            )
            return True

        except Exception as e:
            self.log_ensemble(f"Meta-model training error: {e}", "ERROR")
            return False

    def create_correlation_matrix(self, predictions_data):
        """Enhanced correlation matrix with parallel processing"""
        try:
            prediction_frames = []
            signal_score_map = {
                "STRONG_BUY": 2,
                "BUY": 1,
                "HOLD": 0,
                "SELL": -1,
                "STRONG_SELL": -2,
            }

            for symbol, predictions in predictions_data.items():
                if not isinstance(predictions, dict):
                    continue

                pred_block = None
                for key in (
                    "ultimate_ensemble",
                    "optimized_ensemble",
                    "professional_ensemble",
                ):
                    block = predictions.get(key)
                    if isinstance(block, dict) and block.get("signal"):
                        pred_block = block
                        break

                if not pred_block:
                    continue

                signal = pred_block.get("signal", "HOLD")
                confidence = float(pred_block.get("confidence", 0.0) or 0.0)
                signal_strength = signal_score_map.get(signal, 0) * confidence

                if signal_strength == 0 and confidence <= 0:
                    continue

                prediction_frames.append(
                    {
                        "symbol": symbol,
                        "signal_strength": signal_strength,
                        "confidence": confidence,
                    }
                )

            if len(prediction_frames) > 3:
                df = pd.DataFrame(prediction_frames)
                correlation_data = {}

                for _, row1 in df.iterrows():
                    symbol1 = row1["symbol"]
                    correlation_data[symbol1] = {}
                    for _, row2 in df.iterrows():
                        symbol2 = row2["symbol"]
                        if symbol1 == symbol2:
                            continue
                        corr = row1["signal_strength"] * row2["signal_strength"]
                        correlation_data[symbol1][symbol2] = corr

                self.correlation_matrix = correlation_data
                self.log_ensemble(
                    f"Correlation matrix updated with {len(correlation_data)} symbols"
                )
                return True

            # Clear correlation matrix if insufficient data so status reflects reality
            if prediction_frames:
                self.log_ensemble(
                    f"Correlation matrix skipped — need >=4 predictions, received {len(prediction_frames)}",
                    "DEBUG",
                )
            self.correlation_matrix = {}

        except Exception as e:
            self.correlation_matrix = {}
            self.log_ensemble(f"Correlation matrix error: {e}", "ERROR")

        return False

    def get_ensemble_prediction(self, current_predictions, market_data):
        """Ultimate ensemble prediction combining all models"""
        try:
            if not current_predictions:
                return None

            # Calculate ensemble metrics with parallel processing
            buy_votes = 0
            sell_votes = 0
            total_confidence = 0
            weighted_buy = 0
            weighted_sell = 0
            total_weight = 0

            for symbol, predictions in current_predictions.items():
                if predictions and "professional_ensemble" in predictions:
                    pred_data = predictions["professional_ensemble"]
                    signal = pred_data["signal"]
                    confidence = pred_data["confidence"]
                    weight = MARKET_CAP_WEIGHTS.get(symbol, 0.5)

                    if signal in ["BUY", "STRONG_BUY"]:
                        buy_votes += 1
                        weighted_buy += confidence * weight
                    else:
                        sell_votes += 1
                        weighted_sell += confidence * weight

                    total_confidence += confidence
                    total_weight += weight

            total_votes = buy_votes + sell_votes
            if total_votes == 0:
                return None

            # Enhanced ensemble calculation
            buy_ratio = buy_votes / total_votes
            sell_ratio = sell_votes / total_votes
            avg_confidence = total_confidence / total_votes if total_votes > 0 else 0.5

            weighted_consensus = (
                (weighted_buy - weighted_sell) / total_weight if total_weight > 0 else 0
            )

            # Advanced signal determination
            if weighted_consensus > 0.15 and buy_ratio > 0.7:
                ensemble_signal = "STRONG_BUY"
                ensemble_confidence = min(0.95, (weighted_consensus + 1) / 2)
            elif weighted_consensus > 0.08 and buy_ratio > 0.6:
                ensemble_signal = "BUY"
                ensemble_confidence = min(0.85, (weighted_consensus + 1) / 2)
            elif weighted_consensus < -0.15 and sell_ratio > 0.7:
                ensemble_signal = "STRONG_SELL"
                ensemble_confidence = min(0.95, (-weighted_consensus + 1) / 2)
            elif weighted_consensus < -0.08 and sell_ratio > 0.6:
                ensemble_signal = "SELL"
                ensemble_confidence = min(0.85, (-weighted_consensus + 1) / 2)
            else:
                ensemble_signal = "HOLD"
                ensemble_confidence = 0.5

            # Meta-model boost
            meta_boost = 0
            if self.meta_model and len(current_predictions) >= 3:
                try:
                    features = []
                    buy_signals = sum(
                        1
                        for p in current_predictions.values()
                        if p
                        and p.get("professional_ensemble", {}).get("signal")
                        in ["BUY", "STRONG_BUY"]
                    )
                    total_signals = len(current_predictions)
                    buy_ratio = buy_signals / total_signals
                    features.append(buy_ratio)

                    confidences = [
                        p.get("professional_ensemble", {}).get("confidence", 0.5)
                        for p in current_predictions.values()
                        if p
                    ]
                    avg_conf = np.mean(confidences) if confidences else 0.5
                    features.append(avg_conf)

                    conf_var = np.var(confidences) if len(confidences) > 1 else 0
                    features.append(conf_var)

                    strong_signals = sum(1 for c in confidences if c > 0.7)
                    strong_ratio = (
                        strong_signals / total_signals if total_signals > 0 else 0
                    )
                    features.append(strong_ratio)

                    consensus = abs(buy_ratio - 0.5) * 2
                    features.append(consensus)

                    meta_pred = self.meta_model.predict_proba([features])[0]
                    meta_confidence = max(meta_pred)
                    meta_boost = (meta_confidence - 0.5) * 0.3

                except Exception as e:
                    self.log_ensemble(f"Meta-model prediction error: {e}", "WARNING")

            final_confidence = min(0.95, ensemble_confidence + meta_boost)

            ensemble_result = {
                "signal": ensemble_signal,
                "confidence": final_confidence,
                "buy_ratio": buy_ratio,
                "sell_ratio": sell_ratio,
                "weighted_consensus": weighted_consensus,
                "total_models": total_votes,
                "meta_boost": meta_boost,
                "market_regime": self.market_regime,
                "correlation_strength": len(self.correlation_matrix)
                / len(current_predictions)
                if current_predictions
                else 0,
            }

            self.log_ensemble(
                f"Ensemble: {ensemble_signal} (Conf: {final_confidence:.3f}, "
                f"Buy%: {buy_ratio:.1%}, Consensus: {weighted_consensus:.3f})"
            )

            return ensemble_result

        except Exception as e:
            self.log_ensemble(f"Ensemble prediction error: {e}", "ERROR")
            return None

    def analyze_market_regime_advanced(self, market_data, historical_data):
        """Ultimate market regime analysis"""
        try:
            if not historical_data:
                return "NEUTRAL"

            if isinstance(historical_data, list):
                if historical_data and isinstance(historical_data[0], dict):
                    converted = {}
                    for entry in historical_data:
                        symbol = entry.get("symbol")
                        price = entry.get("close")
                        if price is None:
                            price = entry.get("price")
                        if symbol and price is not None:
                            converted.setdefault(symbol, []).append(float(price))
                    historical_data = converted
                else:
                    self.log_ensemble(
                        "Market regime analysis skipped: unsupported historical list format",
                        "WARNING",
                    )
                    return "NEUTRAL"
            elif not isinstance(historical_data, dict):
                self.log_ensemble(
                    "Market regime analysis skipped: unsupported historical data type",
                    "WARNING",
                )
                return "NEUTRAL"

            if len(historical_data) == 0:
                return "NEUTRAL"

            # Multi-timeframe analysis
            regimes = []

            for symbol in list(historical_data.keys())[:5]:  # Analyze top 5 symbols
                if symbol in historical_data and len(historical_data[symbol]) >= 50:
                    prices = np.array(historical_data[symbol][-50:])

                    # Trend analysis
                    x = np.arange(len(prices))
                    linreg_result = stats.linregress(x, prices)
                    slope = linreg_result.slope  # type: ignore
                    r_value = linreg_result.rvalue  # type: ignore
                    trend_strength = abs(float(r_value))

                    if trend_strength > 0.7:
                        regime = (
                            "STRONG_TREND_BULL"
                            if float(slope) > 0
                            else "STRONG_TREND_BEAR"
                        )
                    elif trend_strength > 0.4:
                        regime = (
                            "WEAK_TREND_BULL" if float(slope) > 0 else "WEAK_TREND_BEAR"
                        )
                    else:
                        regime = "SIDEWAYS"

                    regimes.append(regime)

            if not regimes:
                return "NEUTRAL"

            # Determine overall regime
            strong_bull_count = regimes.count("STRONG_TREND_BULL")
            strong_bear_count = regimes.count("STRONG_TREND_BEAR")

            if strong_bull_count >= 3:
                self.market_regime = "STRONG_BULL"
            elif strong_bear_count >= 3:
                self.market_regime = "STRONG_BEAR"
            elif "SIDEWAYS" in regimes and regimes.count("SIDEWAYS") >= 3:
                self.market_regime = "CONSOLIDATION"
            else:
                self.market_regime = "MIXED"

            return self.market_regime

        except Exception as e:
            self.log_ensemble(f"Market regime analysis error: {e}", "ERROR")
            return "NEUTRAL"
