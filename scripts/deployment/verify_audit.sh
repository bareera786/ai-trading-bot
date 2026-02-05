#!/usr/bin/env bash
set -euo pipefail

# verify_audit.sh
#
# Runs the focused multi-user isolation audit phases using the repository's
# virtual environment at ./.venv.
#
# Safe to run from repo root (this script cd's to its own directory).

ROOT_DIR=""
PY=""

die() {
  echo "ERROR: $*" >&2
  exit 1
}

safe_cd_repo_root() {
  # This script is expected to live at repo root.
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$ROOT_DIR" || die "Failed to cd to repo root: $ROOT_DIR"

  # Lightweight sanity checks so running from elsewhere is still safe.
  [[ -f "$ROOT_DIR/pyproject.toml" || -f "$ROOT_DIR/requirements.txt" || -f "$ROOT_DIR/setup.py" ]] || \
    echo "WARN: Could not confirm Python project root (no pyproject.toml/requirements.txt/setup.py at $ROOT_DIR)" >&2

  PY="$ROOT_DIR/.venv/bin/python"
  [[ -x "$PY" ]] || die "Expected venv python at $PY (create venv at ./.venv first)"
}

print_header() {
  # Match the requested header style.
  echo
  echo "=== $1 ==="
}

detect_coverage_targets() {
  # Detect top-level folders for coverage summary.
  # Excludes: .venv, __pycache__, tests (and hidden folders).
  COVERAGE_TARGETS=()

  local path base
  while IFS= read -r path; do
    base="$(basename "$path")"
    case "$base" in
      .*) continue ;;
      .venv|__pycache__|tests) continue ;;
    esac
    COVERAGE_TARGETS+=("$base")
  done < <(find "$ROOT_DIR" -maxdepth 1 -mindepth 1 -type d -print | LC_ALL=C sort)
}

summarize_coverage() {
  # Optional per-folder summary. Enable with: SHOW_COVERAGE_SUMMARY=1 ./verify_audit.sh
  local coverage_file="$1"

  if [[ "${SHOW_COVERAGE_SUMMARY:-0}" != "1" ]]; then
    return 0
  fi

  if [[ ! -f "$coverage_file" ]]; then
    echo "(coverage summary skipped: $coverage_file not found)"
    return 0
  fi

  detect_coverage_targets
  if [[ ${#COVERAGE_TARGETS[@]} -eq 0 ]]; then
    echo "(coverage summary skipped: no eligible top-level folders found)"
    return 0
  fi

  if ! "$PY" -c 'import coverage' >/dev/null 2>&1; then
    echo "(coverage summary skipped: 'coverage' module not available in venv)"
    return 0
  fi

  printf "\n%-28s %s\n" "Folder" "Coverage"
  printf "%-28s %s\n" "----------------------------" "--------"
  local folder include_pattern pct
  for folder in "${COVERAGE_TARGETS[@]}"; do
    include_pattern="$ROOT_DIR/$folder/*"
    # coverage report returns non-zero if nothing matches the include filter;
    # treat that as "n/a" (do not fail the script).
    local report_out
    report_out="$(COVERAGE_FILE="$coverage_file" "$PY" -m coverage report --include "$include_pattern" 2>/dev/null || true)"
    pct="$(printf '%s\n' "$report_out" | awk '/^TOTAL/ {print $NF; found=1} END {if(!found) print "n/a"}')"
    printf "%-28s %s\n" "$folder" "$pct"
  done
}

run_phase() {
  local phase_id="$1"
  local title="$2"
  shift
  shift
  local -a cmd=("$@")

  local coverage_file="$ROOT_DIR/.coverage.$phase_id"

  print_header "$title"
  printf 'Command: '
  printf '%q ' "${cmd[@]}"
  echo
  echo

  COVERAGE_FILE="$coverage_file" "${cmd[@]}"

  summarize_coverage "$coverage_file"

  echo
  echo "✅ Phase complete: $title"
}

safe_cd_repo_root

run_phase "16b" "Phase 16b — Ensemble confidence" \
  "$PY" -m pytest -q tests/test_multiuser_confidence_smoothing.py --cov-fail-under=0

run_phase "17" "Phase 17 — Binance logs" \
  "$PY" -m pytest -q tests/test_trading_routes.py -k "binance_logs" --cov-fail-under=0

run_phase "18b" "Phase 18b — Indicator selection dashboard" \
  "$PY" -m pytest -q tests/test_indicator_selection_multiuser_isolation.py --cov-fail-under=0

echo
echo "✅ All audit phases complete."
