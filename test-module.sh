#!/usr/bin/env bash
# Install a module in a fresh database and run its tests.   ODOO_IMAGE=odoo:20.0 ./test-module.sh <module> [extra odoo args]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MODULE="$1"; shift || true
DB="t_${MODULE}_$(date +%s)"
LOG="${TEST_LOG:-/tmp/$MODULE-test.log}"
"$HERE/run-odoo.sh" -d "$DB" -i "$MODULE" --db-filter "^$DB\$" --test-tags "/$MODULE" --stop-after-init --log-level=test "$@" > "$LOG" 2>&1 || true
grep -E "tests when loading|ERROR: |FAIL: |CRITICAL|ParseError" "$LOG" | cut -c1-230 | head -20
