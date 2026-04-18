#!/usr/bin/env bash
# 2024 backfill + 2025-01 re-extract (step04 fallback fix).
# Loops extract_snapshot.sh over 5 targets. Each iteration:
#   download → Neo4j load → 9×20 country extract → network_evolution extract
#   → teardown. Dumps stay in dumps_archive/.
#
# Background runtime: ~100 min × 5 snapshots ≈ 2 hours wall clock.
# Resumable: extract_snapshot.sh skips completed downloads.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
LOG="$REPO/analysis/countries/backfill_2024.log"

TARGETS=(
  2024-01-15
  2024-04-22
  2024-07-08
  2024-10-08
  2025-01-08
)

echo "=== backfill start $(date -Iseconds) ===" | tee -a "$LOG"
for target in "${TARGETS[@]}"; do
  echo "" | tee -a "$LOG"
  echo "=== target=$target $(date -Iseconds) ===" | tee -a "$LOG"
  if ! "$REPO/analysis/countries/extract_snapshot.sh" "$target" 2>&1 \
       | tee -a "$LOG"; then
    echo "=== FAILED target=$target; continuing ===" | tee -a "$LOG"
  fi
done
echo "=== backfill done $(date -Iseconds) ===" | tee -a "$LOG"
