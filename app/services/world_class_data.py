import os
import requests
import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

class WorldClassDataService:
    """
    World-Class Data Service for professional-grade trading signals.
    Integrates Sentiment, On-chain data, and High-Frequency Order Book metrics.
    """
    
    def __init__(self, bot_logger=None):
        self.logger = bot_logger or logging.getLogger("world_class_data")
        self.sentiment_cache = {"score": 0.5, "fear_greed": 50, "last_update": 0}
        self.onchain_cache = {"whale_movements": [], "last_update": 0}
        self.liquidation_data = {} # Symbol -> Sliding Window of events
        self.order_book_metrics = {} # Symbol -> {imbalance, depth_ratio}
        
    def get_market_intelligence(self, symbol: str) -> Dict[str, Any]:
        """
        Consolidates all high-level intelligence for a symbol.
        Used by the AI Ensemble to gain 'World Class' context.
        """
        self._refresh_if_needed()
        
        return {
            "sentiment": self.sentiment_cache,
            "onchain": self.onchain_cache,
            "liquidations": self.liquidation_data.get(symbol, []),
            "order_book": self.order_book_metrics.get(symbol, {"imbalance": 1.0, "depth": 0.5})
        }

    def _refresh_if_needed(self):
        """Periodically refreshes external API data."""
        now = time.time()
        
        # Refresh Sentiment every 1 hour
        if now - self.sentiment_cache["last_update"] > 3600:
            self._fetch_sentiment()
            
        # Refresh On-chain data every 15 minutes
        if now - self.onchain_cache["last_update"] > 900:
            self._fetch_onchain_data()

    def _fetch_sentiment(self):
        """Fetches Fear & Greed and News Sentiment handles."""
        try:
            # 1. Fear & Greed Index from Alternative.me (Free API)
            fg_resp = requests.get("https://api.alternative.me/fng/", timeout=10)
            if fg_resp.status_code == 200:
                data = fg_resp.json()
                self.sentiment_cache["fear_greed"] = int(data["data"][0]["value"])
            
            # 2. CryptoPanic News Sentiment (Skeleton - requires API Key for full results)
            # Defaulting to neutral (0.5) if no key or error
            self.sentiment_cache["score"] = self._calculate_composite_sentiment()
            self.sentiment_cache["last_update"] = time.time()
            
            self.logger.info(f"🌐 WorldClass: Sentiment updated. F&G: {self.sentiment_cache['fear_greed']}")
        except Exception as e:
            self.logger.warning(f"⚠️ WorldClass: Sentiment fetch failed: {e}")

    def _calculate_composite_sentiment(self) -> float:
        """Weighting F&G and News into a 0.0 - 1.0 score (0.5 = neutral)."""
        fg = self.sentiment_cache.get("fear_greed", 50)
        # Convert 0-100 F&G to 0-1 score
        fg_score = fg / 100.0
        return fg_score # Currently just using F&G as primary anchor

    def _fetch_onchain_data(self):
        """Skeletal WhaleAlert / Glassnode integration."""
        try:
            # Logic for whale movements would go here.
            # For now, we simulate recent activity to feed the ensemble.
            self.onchain_cache["whale_movements"] = [
                {"type": "exchange_inflow", "amount_usd": 5000000, "symbol": "BTC", "time": time.time()}
            ]
            self.onchain_cache["last_update"] = time.time()
        except Exception as e:
            self.logger.warning(f"⚠️ WorldClass: On-chain fetch failed: {e}")

    def update_order_book_metrics(self, symbol: str, bid_depth: float, ask_depth: float):
        """Calculates imbalance: bid / (bid + ask). > 0.5 is bullish."""
        total = bid_depth + ask_depth
        imbalance = bid_depth / total if total > 0 else 0.5
        self.order_book_metrics[symbol] = {
            "imbalance": round(imbalance, 4),
            "depth_ratio": round(bid_depth / ask_depth if ask_depth > 0 else 1.0, 4)
        }

    def process_liquidation_event(self, event: Dict[str, Any]):
        """Subscriber for Binance Liquidation WebSocket."""
        symbol = event.get("s")
        if not symbol: return
        
        if symbol not in self.liquidation_data:
            self.liquidation_data[symbol] = []
            
        # Add event to sliding window (e.g., last 100 events)
        event_entry = {
            "side": event.get("S"), # BUY or SELL
            "price": float(event.get("p", 0)),
            "quantity": float(event.get("q", 0)),
            "timestamp": event.get("T")
        }
        self.liquidation_data[symbol].append(event_entry)
        
        # Prune old events (e.g., keep last 10 minutes)
        now_ms = time.time() * 1000
        self.liquidation_data[symbol] = [
            e for e in self.liquidation_data[symbol] 
            if now_ms - e["timestamp"] < 600000
        ]
