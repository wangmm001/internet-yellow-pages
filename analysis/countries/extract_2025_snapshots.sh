#!/usr/bin/env bash
# Sequential per-snapshot extraction for the freshly downloaded 2025
# quarterly dumps. Each lifecycle ~20-50 min wall.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
LOG="$REPO/analysis/countries/extract_2025_chain.log"

echo "$(date -Iseconds) === start sequential extract" | tee -a "$LOG"

for spec in 2025-04-01 2025-07-01 2025-10-08; do
    echo "$(date -Iseconds) --- starting $spec" | tee -a "$LOG"
    bash "$REPO/analysis/countries/extract_snapshot.sh" "$spec" \
        2>&1 | tee -a "$LOG"
    echo "$(date -Iseconds) --- done $spec" | tee -a "$LOG"
done

echo "$(date -Iseconds) === all 3 snapshots done" | tee -a "$LOG"
