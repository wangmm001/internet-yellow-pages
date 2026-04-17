#!/usr/bin/env bash
# Run extract_snapshot.sh serially for all 4 new quarterly snapshots.
# Skips snapshots whose metrics dir already contains ≥ 9 × 20 = 180 JSONs.
#
# Dates picked per availability on archive.ihr.live:
#   2025-01-08 (4 GB)   2025-07-08 (9 GB)   2025-10-08 (13 GB)
#   2026-01-15 (13 GB, 2026-01-08 not published)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG="$REPO/analysis/countries/extract.log"

SNAPS=(2025-01-08 2025-07-08 2025-10-08 2026-01-15)

echo "=== pipeline start $(date -Iseconds) ==="           | tee -a "$LOG"
for S in "${SNAPS[@]}"; do
    SNAP="${S:0:7}"
    DIR="$REPO/analysis/countries/data/$SNAP"
    JSON_COUNT=$(find "$DIR" -name 'step*_metrics.json' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$JSON_COUNT" -ge 180 ]; then
        echo "[$SNAP] already extracted ($JSON_COUNT JSONs), skipping" | tee -a "$LOG"
        continue
    fi
    echo "=== [$SNAP] extracting ==="                     | tee -a "$LOG"
    if "$SCRIPT_DIR/extract_snapshot.sh" "$S" 2>&1 | tee -a "$LOG"; then
        echo "[$SNAP] SUCCESS" | tee -a "$LOG"
    else
        echo "[$SNAP] FAILED (continuing with next)" | tee -a "$LOG"
    fi
done
echo "=== pipeline done $(date -Iseconds) ==="            | tee -a "$LOG"
