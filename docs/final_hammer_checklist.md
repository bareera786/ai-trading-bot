# FINAL_HAMMER Launch Checklist

`FINAL_HAMMER=TRUE` is the last gate between safe sandboxing and **real-money executions**. Keep it `FALSE` until every control below has been satisfied, logged, and signed off. The steps mirror how we operate staging → production cutovers so you can run the same playbook locally or on a VPS.

## Safety Contract (read before touching the flag)

- Never enable FINAL_HAMMER unless Binance keys, balances, and account modes have been double-checked in the dashboard *and* in the exchange UI.
- Always ship a fresh asset bundle (`npm run build:assets`) so browsers load the hashed JS/CSS referenced via `asset_url()`. Stale assets mean stale telemetry.
- Validate the Futures Manual Service: `/api/futures/manual` should show the selected symbol, leverage, and timestamps; `/api/futures/manual/select` + `/api/futures/manual/toggle` must respond instantly without stack traces.
- Run the regression set listed below every time. If any test fails, keep FINAL_HAMMER at `FALSE` and fix the issue first.

## Stage 1 – Environment prep

1. **Sync configuration:** `cp config/deploy.env.example config/deploy.env` (if new machine) and fill in keys, DB URLs, telemetry settings, etc.
2. **Dependencies:**
   - Python: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
   - Node: `npm install` (installs esbuild + asset helper scripts)
3. **Asset build:** `npm run build:assets` → verify `app/static/dist/manifest.json` contains hashed filenames and matches what the templates serve through `asset_url()`.
4. **Persistence snapshot:** copy `bot_persistence/` to an off-box location in case you need to roll back state files.
5. **Credentials:**
   - Confirm `BINANCE_TERMS_ACCEPTED=1` is set when going live.
   - Load real API keys via the dashboard credential modal (they’re encrypted with Fernet before touching disk).

## Stage 2 – Manual control-plane verification

1. Hit `GET /api/futures/manual` – expect `available_symbols`, `selected_symbol`, and `timestamp`.
2. POST to `/api/futures/manual/select` with `{"symbol": "BTCUSDT", "leverage": 5, "order_size_usdt": 200}` – the response should echo the sanitized values and the dashboard should refresh immediately.
3. Toggle trading with `/api/futures/manual/toggle` using `{ "enable": true, "mode": "manual" }`. If the futures trader is disconnected you will receive a descriptive 400 response and the service will revert the flag.
4. Check `bot_persistence/logs/bot.log` or the dashboard system-status widget for matching `futures_manual_auto_trade` + `futures_trading_ready` states.

## Stage 3 – Regression suite (required before flipping the switch)

Run the following from the repo root with your virtualenv active:

```bash
pytest tests/test_public_landing.py \
       tests/test_public_subscriptions.py \
       tests/test_user_api.py \
       tests/test_toggle.py \
       tests/test_futures_toggle.py
```

Add any domain-specific tests (e.g., `tests/test_persistence_system.py`) that touch the components you edited for the release. Keep the terminal output attached to your deployment record.

## Stage 4 – Enable FINAL_HAMMER

1. Set the flag: `export FINAL_HAMMER=TRUE` (or update the value inside `config/deploy.env`).
2. Restart the runtime (`flask run`, `systemctl restart ai-trading-bot`, or `./start_server.py`).
3. Watch `server.log` and the dashboard for at least one full futures polling cycle. The Futures Manual Service should report `auto_trade_enabled=true` if you toggled it on in Stage 2.
4. Execute a tiny live order (e.g., $10 notional) to confirm connectivity, then gradually lift position sizes.

## Rollback procedure

If anything looks wrong:

1. Set `FINAL_HAMMER=FALSE` and restart the service – this instantly blocks new live orders.
2. Disable manual trading via `/api/futures/manual/toggle` to ensure the dashboard reflects the safe state.
3. Re-run the regression suite and inspect logs; revert to the previous `bot_persistence` snapshot if configuration drift is suspected.
4. File a post-mortem entry in `docs/self_improvement/` (or your internal tracker) before attempting another launch.

Document every FINAL_HAMMER event (who, when, why, rollback status) so audits remain painless and you can prove due diligence to Binance or compliance reviewers.
