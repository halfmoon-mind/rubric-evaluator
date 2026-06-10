#!/usr/bin/env sh
# Portable launcher for check_rules.py: tries python3, then python, then the
# Windows `py -3` launcher. All arguments are forwarded, so this also drives the
# grade step (run_checks.sh --grade <findings.json>). If no interpreter is found,
# it points at the manual fallback and exits 127.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SCRIPT_DIR/check_rules.py" "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python "$SCRIPT_DIR/check_rules.py" "$@"
fi

if command -v py >/dev/null 2>&1; then
  exec py -3 "$SCRIPT_DIR/check_rules.py" "$@"
fi

cat >&2 <<'EOF'
No Python runtime was found (tried python3, python, py -3).
Read references/fallbacks.md and produce a PROVISIONAL manual report,
or install Python and rerun scripts/run_checks.sh.
EOF
exit 127
