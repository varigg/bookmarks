#!/usr/bin/env bash
# Every AGENTS.md gate, in order. Run from anywhere; stage new files first.
#
# Every gate runs even after one fails. A gate whose tool is missing reports
# SKIPPED, and SKIPPED is never a pass. Exit 0 only when every gate passed,
# 1 when any failed, 2 when none failed but some were skipped.
# The boot check and shape test are pytest files (test_boot.py, test_shape.py,
# test_import_direction.py), so they run in the tests gate.
set -uo pipefail
cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)" || exit 1
# A stale uv.lock fails the gate; plain `uv run` would rewrite it and pass.
export UV_LOCKED=1

failed=0 skipped=0 summary=()

gate() { # <name> <required-tool> <command...>
  local name="$1" tool="$2"
  shift 2
  if ! command -v "$tool" >/dev/null; then
    summary+=("$name SKIPPED ($tool not installed)")
    skipped=1
    return
  fi
  echo "== $name" >&2
  if "$@" >&2; then
    summary+=("$name ok")
  else
    summary+=("$name FAIL (exit $?)")
    failed=1
  fi
}

no_tracked_data() {
  local tracked
  tracked=$(git ls-files ':(glob)**/*.db' ':(glob)**/.env' ':(glob)**/data/**')
  [[ -z "$tracked" ]] || { echo "tracked data files:" "$tracked"; return 1; }
}

gate lint uv uv run ruff check .
gate format uv uv run ruff format --check .
gate tests uv uv run pytest -q
gate audit uv uv run pip-audit --skip-editable
gate tracked-data git no_tracked_data
gate secrets gitleaks gitleaks git --no-banner --redact .

printf '%s\n' "${summary[@]}"
((failed)) && exit 1
((skipped)) && exit 2
exit 0
