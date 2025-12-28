E2E (Playwright) tests
=======================

This project includes an optional Playwright-based E2E test that verifies the RIBS deploy toast behavior.

Setup (local/dev machine):

1. Install Python dependencies (this will install `playwright` and `pytest-playwright`):

```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:

```bash
python -m playwright install
```

3. Run the E2E test (by default E2E tests are disabled; enable by setting RUN_E2E=1):

```bash
# Run against local dev server
RUN_E2E=1 pytest tests/e2e/test_ribs_deploy_toast.py -q

# Or run against staging by setting TARGET_URL
TARGET_URL=http://151.243.171.80 RUN_E2E=1 pytest tests/e2e/test_ribs_deploy_toast.py -q
```

Notes:
- The test will try to visit `/ribs` and call `deployRIBSStrategy('nonexistent_strategy_test')`, so it does not require a specific elite to be present.
- The test auto-accepts the confirmation dialog and asserts a toast appears with an informative message.
