#!/usr/bin/env bash
# Usage: run-council.sh <repo-dir>   (e.g. ../raise after a merge). Read-only reviewers, run in parallel.
set -u
REPO=${1:?repo dir}; HERE="$(cd "$(dirname "$0")" && pwd)"; TS=$(date +%H%M)
export PATH="$HOME/.local/bin:$PATH" MODE=replay COUNCIL_DIR="$HERE" COUNCIL_SCRATCH="$(mktemp -d)"
cd "$REPO" || exit 1
for r in r1-contracts r2-replay r3-frontend r4-correctness r5-e2e r6-chaos; do
  ( agy --print --mode plan --print-timeout 900s "$(cat "$HERE/common.txt" "$HERE/$r.txt")" \
      > "$HERE/reports/$TS-$r.md" 2>&1 ) &
done
wait
python3 "$HERE/gate.py" "$HERE/reports" "$TS"; GATE=$?
echo "council done -> $HERE/reports/ ($TS)"; exit $GATE
