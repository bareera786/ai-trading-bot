# System (Automated) Trade Recording

Overview

Automated/system trades were previously written only to the JSON-based comprehensive trade journal (`comprehensive_trades.json`), which meant the Admin per-user analytics (which query the `user_trade` DB table) did not show automated trades. To make automated trades visible in admin views, the bot can now optionally record system trades to the DB.

How to enable

- Set these keys in `TRADING_CONFIG` (or via admin overrides):
  - `record_system_trades_to_db`: `True` to enable recording
  - `system_trade_user_id`: the `User.id` of the account to attribute system trades to (required when enabling)

Notes & safety

- The recording is a best-effort, config-gated call to the existing `record_user_trade(...)` helper. If `system_trade_user_id` is not set, the system will not write DB rows.
- The default configuration remains disabled to avoid creating unwanted DB rows.
- Admin dashboard now includes a merged view of the JSON trade journal and DB `user_trade` rows via `/api/trades?merge_db=1` (admin-only). The dashboard UI will automatically request the merged view for admin users.

Testing

- A unit test `tests/test_system_trade_recording.py` verifies that when enabled and a valid `system_trade_user_id` is configured, automated trades are persisted to `user_trade` and attributed correctly.

Deployment

- After toggling the config, restart the service and verify the Admin dashboard shows recently-recorded system trades and that trade counts match the JSON journal (allowing for deduplication differences).
