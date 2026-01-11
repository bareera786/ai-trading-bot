"""Binance credential storage and logging helpers."""
from __future__ import annotations

import json
import os
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Union, TYPE_CHECKING
import time
from requests.exceptions import Timeout
import requests
import importlib

try:  # cryptography is required for credential encryption, but we guard imports for optional installs
    from cryptography.fernet import Fernet  # type: ignore
except Exception:  # pragma: no cover - handled gracefully downstream
    Fernet = None  # type: ignore

if TYPE_CHECKING:
    try:
        from binance.um_futures import UMFutures as BinanceFuturesClient  # type: ignore
    except Exception:
        BinanceFuturesClient = None  # type: ignore


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    return default


class CredentialCipher:
    """Thin wrapper around Fernet to encrypt/decrypt API secrets."""

    def __init__(self, key: Optional[Union[str, bytes]]) -> None:
        self._fernet = None
        normalized = key.encode() if isinstance(key, str) else key
        if normalized and Fernet:
            try:
                self._fernet = Fernet(normalized)
            except Exception:
                print(
                    "⚠️ Invalid BINANCE_CREDENTIAL_KEY provided; falling back to plaintext storage."
                )
        elif normalized and not Fernet:
            print(
                "⚠️ 'cryptography' package missing; install it to enable credential encryption."
            )

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def encrypt(self, value: str) -> str:
        if not value or not self._fernet:
            return value
        token = self._fernet.encrypt(value.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, value: Optional[str]) -> str:
        if not value:
            return ""
        if not self._fernet:
            return ""
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except Exception:
            return ""


from .pathing import BOT_PROFILE, PROJECT_ROOT_PATH, migrate_file_to_profile


class BinanceCredentialStore:
    """Lightweight, file-backed storage for Binance API credentials grouped by account type."""

    SUPPORTED_ACCOUNT_TYPES = {"spot", "futures"}

    def __init__(
        self,
        storage_dir: str = "bot_persistence",
        *,
        credential_file: Optional[str] = None,
        encryption_key: Optional[Union[str, bytes]] = None,
    ) -> None:
        self.storage_dir = storage_dir
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
        except PermissionError:
            # In containerized environments, we may not have permission to create directories
            # Continue with credential storage but warn that persistence may not work
            print(f"⚠️ Could not create credential storage directory {self.storage_dir}, credential persistence disabled")
        self.credential_file = credential_file or os.path.join(
            self.storage_dir, "binance_credentials.json"
        )
        self._migrate_legacy_files()
        self._lock = threading.RLock()
        self._cache: Optional[dict[str, dict[str, Any]]] = None
        key = (
            encryption_key
            if encryption_key is not None
            else os.getenv("BINANCE_CREDENTIAL_KEY")
        )
        self._cipher = CredentialCipher(key)
        self._decryption_warning_emitted = False

    def _migrate_legacy_files(self) -> None:
        """Move pre-profile credential files into the profile-scoped vault."""

        target = Path(self.credential_file)
        legacy_candidates = [
            Path(self.storage_dir) / "binance_credentials.json",
            PROJECT_ROOT_PATH / "bot_persistence" / "binance_credentials.json",
            PROJECT_ROOT_PATH
            / "bot_persistence"
            / BOT_PROFILE
            / "binance_credentials.json",
        ]
        for candidate in legacy_candidates:
            if candidate == target:
                continue
            if migrate_file_to_profile(candidate, target):
                break

    def _normalize_account_type(self, account_type: Optional[str]) -> str:
        if not account_type:
            return "spot"
        account_type = str(account_type).strip().lower()
        if account_type not in self.SUPPORTED_ACCOUNT_TYPES:
            return "spot"
        return account_type

    def _sanitize_entry(self, entry: Any, account_type: str = "spot") -> dict[str, Any]:
        if not isinstance(entry, dict):
            entry = {}

        decrypted_entry = self._hydrate_secret_fields(entry)
        sanitized = {
            "api_key": (decrypted_entry.get("api_key") or "").strip(),
            "api_secret": (decrypted_entry.get("api_secret") or "").strip(),
            "testnet": _coerce_bool(decrypted_entry.get("testnet", True), default=True),
            "note": decrypted_entry.get("note") or "",
            "updated_at": decrypted_entry.get("updated_at"),
            "account_type": self._normalize_account_type(
                decrypted_entry.get("account_type") or account_type
            ),
            "encrypted": bool(decrypted_entry.get("encrypted")),
        }
        if sanitized["updated_at"] is None and sanitized["api_key"]:
            sanitized["updated_at"] = datetime.utcnow().isoformat()
        return sanitized

    def _hydrate_secret_fields(self, entry: dict[str, Any]) -> dict[str, Any]:
        hydrated = dict(entry or {})
        encrypted_flag = bool(hydrated.get("encrypted"))
        encrypted_key = hydrated.get("api_key_encrypted")
        encrypted_secret = hydrated.get("api_secret_encrypted")
        stored_encrypted = bool(encrypted_flag or encrypted_key or encrypted_secret)

        if stored_encrypted:
            hydrated["api_key"] = self._decrypt_or_warn(
                encrypted_key or hydrated.get("api_key"),
                field="api_key",
                encrypted=True,
            )
            hydrated["api_secret"] = self._decrypt_or_warn(
                encrypted_secret or hydrated.get("api_secret"),
                field="api_secret",
                encrypted=True,
            )
            hydrated["encrypted"] = True
        else:
            hydrated["api_key"] = hydrated.get("api_key") or ""
            hydrated["api_secret"] = hydrated.get("api_secret") or ""
            hydrated["encrypted"] = False
        return hydrated

    def _decrypt_or_warn(self, value: Any, *, field: str, encrypted: bool) -> str:
        token = (value or "").strip()
        if not token:
            return ""
        if self._cipher.enabled:
            decrypted = self._cipher.decrypt(token)
            if decrypted:
                return decrypted
            return ""
        if encrypted and not self._decryption_warning_emitted:
            print(
                "⚠️ Encrypted Binance credentials detected but BINANCE_CREDENTIAL_KEY is missing;"
                " returning blank secrets for security."
            )
            self._decryption_warning_emitted = True
        return ""

    def _normalize_data(self, data: Any) -> dict[str, Any]:
        """Return a canonical in-memory representation.

        Canonical format:
          {
            "users": {"<user_id>": {"spot": <entry>, "futures": <entry>}},
            "spot": <entry>,
            "futures": <entry>
          }

        Supports legacy formats:
          - {"spot": {...}, "futures": {...}}
          - {"api_key": ..., "api_secret": ...} (spot)
          - {"<user_id>": {"spot": {...}}, ...} (older per-user flat map)
        """

        normalized: dict[str, Any] = {}
        if not isinstance(data, dict):
            return normalized

        # Per-user scoped format: {"users": {"1": {"spot": {...}}}}
        users_in = data.get("users")
        if isinstance(users_in, dict):
            users_map: dict[str, dict[str, Any]] = {}
            for user_key, user_map in users_in.items():
                if not isinstance(user_map, dict):
                    continue
                user_id_key = str(user_key)
                acct_map: dict[str, Any] = {}
                for acct_key, entry in user_map.items():
                    acct_key_str = str(acct_key).strip().lower()
                    if acct_key_str not in self.SUPPORTED_ACCOUNT_TYPES:
                        # Allow extra keys (e.g., legacy convenience fields like
                        # api_key_encrypted at the user level).
                        continue
                    acct = self._normalize_account_type(acct_key_str)
                    acct_map[acct] = self._sanitize_entry(entry, acct)
                users_map[user_id_key] = acct_map
            normalized["users"] = users_map

        # Legacy: single entry implies spot
        if "api_key" in data or "api_secret" in data:
            normalized["spot"] = self._sanitize_entry(data, "spot")
            return normalized

        # Legacy/global account mapping + support older flat user maps
        users_from_flat: dict[str, dict[str, Any]] = {}
        saw_non_account_key = False

        for key, value in data.items():
            if key == "users":
                continue

            key_str = str(key)
            if key_str in self.SUPPORTED_ACCOUNT_TYPES:
                acct = self._normalize_account_type(key_str)
                normalized[acct] = self._sanitize_entry(value, acct)
                continue

            # If it isn't an account type and looks like a per-user mapping, capture it.
            if isinstance(value, dict):
                saw_non_account_key = True
                acct_map: dict[str, Any] = {}
                for acct_key, entry in value.items():
                    acct = self._normalize_account_type(acct_key)
                    acct_map[acct] = self._sanitize_entry(entry, acct)
                users_from_flat[key_str] = acct_map
            else:
                saw_non_account_key = True

        # If the file was an older per-user flat map, fold it into canonical users.
        if saw_non_account_key and users_from_flat:
            existing_users = normalized.get("users")
            if not isinstance(existing_users, dict):
                existing_users = {}
            # Merge (do not overwrite existing canonical users unless missing)
            for user_id_key, acct_map in users_from_flat.items():
                if user_id_key not in existing_users:
                    existing_users[user_id_key] = acct_map
            normalized["users"] = existing_users

        return normalized

    def _ensure_cache(self) -> dict[str, dict[str, Any]]:
        if self._cache is None:
            self._cache = self._load_from_disk()
        return self._cache

    def _load_from_disk(self) -> dict[str, dict[str, Any]]:
        if not os.path.exists(self.credential_file):
            return {}
        try:
            with open(self.credential_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                return self._normalize_data(data)
        except (
            Exception
        ) as exc:  # pragma: no cover - defensive logging handled upstream
            print(f"⚠️ Unable to load Binance credentials: {exc}")
        return {}

    def list_user_ids(self) -> list[int]:
        """Return user ids that have at least one stored credential record."""

        with self._lock:
            data = self._load_from_disk()
        users = data.get("users") if isinstance(data, dict) else None
        if not isinstance(users, dict):
            return []

        out: list[int] = []
        for key, value in users.items():
            try:
                user_id = int(key)
            except (TypeError, ValueError):
                continue
            if not isinstance(value, dict):
                continue
            for account_key in ("spot", "futures"):
                entry = value.get(account_key) or {}
                if not isinstance(entry, dict):
                    continue
                if (entry.get("api_key") or entry.get("api_key_encrypted")) and (
                    entry.get("api_secret") or entry.get("api_secret_encrypted")
                ):
                    out.append(user_id)
                    break
        return sorted(set(out))

    def _serialize_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        serialized = dict(entry)
        if self._cipher.enabled:
            serialized["api_key_encrypted"] = self._cipher.encrypt(
                serialized.get("api_key", "")
            )
            serialized["api_secret_encrypted"] = self._cipher.encrypt(
                serialized.get("api_secret", "")
            )
            serialized.pop("api_key", None)
            serialized.pop("api_secret", None)
            serialized["encrypted"] = True
        else:
            serialized["encrypted"] = False
        return serialized

    def _write_to_disk(self, data: dict[str, Any]) -> None:
        normalized = self._normalize_data(data)
        to_write: dict[str, Any] = {}

        users = normalized.get("users")
        if isinstance(users, dict):
            users_out: dict[str, dict[str, Any]] = {}
            for user_id_key, user_map in users.items():
                if not isinstance(user_map, dict):
                    continue
                serialized_user: dict[str, Any] = {
                    self._normalize_account_type(acct_key): self._serialize_entry(entry)
                    for acct_key, entry in user_map.items()
                    if isinstance(entry, dict)
                }

                # Backward-compatible convenience fields (some tests/legacy tooling
                # expect encryption markers at the user root).
                spot_entry = serialized_user.get("spot")
                if isinstance(spot_entry, dict) and spot_entry.get("encrypted"):
                    serialized_user["encrypted"] = True
                    if spot_entry.get("api_key_encrypted"):
                        serialized_user["api_key_encrypted"] = spot_entry.get(
                            "api_key_encrypted"
                        )
                    if spot_entry.get("api_secret_encrypted"):
                        serialized_user["api_secret_encrypted"] = spot_entry.get(
                            "api_secret_encrypted"
                        )

                users_out[str(user_id_key)] = serialized_user
            to_write["users"] = users_out

        # Preserve global (legacy) credentials if present.
        for acct in self.SUPPORTED_ACCOUNT_TYPES:
            if acct in normalized and isinstance(normalized.get(acct), dict):
                to_write[acct] = self._serialize_entry(normalized[acct])

        tmp_file = f"{self.credential_file}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as handle:
            json.dump(to_write, handle, indent=2, default=str)
        os.replace(tmp_file, self.credential_file)

    def get_credentials(
        self,
        account_type: Optional[str] = None,
        user_id: Optional[Union[int, str]] = None,
    ) -> dict[str, Any]:
        """Get credentials for a given account type or user. If user_id is provided, returns that user's credentials.

        If no arguments are provided, returns the global (legacy) credential mapping.
        """
        with self._lock:
            cache = self._ensure_cache()
            # Per-user scoped credentials
            if user_id is not None:
                users = cache.get("users") or {}
                user_key = str(user_id)
                user_map = users.get(user_key) or {}
                if account_type:
                    return dict(
                        user_map.get(self._normalize_account_type(account_type)) or {}
                    )
                # Return all for user
                return {
                    key: dict(value)
                    for key, value in (
                        user_map.items() if isinstance(user_map, dict) else []
                    )
                }

            # Legacy/global behaviour
            if account_type:
                key = self._normalize_account_type(account_type)
                return dict(cache.get(key) or {})
            return {
                key: dict(value)
                for key, value in cache.items()
                if key in self.SUPPORTED_ACCOUNT_TYPES and isinstance(value, dict)
            }

    def save_credentials(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        note: Optional[str] = None,
        account_type: str = "spot",
        user_id: Optional[Union[int, str]] = None,
    ) -> dict[str, Any]:
        payload = {
            "api_key": api_key or "",
            "api_secret": api_secret or "",
            "testnet": _coerce_bool(testnet, default=True),
            "updated_at": datetime.utcnow().isoformat(),
            "note": note or "",
            "account_type": self._normalize_account_type(account_type),
        }
        payload = self._sanitize_entry(payload, payload["account_type"])
        account_key = payload["account_type"]
        with self._lock:
            cache = self._ensure_cache()
            if user_id is not None:
                users = cache.get("users") or {}
                user_key = str(user_id)
                user_map = users.get(user_key) or {}
                user_map[account_key] = payload
                users[user_key] = user_map
                cache["users"] = users
            else:
                cache[account_key] = payload
            self._write_to_disk(cache)
            if self._cipher.enabled:
                if user_id is not None:
                    cache.get("users", {}).get(str(user_id), {}).get(account_key, {})[
                        "encrypted"
                    ] = True
                else:
                    cache[account_key]["encrypted"] = True
            self._cache = dict(cache)
        return dict(payload)

    @property
    def encryption_enabled(self) -> bool:
        return self._cipher.enabled

    def clear_credentials(
        self,
        account_type: Optional[str] = None,
        user_id: Optional[Union[int, str]] = None,
    ) -> dict[str, dict[str, Any]]:
        with self._lock:
            cache = self._ensure_cache()
            if user_id is not None:
                users = cache.get("users") or {}
                user_key = str(user_id)
                user_map = users.get(user_key) or {}
                if account_type:
                    user_map.pop(self._normalize_account_type(account_type), None)
                else:
                    user_map.clear()
                users[user_key] = user_map
                cache["users"] = users
            else:
                if account_type:
                    cache.pop(self._normalize_account_type(account_type), None)
                else:
                    cache.clear()
            self._write_to_disk(cache)
            self._cache = dict(cache)
        return {}


class BinanceLogManager:
    """Thread-safe in-memory log store for Binance connectivity events."""

    def __init__(
        self,
        max_entries: int = 200,
        dashboard_data_provider: Optional[Callable[[], dict[str, Any]]] = None,
    ) -> None:
        self.max_entries = max_entries
        self._lock = threading.RLock()
        self._logs: deque[dict[str, Any]] = deque(maxlen=max_entries)
        self._dashboard_data_provider = dashboard_data_provider

    def attach_dashboard_data(
        self, provider: Union[Callable[[], dict[str, Any]], dict[str, Any]]
    ) -> None:
        if callable(provider):
            self._dashboard_data_provider = provider
        else:
            self._dashboard_data_provider = lambda: provider  # type: ignore[assignment]

    def add(
        self,
        event_type: str,
        message: str,
        severity: str = "info",
        account_type: str = "spot",
        details: Optional[dict[str, Any]] = None,
        user_id: Optional[Union[int, str]] = None,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(user_id) if user_id is not None else None,
            "event_type": event_type,
            "message": message,
            "severity": severity,
            "account_type": account_type or "spot",
            "details": details or {},
        }
        with self._lock:
            self._logs.append(entry)
            self._push_to_dashboard()
        return entry

    def get_logs(
        self,
        limit: int = 50,
        account_type: Optional[str] = None,
        severity: Optional[str] = None,
        user_id: Optional[Union[int, str]] = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            logs_iterable = list(reversed(self._logs))
            if user_id is not None:
                user_key = str(user_id)
                logs_iterable = [
                    log for log in logs_iterable if str(log.get("user_id")) == user_key
                ]
            if account_type:
                acct = str(account_type).strip().lower()
                logs_iterable = [
                    log for log in logs_iterable if log.get("account_type") == acct
                ]
            if severity:
                sev = str(severity).strip().lower()
                logs_iterable = [
                    log
                    for log in logs_iterable
                    if str(log.get("severity", "")).lower() == sev
                ]
            return logs_iterable[
                : max(1, int(limit) if isinstance(limit, (int, float)) else 50)
            ]

    def _push_to_dashboard(self) -> None:
        if not self._dashboard_data_provider:
            return
        try:
            dashboard_data = self._dashboard_data_provider()
        except Exception:
            return
        if not isinstance(dashboard_data, dict):
            return
        dashboard_data["binance_logs"] = list(reversed(self._logs))[:50]


class BinanceCredentialService:
    """Encapsulates credential application flows and status reporting."""

    def __init__(
        self,
        credentials_store: BinanceCredentialStore,
        ultimate_trader: Any,
        optimized_trader: Any,
        *,
        futures_manual_lock: Optional[Union[threading.RLock, threading.Lock]] = None,
        futures_manual_settings: Optional[dict[str, Any]] = None,
        binance_log_manager: Optional[BinanceLogManager] = None,
        dashboard_data_provider: Optional[
            Union[Callable[[], dict[str, Any]], dict[str, Any]]
        ] = None,
        coerce_bool: Optional[Callable[[Any, bool], bool]] = None,
        terms_accepted: Optional[bool] = None,
    ) -> None:
        self.credentials_store = credentials_store
        self.ultimate_trader = ultimate_trader
        self.optimized_trader = optimized_trader
        self.futures_manual_lock = futures_manual_lock
        self.futures_manual_settings = futures_manual_settings
        self.binance_log_manager = binance_log_manager
        self._dashboard_data_provider = dashboard_data_provider
        self._coerce_bool = coerce_bool or _coerce_bool
        self._terms_override = terms_accepted

    def attach_dashboard_data(
        self, provider: Union[Callable[[], dict[str, Any]], dict[str, Any]]
    ) -> None:
        if callable(provider):
            self._dashboard_data_provider = provider
        else:
            self._dashboard_data_provider = lambda: provider  # type: ignore[assignment]

    @staticmethod
    def mask_api_key(api_key: Any) -> Optional[str]:
        if not api_key:
            return None
        api_key = str(api_key)
        if len(api_key) <= 8:
            return "****"
        return f"{api_key[:4]}…{api_key[-4:]}"

    def initialize_all(self) -> None:
        self.apply_credentials("spot")
        self.apply_credentials("futures")

    def apply_credentials(
        self,
        account_type: str = "spot",
        creds: Optional[dict[str, Any]] = None,
        *,
        user_id: Optional[Union[int, str]] = None,
    ) -> bool:
        account_key = self.credentials_store._normalize_account_type(account_type)
        if creds is None or not isinstance(creds, dict) or not creds.get("api_key"):
            creds_map = (
                self.credentials_store.get_credentials(user_id=user_id)
                if user_id is not None
                else self.credentials_store.get_credentials()
            )
            creds = creds_map.get(account_key) if isinstance(creds_map, dict) else {}

        if not creds:
            return False

        api_key = creds.get("api_key")
        api_secret = creds.get("api_secret")
        testnet = _coerce_bool(creds.get("testnet", True), default=True)
        if not api_key or not api_secret:
            return False

        # When called in a user-scoped context (multi-tenant dashboard), do not
        # mutate the global trader instances. Instead, validate credentials and
        # let per-user trade execution use isolated client instances.
        if user_id is not None:
            result = self.test_credentials(
                str(api_key),
                str(api_secret),
                account_type=account_key,
                testnet=testnet,
            )
            return bool(result.get("connected"))

        if not self._allowed_for_live_trading(testnet):
            self._log_event(
                "TERMS_BLOCKED",
                "Live Binance trading blocked until BINANCE_TERMS_ACCEPTED=1 is configured.",
                severity="warning",
                account_type=account_key,
                details={"testnet": testnet, "terms_accepted": self._terms_accepted()},
            )
            return False

        if account_key == "spot":
            connected_any = False
            for trader in filter(None, (self.ultimate_trader, self.optimized_trader)):
                enable = getattr(trader, "enable_real_trading", None)
                if callable(enable):
                    connected = bool(
                        enable(api_key=api_key, api_secret=api_secret, testnet=testnet)
                    )
                    connected_any = connected_any or connected
            self._log_event(
                "CREDENTIAL_APPLY",
                "Spot credentials applied to trading engines."
                if connected_any
                else "Failed to activate spot credentials for trading engines.",
                severity="success" if connected_any else "error",
                account_type="spot",
                details={"testnet": testnet},
            )
            return connected_any

        if account_key == "futures":
            connected = False
            if self.ultimate_trader:
                enable = getattr(self.ultimate_trader, "enable_futures_trading", None)
                if callable(enable):
                    connected = bool(
                        enable(api_key=api_key, api_secret=api_secret, testnet=testnet)
                    )
            self._update_futures_dashboard(connected=connected, testnet=testnet)
            self._log_event(
                "FUTURES_CREDENTIAL_APPLY",
                "Futures credentials applied to manual trading engine."
                if connected
                else "Failed to activate futures credentials.",
                severity="success" if connected else "error",
                account_type="futures",
                details={"testnet": testnet},
            )
            return connected

        self._log_event(
            "CREDENTIAL_STORED",
            f"Stored credentials for {account_key.upper()} trading.",
            severity="info",
            account_type=account_key,
            details={"testnet": testnet},
        )
        return True

    def get_status(
        self,
        include_connection: bool = False,
        include_logs: bool = False,
        user_id: Optional[Union[int, str]] = None,
    ) -> dict[str, Any]:
        # Allow requesting status scoped to a particular user (if provided)
        creds_map = (
            self.credentials_store.get_credentials(user_id=user_id)
            if user_id is not None
            else self.credentials_store.get_credentials()
        )
        accounts: dict[str, dict[str, Any]] = {}

        if isinstance(creds_map, dict):
            for key, value in creds_map.items():
                account_key = self.credentials_store._normalize_account_type(key)
                entry = value or {}
                has_credentials = bool(entry.get("api_key") and entry.get("api_secret"))
                accounts[account_key] = {
                    "account_type": account_key,
                    "has_credentials": has_credentials,
                    "testnet": _coerce_bool(
                        entry.get("testnet", True), default=True
                    ),
                    "masked_key": self.mask_api_key(entry.get("api_key"))
                    if has_credentials
                    else None,
                    "note": entry.get("note") or "",
                    "updated_at": entry.get("updated_at"),
                    "connected": False,
                    "last_error": None,
                    "encrypted": bool(entry.get("encrypted")),
                    "requires_terms_acceptance": False,
                }

        for default_key in self.credentials_store.SUPPORTED_ACCOUNT_TYPES:
            accounts.setdefault(
                default_key,
                {
                    "account_type": default_key,
                    "has_credentials": False,
                    "testnet": True,
                    "masked_key": None,
                    "note": "",
                    "updated_at": None,
                    "connected": False,
                    "last_error": None,
                    "encrypted": False,
                    "requires_terms_acceptance": False,
                },
            )

        if include_connection and user_id is not None:
            for account_key, entry in accounts.items():
                if not entry.get("has_credentials"):
                    continue
                try:
                    # Re-fetch the concrete credential record so we get unmasked fields.
                    creds = self.credentials_store.get_credentials(
                        account_key, user_id=user_id
                    )
                    testnet = _coerce_bool(creds.get("testnet", True), default=True)
                    result = self.test_credentials(
                        str(creds.get("api_key") or ""),
                        str(creds.get("api_secret") or ""),
                        account_type=account_key,
                        testnet=testnet,
                    )
                    entry["connected"] = bool(result.get("connected"))
                    entry["last_error"] = result.get("error")
                except Exception as exc:  # pragma: no cover
                    entry["connected"] = False
                    entry["last_error"] = str(exc)

        active_account = (
            "spot" if "spot" in accounts else next(iter(accounts.keys()), "spot")
        )

        ultimate_status = None
        optimized_status = None
        futures_status = None
        if include_connection:
            ultimate_status = self._safe_trader_status(
                self.ultimate_trader, "get_real_trading_status"
            )
            optimized_status = self._safe_trader_status(
                self.optimized_trader, "get_real_trading_status"
            )
            futures_status = self._safe_trader_status(
                self.ultimate_trader, "get_futures_trading_status"
            )

            spot_account = accounts.get("spot")
            if spot_account is not None:
                ultimate_connected = (
                    bool(ultimate_status.get("connected")) if ultimate_status else False
                )
                optimized_connected = (
                    bool(optimized_status.get("connected"))
                    if optimized_status
                    else False
                )
                spot_account["ultimate_connected"] = ultimate_connected
                spot_account["optimized_connected"] = optimized_connected
                spot_account["connected"] = ultimate_connected or optimized_connected
                last_error = None
                if ultimate_status:
                    last_error = ultimate_status.get("last_error") or last_error
                if optimized_status and not last_error:
                    last_error = optimized_status.get("last_error")
                spot_account["last_error"] = last_error
                spot_account["requires_terms_acceptance"] = not spot_account.get(
                    "testnet", True
                )

            futures_account = accounts.get("futures")
            if futures_account is not None:
                futures_connected = (
                    bool(futures_status.get("connected")) if futures_status else False
                )
                futures_account["connected"] = futures_connected
                futures_account["last_error"] = (
                    futures_status.get("last_error") if futures_status else None
                )
                futures_account["testnet"] = _coerce_bool(
                    futures_status.get("testnet")
                    if futures_status
                    else futures_account.get("testnet"),
                    default=futures_account.get("testnet", True),
                )
                futures_account["requires_terms_acceptance"] = not futures_account.get(
                    "testnet", True
                )

        summary = accounts.get(active_account, {}).copy()
        status = {
            "accounts": accounts,
            "active_account": active_account,
            "has_credentials": summary.get("has_credentials", False),
            "testnet": _coerce_bool(summary.get("testnet"), default=True),
            "masked_key": summary.get("masked_key"),
            "note": summary.get("note"),
            "updated_at": summary.get("updated_at"),
            "compliance": {
                "terms_accepted": self._terms_accepted(),
                "credential_encryption": self.credentials_store.encryption_enabled,
            },
        }

        if include_connection:
            status["ultimate_status"] = ultimate_status
            status["optimized_status"] = optimized_status
            status["futures_status"] = futures_status
            status["ultimate_connected"] = (
                bool(ultimate_status.get("connected")) if ultimate_status else False
            )
            status["optimized_connected"] = (
                bool(optimized_status.get("connected")) if optimized_status else False
            )
            status["futures_connected"] = (
                bool(futures_status.get("connected")) if futures_status else False
            )
            status["ultimate_last_error"] = (
                ultimate_status.get("last_error") if ultimate_status else None
            )
            status["optimized_last_error"] = (
                optimized_status.get("last_error") if optimized_status else None
            )
            status["futures_last_error"] = (
                futures_status.get("last_error") if futures_status else None
            )

        if include_logs and self.binance_log_manager:
            status["logs"] = self.binance_log_manager.get_logs(
                limit=50,
                user_id=user_id,
            )
        else:
            status["logs"] = []

        status["any_credentials"] = any(
            acc.get("has_credentials") for acc in accounts.values()
        )
        return status

    def _allowed_for_live_trading(self, testnet: bool) -> bool:
        if testnet:
            return True
        return self._terms_accepted()

    def _terms_accepted(self) -> bool:
        if self._terms_override is not None:
            return bool(self._terms_override)
        env_value = os.getenv("BINANCE_TERMS_ACCEPTED")
        return _coerce_bool(env_value, default=False)

    def _safe_trader_status(
        self, trader: Any, method_name: str
    ) -> Optional[dict[str, Any]]:
        if not trader:
            return None
        method = getattr(trader, method_name, None)
        if not callable(method):
            return None
        try:
            res = method()
            if isinstance(res, dict):
                return res or {}
            return {}
        except Exception:
            return {"connected": False, "last_error": f"{method_name}_error"}

    def test_credentials(
        self,
        api_key: str,
        api_secret: str,
        account_type: str = "spot",
        testnet: bool = True,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """Attempt a lightweight validation of API credentials.

        Returns a dict with keys: connected (bool), error (optional str).
        """
        try:
            account_key = self.credentials_store._normalize_account_type(account_type)
            if account_key == "futures":
                # Import Binance futures client dynamically to avoid hard failure
                # in environments where the optional `binance` package isn't installed.
                try:
                    BinanceClient = importlib.import_module("binance.client").Client
                except Exception:
                    BinanceClient = None

                try:
                    BinanceFuturesClient = importlib.import_module("binance.um_futures").UMFutures
                except Exception:
                    BinanceFuturesClient = None

                from app.services.trading import BinanceFuturesTrader

                if BinanceFuturesClient is None or BinanceClient is None:
                    return {
                        "connected": False,
                        "error": "Missing optional 'binance' SDK (binance.client or binance.um_futures).",
                    }

                trader = BinanceFuturesTrader(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=testnet,
                    binance_um_futures_cls=BinanceFuturesClient,
                    binance_rest_client_cls=BinanceClient,
                    coerce_bool=self._coerce_bool,
                )
                connected = bool(trader.connect())
                status = trader.get_status() if hasattr(trader, "get_status") else {}
                if not connected:
                    return {"connected": False, "error": trader.last_error, "detail": status}
                return {"connected": bool(status.get("connected")), "detail": status}

            # Spot
            from app.services.trading import RealBinanceTrader
            from binance.client import Client as BinanceClient
            from binance.exceptions import BinanceAPIException

            trader = RealBinanceTrader(
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet,
                account_type="spot",
                binance_client_cls=BinanceClient,
                api_exception_cls=BinanceAPIException,
            )
            connected = bool(trader.connect())
            status = trader.get_status() if hasattr(trader, "get_status") else {}
            if not connected:
                return {"connected": False, "error": trader.last_error, "detail": status}
            return {"connected": bool(status.get("connected")), "detail": status}
        except Exception as exc:
            return {"connected": False, "error": str(exc)}

    def _log_event(
        self,
        event_type: str,
        message: str,
        *,
        severity: str,
        account_type: str,
        details: dict[str, Any],
    ) -> None:
        if not self.binance_log_manager:
            return
        self.binance_log_manager.add(
            event_type,
            message,
            severity=severity,
            account_type=account_type,
            details=details,
        )

    def _update_futures_dashboard(self, *, connected: bool, testnet: bool) -> None:
        if not self.futures_manual_lock or self.futures_manual_settings is None:
            return
        with self.futures_manual_lock:
            self.futures_manual_settings["testnet"] = testnet
            self.futures_manual_settings["last_error"] = (
                None if connected else "Failed to connect futures trader"
            )
            dashboard_data = self._get_dashboard_data()
            if not isinstance(dashboard_data, dict):
                return
            dashboard_data["futures_manual"] = self.futures_manual_settings
            system_status = dashboard_data.get("system_status") or {}
            system_status["futures_trading_ready"] = bool(connected)
            system_status[
                "futures_manual_auto_trade"
            ] = self.futures_manual_settings.get("auto_trade_enabled", False)
            dashboard_data["system_status"] = system_status

    def _get_dashboard_data(self) -> Optional[dict[str, Any]]:
        provider = self._dashboard_data_provider
        if provider is None:
            return None
        if callable(provider):
            try:
                return provider()
            except Exception:
                return None
        return provider

    def rotate_credentials(
        self, account_type: str = "spot", reason: str = "scheduled"
    ) -> bool:
        """
        Rotate Binance API credentials for security.

        This method should be called periodically to renew API keys
        and maintain security best practices.

        Args:
            account_type: Type of account ("spot" or "futures")
            reason: Reason for rotation (e.g., "scheduled", "compromised", "expired")

        Returns:
            bool: True if rotation was successful, False otherwise
        """
        try:
            # Get current credentials
            creds_map = self.credentials_store.get_credentials()
            account_key = self.credentials_store._normalize_account_type(account_type)
            creds_record = creds_map.get(account_key) if isinstance(creds_map, dict) else {}

            if not creds_record or not creds_record.get("api_key"):
                self._log_event(
                    "ROTATION_FAILED",
                    f"No credentials found for {account_type} account",
                    severity="warning",
                    account_type=account_key,
                    details={"reason": reason, "rotation_type": "credential_rotation"},
                )
                return False

            # Log rotation attempt
            masked_key = self.mask_api_key(creds_record.get("api_key"))
            self._log_event(
                "ROTATION_STARTED",
                f"Starting credential rotation for {account_type} account ({masked_key})",
                severity="info",
                account_type=account_key,
                details={
                    "reason": reason,
                    "rotation_type": "credential_rotation",
                    "old_key_masked": masked_key,
                },
            )

            # Note: In a production system, this would integrate with
            # Binance's API key management endpoints to automatically
            # generate new keys. For now, we log the rotation event
            # and mark the credentials as needing manual renewal.

            # Update the credential metadata to indicate rotation needed
            updated_creds = creds_record.copy()
            updated_creds["rotation_needed"] = True
            updated_creds["last_rotation_check"] = datetime.utcnow().isoformat()
            updated_creds["rotation_reason"] = reason

            # Save updated credentials (store rotation flag in note)
            success = self.credentials_store.save_credentials(
                api_key=creds_record["api_key"],
                api_secret=creds_record["api_secret"],
                testnet=creds_record.get("testnet", True),
                account_type=account_type,
                note=f"Rotation needed: {reason} - {creds_record.get('note', '')}",
            )

            if success:
                self._log_event(
                    "ROTATION_COMPLETED",
                    f"Credential rotation metadata updated for {account_type} account",
                    severity="info",
                    account_type=account_key,
                    details={
                        "reason": reason,
                        "rotation_type": "credential_rotation",
                        "action": "metadata_updated",
                    },
                )
                return True
            else:
                self._log_event(
                    "ROTATION_FAILED",
                    f"Failed to update rotation metadata for {account_type} account",
                    severity="error",
                    account_type=account_key,
                    details={"reason": reason, "rotation_type": "credential_rotation"},
                )
                return False

        except Exception as e:
            self._log_event(
                "ROTATION_ERROR",
                f"Unexpected error during credential rotation: {str(e)}",
                severity="error",
                account_type=account_type,
                details={
                    "reason": reason,
                    "rotation_type": "credential_rotation",
                    "error_type": type(e).__name__,
                },
            )
            return False

    @staticmethod
    def fetch_with_retries(url, params=None, timeout=30.0, retries=2):
        """Fetch data from Binance API with retries for timeout errors."""
        for attempt in range(retries + 1):
            try:
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except Timeout as e:
                if attempt < retries:
                    time.sleep(1)  # Fixed delay between retries
                    continue
                raise e  # Raise the exception if retries are exhausted

    # Example usage in existing methods
    def fetch_ticker_data(self, symbol):
        url = f"https://api.binance.com/api/v3/ticker/24hr"
        params = {"symbol": symbol}
        return self.fetch_with_retries(url, params=params, timeout=30.0)
