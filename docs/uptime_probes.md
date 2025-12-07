# Uptime Probes

Simple health checks for the marketing funnel now live alongside the app.

## Pytest smoke tests
- `tests/test_public_landing.py` ensures `/marketing` renders without auth and `/` redirects correctly.
- Existing API tests (`tests/test_public_subscriptions.py`) verify the subscription catalog is retrievable.

Run the focused suite locally:

```bash
. .venv/bin/activate
.venv/bin/pytest tests/test_public_landing.py tests/test_public_subscriptions.py
```

## CLI probe for deployments
`scripts/uptime_probe.py` performs the same checks against a running environment (marketing HTML, root redirect, subscription API). Example:

```bash
python scripts/uptime_probe.py --base-url https://trading.example.com
```

Exit code is non-zero if any probe fails, so you can wire it into CI or post-deploy hooks.
