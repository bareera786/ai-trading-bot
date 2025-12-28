# Binance Compliance & Submission Guide

This document captures the safeguards and artifacts required to present the AI Trading Bot to Binance Academy and the official Binance API ecosystem. It translates Binance's API license requirements, data security expectations, and best practices into a concrete checklist for this repository.

---

## 1. Platform Summary
- **Name:** Ultimate AI Trading Bot (spot + futures automation)
- **Tech stack:** Python 3.9+, Flask, SQLAlchemy, python-binance, Socket.IO.
- **Deployment modes:**
  - `BINANCE_TESTNET=1` keeps the bot in paper-trading mode (Binance Testnet endpoints).
  - `FINAL_HAMMER=FALSE` prevents live orders even if keys are present.
  - Production mode requires explicit `FINAL_HAMMER=TRUE` and testnet flag unset.
- **Credential flow:** Users submit Binance API keys (spot/futures) through the dashboard, where `BinanceCredentialService` encrypts and persists them in `bot_persistence/` or an external secrets backend.

---

## 2. Binance API Program Expectations → Implementation Mapping
| Requirement | Implementation Notes |
| --- | --- |
| Accept the [Binance Developer Terms](https://developers.binance.com/docs/binance-api/terms) | Documented in `README` under the compliance section (see updates below). |
| Use official endpoints with proper rate limiting | All HTTP calls go through `python-binance`, inheriting its automatic weight & retry handling. Background services batch requests using the provided client instances. |
| Provide clear user consent for key usage | Dashboard asks for API key + secret with tooltips explaining required permissions (Read, Trade; **never** Withdraw). Keys stored encrypted and scoped per profile. |
| Protect user data & secrets | `BinanceCredentialService` now encrypts credentials at rest (via `BINANCE_CREDENTIAL_KEY` Fernet key), rotates them on demand, and redacts secrets from logs. Secrets can also be injected via environment variables for immutable deployments. |
| Provide audit logs & incident response | `app/services/persistence.py` snapshots states, `artifacts/qfm/` stores ML telemetry, and `logs/` capture admin + trading actions. Incident playbook: revoke keys, disable `FINAL_HAMMER`, inspect `server.log`. |
| Offer sandbox/test evidence | `tests/test_*` suites cover key flows. `BINANCE_TESTNET` flag plus `scripts/uptime_probe.py` provide reproducible health checks across `/marketing`, `/api/subscriptions/plans`, and `/admin/leads`. |
| Respect KYC/AML obligations | The bot never touches custody; it acts only after the authenticated Binance account (already KYC’d) authorizes API keys. Admin docs remind operators to keep KYC/AML evidence inside their exchange account. |

---

## 3. Security & Operational Controls
1. **API key scope recommendations**
   - Enable **Read** + **Futures/Spot Trade** permissions only.
   - Disable withdrawals at the API level; even if compromised, the bot cannot move funds.
2. **Key rotation procedure**
   - Revoke keys in Binance UI.
   - Post new credentials via `/api/binance/credentials` or dashboard.
   - Restart services to flush caches.
3. **Storage**
   - Set `BINANCE_CREDENTIAL_KEY` (Fernet base64) so stored credentials are encrypted before touching disk.
   - For on-prem or VPS deployments, mount `bot_persistence/` on encrypted disks (LUKS/FileVault) or relocate secrets to Vault/AWS Secrets Manager.
4. **Logging**
   - `server.log` never prints API secrets.
   - Lead capture + marketing forms sanitize PII.
5. **Network boundaries**
   - Expose Flask only behind HTTPS (NGINX/Caddy) with TLS 1.2+.
   - Allow outbound traffic exclusively to `*.binance.com`, `*.binancefuture.com`, and approved telemetry endpoints.

---

## 4. Testing & Validation Checklist
| Item | Command / Artifact |
| --- | --- |
| Marketing & public endpoints | `.venv/bin/pytest tests/test_public_landing.py tests/test_public_subscriptions.py` |
| Lead capture & admin review | `.venv/bin/pytest tests/test_lead_capture.py tests/test_admin_leads_view.py` |
| Status diagnostics & API smoke | `.venv/bin/pytest tests/test_status_diagnostics.py` |
| Live probe against deployed env | `python scripts/uptime_probe.py --base-url https://YOUR_HOST` |
| Trading backtest & health | `python scripts/status_diagnostics.py` (ensures trading context + ML models load) |
|

Provide screenshots or CI logs of these commands passing when submitting to Binance Academy.

---

## 5. Submission Packet for Binance Academy / API Program
1. **Executive summary** – 1–2 pages describing the bot, supported markets, and risk controls.
2. **Architecture diagram** – Highlight Flask app, background workers, Binance REST/WebSocket clients, and persistence layers.
3. **Security controls** – Reference this document plus any SOC2/ISO controls if available.
4. **Testing evidence** – Attach recent CI logs and uptime probe output.
5. **User documentation** – Link `README` sections for setup, testnet configuration, and admin operations.
6. **Compliance attestation** – Signed statement acknowledging Binance API Terms, rate limits, and prohibition on withdrawals.

---

## 6. Next Actions
- [ ] Capture screenshots of the marketing landing page, dashboard, and credential input flow.
- [ ] Export anonymized log snippets showing rate-limit compliance and error handling.
- [ ] Prepare a short video or Loom demo (Binance Academy often requests a walkthrough).
- [ ] Submit the packet through the [Binance API Partner application form](https://www.binance.com/en/binance-api) and keep records of correspondence.

---

## Appendix: Required Environment Flags

| Variable | Purpose |
| --- | --- |
| `BINANCE_CREDENTIAL_KEY` | Base64 Fernet key that encrypts any API key/secret persisted to `bot_persistence/binance_credentials.json`. Generate via `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. |
| `BINANCE_TERMS_ACCEPTED` | Must be set to `1` after accepting the official Binance Developer Terms; non-testnet trading is blocked until this flag is enabled. |
| `FINAL_HAMMER` | Remains `FALSE` during audits/approval. The bot still checks this flag right before live trade execution. |
| `BINANCE_TESTNET` | Keep `1` during review to ensure all calls hit Binance's paper endpoints. |

With these artifacts in place, reviewers can trace how the project handles Binance credentials, respects the exchange's policies, and maintains observability.
