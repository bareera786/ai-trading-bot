# Repository Cleanup & History-Purge Plan

Purpose
-------
This document records a safe, auditable plan to remove large artifacts and any accidental secrets from the git history, add preventive CI checks, and harden repository structure for a private / commercial project.

Summary of items to remove from history
---------------------------------------
Files already untracked on the cleanup branch (candidate list):
- artifacts/qfm/default/feature_matrices/*_1h_1y_qfm_matrix.csv
- artifacts/qfm/default/qfm_artifacts_summary.json
- node_modules/esbuild/* (binaries + license)
- .coverage and other temporary coverage files

Potential additional candidates (check before action):
- Any large CSVs, PKL, .joblib files under `artifacts/`, `optimized_models/`, `optimized_trade_data/`.
- Any accidentally committed config/deploy.env or files containing credentials (we didn't find tracked deploy.env, but double-check history for older commits).

High-level plan
---------------
1. Prepare: identify exact files & compute size impact; prepare a PR with the proposed set of removals and `.gitignore` additions (done: `chore/cleanup-repo`).
2. Soft cleanup (non-history): remove files from index and add to `.gitignore` (already done in branch). This preserves working tree local copies and prevents re-adding.
3. Run CI and tests across the repo to make sure we didn't break anything (done locally; we fixed several test regressions). Address any failing tests.
4. History purge (destructive): use `git filter-repo` (preferred) or `bfg` to entirely remove files from all commits and reduce repo size. This requires force-pushing the branch and coordination with all contributors.
5. Post-purge: rotate any secrets that appear anywhere in the old commits (we didn't find obvious tracked secrets in current HEAD, but the history scan is mandatory). Invalidate the old keys in deployments and secret vaults.
6. Add CI protections: a GitHub Action to reject >5 MB files in PRs, a secret scanner (trufflehog / repo-supervisor), and pre-commit hooks to catch large files and naive secrets.
7. Add documentation for artifact storage: move large model/artifact files to external storage (S3, GCS, artifact bucket) and provide scripts to fetch them (e.g., `scripts/fetch_artifacts.py`), plus update README.
8. Communicate & coordinate: announce the planned purge window, tell all contributors to create local backups / push branches, and provide re-clone instructions after the purge.

Detailed Steps for History-Purge (git-filter-repo)
-------------------------------------------------
> Warning: This is destructive. All contributors must re-clone after we force-push.

1. Create a temporary backup repo (bare clone):

   ```bash
   git clone --mirror https://github.com/bareera786/ai-trading-bot.git ai-trading-bot-mirror.git
   cd ai-trading-bot-mirror.git
   git bundle create ../ai-trading-bot-backup.bundle --all
   # Keep the bundle somewhere safe outside the repo
   ```

2. Install git-filter-repo (recommended) or use BFG:

   - Homebrew: `brew install git-filter-repo`
   - Or: `pip install git-filter-repo` (use in a virtualenv)

3. Dry-run to list problematic files and sizes:

   ```bash
   git rev-list --objects --all | \
     git cat-file --batch-check='%(objecttype) %(objectname) %(rest)' | \
     grep '^blob' | \
     sort --numeric-sort --key=3 | \
     awk '{print $3,$2}' | tail -n 50
   ```

4. Prepare a `paths-to-remove.txt` file listing globs/paths to purge (example):

   ```text
   artifacts/qfm/default/feature_matrices/*.csv
   node_modules/esbuild/**
   .coverage
   htmlcov/**
   ```

5. Run git-filter-repo (removes the paths from history):

   ```bash
   # From the mirrored repo
   git filter-repo --invert-paths --paths-from-file ../paths-to-remove.txt
   ```

6. Inspect results locally: verify repo size is reduced and no desired files were removed. Run tests locally on the cleaned mirror (optional: checkout quick working clone from mirror and run tests there).

7. Force-push to GitHub (coordinate with team):

   ```bash
   # Notify team first. Then:
   git remote set-url origin git@github.com:bareera786/ai-trading-bot.git
   git push --force --all
   git push --force --tags
   ```

8. Ask all contributors to re-clone (document in PR and an email/Slack):

   ```text
   git clone https://github.com/bareera786/ai-trading-bot.git
   ```

Rollback steps
--------------
- If anything goes wrong, restore from the bundle created earlier: clone from the bundle or push the bundle back to remote.

CI hardening & automation
-------------------------
1. Add a GitHub Action (PR workflow) that checks:
   - No files > 5 MB are added in the PR (fail if found).
   - Run a secret scanner like `trufflehog` (or use github advanced security).
   - Run `scripts/run_ci_checks.sh` as a sanity step.

2. Add a pre-commit hook that checks file sizes and runs `detect-secrets`.

3. Add a docs/DEV_GUIDE.md section describing artifacts storage and how to fetch models via the provided script.

Security & secrets
------------------
- Any keys found in history must be rotated (Binance credential keys, SECRET_KEY in old commits, etc.).
- Ensure `config/deploy.env` is in `.gitignore` (it already is) and no production secrets are present in tracked files.

Open questions / choices for you
-------------------------------
- Do you want me to proceed with the destructive history purge now (I will prepare and show the exact `paths-to-remove.txt` and the list of commits affected), or do you want to:
  - Run the purge in a pre-announced maintenance window with team coordination, or
  - Hold off and first add CI hardening, which reduces the urgency for a purge?

Suggested next step (my recommendation)
--------------------------------------
1. Add the `paths-to-remove.txt` and run a dry-run with `git filter-repo --analyze` to see the impact.
2. Open a PR with the `docs/repo_cleanup_plan.md` (this file) and the CI hardening GitHub Action and pre-commit config changes (non-destructive changes now).
3. After review/approval, schedule the forced history purge in a short maintenance window and notify collaborators.

---

If you confirm, I will:
- (A) Add `paths-to-remove.txt` to this branch and run a local dry-run to show the size improvement; OR
- (B) Add GitHub Action + pre-commit configs to block large files and secrets (non-destructive), and open a PR with these plus this plan.

Which would you like me to do next? If you want both, I’ll start with (B) so the repo is protected immediately and then schedule (A) for the purge with your approval.
