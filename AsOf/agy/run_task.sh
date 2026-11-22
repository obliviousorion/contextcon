#!/usr/bin/env bash
# Run one NON-SENSITIVE build task on Antigravity (agy) headless, then verify it only touched allowed paths.
# Usage: agy/run_task.sh <task-file> <allowed-path-prefix> [more prefixes...]
# Example: agy/run_task.sh agy/tasks/ui.md frontend/
# Exit codes: 0 ok · 2 agy missing/failed · 3 touched files outside the allowed paths (nothing is reverted; the lead decides)
set -u
TASK=${1:?task file}; shift; ALLOWED=("$@"); [ ${#ALLOWED[@]} -gt 0 ] || { echo "need at least one allowed path prefix" >&2; exit 2; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
export PATH="$HOME/.local/bin:$PATH"
AGY=${AGY_BIN:-agy}; command -v "$AGY" >/dev/null || { echo "agy not installed: fall back to the Claude subagent for this task" >&2; exit 2; }
NAME=$(basename "$TASK" .md); TS=$(date +%H%M%S); LOG="agy/logs/$TS-$NAME.log"
BEFORE=$(git status --porcelain --untracked-files=all . | sort)
PROMPT="$(cat agy/RULES_FOR_AGY.md)

ALLOWED PATHS FOR THIS TASK (create/edit files ONLY under these, relative to $ROOT): ${ALLOWED[*]}

$(cat "$TASK")"
"$AGY" --print --mode accept-edits --print-timeout 1500s "$PROMPT" > "$LOG" 2>&1; RC=$?
AFTER=$(git status --porcelain --untracked-files=all . | sort)
CHANGED=$(comm -13 <(echo "$BEFORE") <(echo "$AFTER") | awk '{print $NF}')
OUTSIDE=""
for f in $CHANGED; do f=${f#AsOf/}; ok=0; for a in "${ALLOWED[@]}"; do [[ "$f" == "$a"* ]] && ok=1; done; [ $ok -eq 1 ] || OUTSIDE="$OUTSIDE $f"; done
echo "agy exit=$RC log=$LOG"; echo "changed:"; echo "$CHANGED" | sed 's/^/  /'
if [ -n "$OUTSIDE" ]; then echo "OUT-OF-SCOPE CHANGES (review and revert manually if wrong):$OUTSIDE" >&2; exit 3; fi
[ $RC -eq 0 ] || exit 2
exit 0
