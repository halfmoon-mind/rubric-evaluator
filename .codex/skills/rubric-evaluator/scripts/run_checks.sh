#!/usr/bin/env sh
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
No Python runtime was found.
Use references/fallbacks.md for provisional manual evaluation, or install Python and rerun scripts/run_checks.sh.
EOF
exit 127
