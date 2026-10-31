#!/usr/bin/env bash
# Rebuild the release branches 19.0 (from main) and 20.0 (from odoo20-dev) with the module at the root, and push everything.
set -euo pipefail
cd "$(dirname "$0")"
git diff --quiet && git diff --cached --quiet || { echo "Commit your changes first." >&2; exit 1; }
for pair in "19.0:main" "20.0:odoo20-dev"; do
  series="${pair%%:*}"; src="${pair##*:}"
  git branch -D "$series" >/dev/null 2>&1 || true
  git subtree split --prefix=addons "$src" -b "$series" >/dev/null
done
git push -q origin main odoo20-dev
git push -q --force-with-lease origin 19.0 20.0
for b in 19.0 20.0; do echo "$b: $(git ls-tree --name-only origin/$b | tr '\n' ' ')"; done
