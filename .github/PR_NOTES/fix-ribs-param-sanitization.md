PR Title: Fix test-mode bootstrap ordering, session handling, and RIBS robustness

Summary
-------
This branch stabilizes the test environment and fixes multiple test flakiness/regressions:

- Ensure DB schema creation and migrations run even when test-mode requests runtime to be skipped.
- Force an in-memory SQLite DB and set `SKIP_RUNTIME_BOOTSTRAP`/`TESTING` during pytest runs to avoid collisions with persistent instance DB.
- Add lightweight, test-only in-memory fallbacks for credential storage, logging, and a minimal trader so endpoints work when the full runtime is not initialized.
- Configure SQLAlchemy sessions in tests to set `expire_on_commit=False` to avoid DetachedInstanceError when tests access model attributes after commit.
- Fix `tests/test_migrations_email_verified.py` to use `monkeypatch` when injecting `app.extensions` into `sys.modules`.

Testing
-------
- Ran full test suite locally: **145 passed, 2 skipped**.
- Coverage: **38.91%** (above required 30%).

Notes / Risks
------------
- Changes are conservative and limited to development/test runtime behaviour and small defensive guards. Production runtime behavior is unchanged unless `AI_BOT_TEST_MODE` or pytest envs are in effect.

Next steps
----------
- Open a PR for review (compare: main...fix/ribs-param-sanitization). Suggested reviewers: @bareera786
- After merge, I can prepare a small deployment run and monitor the VPS logs for any runtime startup warnings.
