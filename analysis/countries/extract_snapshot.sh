#!/usr/bin/env bash
# Per-snapshot lifecycle: download dump (once) → load Neo4j → extract 9×20 →
# stop Neo4j → purge loaded DB. Dump kept in dumps_archive/ for reruns.
#
# Usage: ./extract_snapshot.sh 2025-01-08
set -euo pipefail

TARGET="${1:?usage: $0 YYYY-MM-DD}"
YEAR="${TARGET:0:4}"; MONTH="${TARGET:5:2}"; DAY="${TARGET:8:2}"
SNAP="$YEAR-$MONTH"

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
ARCHIVE="$REPO/dumps_archive"
DUMPS="$REPO/dumps"
DATA="$REPO/data"
VENV_PY="$REPO/.venv/bin/python"
DUMP_URL="https://archive.ihr.live/ihr/iyp/$YEAR/$MONTH/$DAY/iyp-$TARGET.dump"
DUMP_FILE="$ARCHIVE/iyp-$TARGET.dump"
LOG_PREFIX="[$SNAP]"

echo "$LOG_PREFIX === start $(date -Iseconds) ==="

mkdir -p "$ARCHIVE" "$DUMPS" "$DATA"

# Portable file-size helper (macOS `stat -f%z`, Linux `stat -c%s`)
fsize() { stat -f%z "$1" 2>/dev/null || stat -c%s "$1" 2>/dev/null || echo 0; }

# 1. Download (resumeable, skipped if file already complete)
if [ -f "$DUMP_FILE" ]; then
    REMOTE_SIZE=$(curl -sI "$DUMP_URL" --max-time 30 \
        | awk -v IGNORECASE=1 '/content-length/{print $2}' | tr -d '\r')
    LOCAL_SIZE=$(fsize "$DUMP_FILE")
    if [ "$LOCAL_SIZE" = "$REMOTE_SIZE" ]; then
        echo "$LOG_PREFIX dump already complete: $DUMP_FILE"
    else
        echo "$LOG_PREFIX resume download (local=$LOCAL_SIZE remote=$REMOTE_SIZE)"
        curl -L -C - --progress-bar "$DUMP_URL" -o "$DUMP_FILE"
    fi
else
    echo "$LOG_PREFIX downloading $DUMP_URL"
    curl -L --progress-bar "$DUMP_URL" -o "$DUMP_FILE"
fi

# 2. Stage dump for loader
echo "$LOG_PREFIX staging dump → $DUMPS/neo4j.dump"
cp "$DUMP_FILE" "$DUMPS/neo4j.dump"

# 3. Purge previously loaded DB so loader will re-run
echo "$LOG_PREFIX stopping any running Neo4j container"
docker stop iyp iyp_loader 2>/dev/null || true
docker rm iyp iyp_loader 2>/dev/null || true
echo "$LOG_PREFIX purging loaded database"
rm -rf "$DATA/databases" "$DATA/transactions"

# 4. Bring up loader + DB
echo "$LOG_PREFIX starting docker compose --profile local"
cd "$REPO"
uid="$(id -u)" gid="$(id -g)" docker compose --profile local up -d

# 5. Wait for Neo4j readiness (up to 60 min)
echo "$LOG_PREFIX waiting for Neo4j readiness"
READY=0
for i in $(seq 1 360); do
    sleep 10
    if "$VENV_PY" -c "
from neo4j import GraphDatabase
try:
    d = GraphDatabase.driver('bolt://localhost:7687')
    with d.session() as s:
        r = s.run('MATCH (n) RETURN count(n) AS c').single()
    print(r['c'])
except Exception:
    raise SystemExit(1)
" 2>/dev/null | grep -qE '^[0-9]+$'; then
        READY=1
        echo "$LOG_PREFIX Neo4j ready after ${i}0s"
        break
    fi
done
if [ "$READY" != "1" ]; then
    echo "$LOG_PREFIX ERROR: Neo4j did not become ready within 60 min"
    exit 1
fi

# 6. Run 9-country × 20-step extraction
echo "$LOG_PREFIX running analysis.countries.run_all --snapshot $SNAP"
cd "$REPO"
"$VENV_PY" -m analysis.countries.run_all --snapshot "$SNAP"

# 7. Verify extraction
echo "$LOG_PREFIX verifying"
"$VENV_PY" -m analysis.countries.run_all --verify --snapshot "$SNAP" || true

# 8. Tear down (keeps dump in dumps_archive/)
echo "$LOG_PREFIX stopping Neo4j and purging loaded DB"
docker stop iyp iyp_loader 2>/dev/null || true
docker rm iyp iyp_loader 2>/dev/null || true
rm -rf "$DATA/databases" "$DATA/transactions"
rm -f "$DUMPS/neo4j.dump"

echo "$LOG_PREFIX === done $(date -Iseconds) ==="
