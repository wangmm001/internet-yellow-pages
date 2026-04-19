#!/usr/bin/env bash
# Wait for 2026-01-01 download → run extract_snapshot.sh → done.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
LOG="$REPO/analysis/countries/extract_2026-01.log"
DUMP="$REPO/dumps_archive/iyp-2026-01-01.dump"

echo "$(date -Iseconds) waiting for 2026-01-01 download to finish" | tee -a "$LOG"
while pgrep -fa "curl.*iyp-2026-01-01.dump" > /dev/null; do
    sleep 20
done
sz=$(stat -c%s "$DUMP")
echo "$(date -Iseconds) download finished: $((sz/1024/1024/1024)) GB" | tee -a "$LOG"

echo "$(date -Iseconds) starting extract_snapshot 2026-01-01" | tee -a "$LOG"
bash "$REPO/analysis/countries/extract_snapshot.sh" 2026-01-01 2>&1 | tee -a "$LOG"
echo "$(date -Iseconds) done" | tee -a "$LOG"
