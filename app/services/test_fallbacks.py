"""Minimal in-memory services used by tests and lightweight setups.

These are intentionally tiny, have no external dependencies, and are only
used when the full runtime is not initialized (e.g., during tests that set
AI_BOT_TEST_MODE). They provide a predictable behavior for endpoints that
expect credential storage, logging, and simple trader status.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class InMemoryCredentialsStore:
    def __init__(self):
        # Structure: {user_id: {account_type: creds_dict}}
        self._store: Dict[int, Dict[str, Dict[str, Any]]] = {}

    def _normalize_account_type(self, account_type: Optional[str]) -> str:
        t = (account_type or "spot").strip().lower()
        return "futures" if t.startswith("f") else "spot"

    def save_credentials(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        note: Optional[str] = None,
        account_type: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        acct = self._normalize_account_type(account_type)
        uid = int(user_id) if user_id is not None else 0
        self._store.setdefault(uid, {})[acct] = {
            "api_key": api_key,
            "api_secret": api_secret,
            "testnet": bool(testnet),
            "note": note,
            "account_type": acct,
            "user_id": uid,
        }
        return self._store[uid][acct]

    def get_credentials(self, user_id: Optional[int] = None, account_type: Optional[str] = None):
        uid = int(user_id) if user_id is not None else 0
        acct = self._normalize_account_type(account_type) if account_type else None
        user_creds = self._store.get(uid, {})
        if acct:
            return user_creds.get(acct)
        return user_creds

    def clear_credentials(self, account_type: Optional[str] = None, user_id: Optional[int] = None):
        uid = int(user_id) if user_id is not None else 0
        acct = self._normalize_account_type(account_type) if account_type else None
        if uid not in self._store:
            return False
        if acct:
            self._store[uid].pop(acct, None)
            return True
        self._store.pop(uid, None)
        return True


class SimpleLogManager:
    def __init__(self):
        self._logs: List[Dict[str, Any]] = []

    def add(self, event_type: str, message: str, *, user_id: Optional[int] = None, **kwargs):
        self._logs.insert(
            0,
            {
                "type": event_type,
                "message": message,
                "user_id": str(user_id) if user_id is not None else None,
                "details": kwargs,
            },
        )

    def get_logs(
        self,
        limit: int = 50,
        account_type: Optional[str] = None,
        severity: Optional[str] = None,
        user_id: Optional[int] = None,
    ):
        logs = self._logs
        if user_id is not None:
            user_key = str(user_id)
            logs = [log for log in logs if str(log.get("user_id")) == user_key]
        return logs[:limit]


class FallbackTrader:
    def __init__(self):
        self.paper_trading = True
        self.real_trading_enabled = False
        self.futures_trading_enabled = False

    def get_real_trading_status(self):
        return {"enabled": bool(self.real_trading_enabled)}


class FallbackMarketDataService:
    """Minimal market data service for test/fallback mode."""
    
    def __init__(self, ultimate_trader: Any, optimized_trader: Any):
        self.ultimate_trader = ultimate_trader
        self.optimized_trader = optimized_trader
        self._user_traders: Dict[int, tuple[Any, Any]] = {}
    
    def _get_or_create_user_traders(self, user_id: int) -> tuple[Any, Any]:
        """Return per-user trader instances for multi-user isolation."""
        if user_id in self._user_traders:
            return self._user_traders[user_id]
        
        # In fallback mode, just return the shared traders
        # In production, this would create isolated instances
        self._user_traders[user_id] = (self.ultimate_trader, self.optimized_trader)
        return self.ultimate_trader, self.optimized_trader


def default_apply_credentials(account_type: str = "spot", creds: Optional[Dict[str, Any]] = None) -> bool:
    # Pretend we connected successfully
    return True


def default_get_status(include_connection: bool = True, include_logs: bool = True, user_id: Optional[int] = None):
    return {"ultimate_status": {}, "optimized_status": {}, "logs": [], "account_connections": {}}


__all__ = [
    "InMemoryCredentialsStore",
    "SimpleLogManager",
    "FallbackTrader",
    "FallbackMarketDataService",
    "default_apply_credentials",
    "default_get_status",
]
