#!/usr/bin/env bash
# Run network_evolution.py --extract against each of the 6 quarterly dumps,
# then a single --render pass. Reuses analysis/countries/extract_snapshot.sh's
# docker + Neo4j lifecycle pattern.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
ARCHIVE="$REPO/dumps_archive"
DUMPS="$REPO/dumps"
DATA="$REPO/data"
VENV_PY="$REPO/.venv/bin/python"
LOG="$REPO/analysis/complex_network/network_evolution.log"

SNAPS=(
  "2025-01:2025-01-08"
  "2025-04:2025-04-08"
  "2025-07:2025-07-08"
  "2025-10:2025-10-08"
  "2026-01:2026-01-15"
  "2026-04:2026-04-08"
)

fsize() { stat -f%z "$1" 2>/dev/null || stat -c%s "$1" 2>/dev/null || echo 0; }

wait_neo4j() {
    for i in $(seq 1 180); do
        sleep 5
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
            echo "  Neo4j ready (${i}x5s)"
            return 0
        fi
    done
    return 1
}

echo "=== network-evolution pipeline start $(date -Iseconds) ===" | tee -a "$LOG"
for entry in "${SNAPS[@]}"; do
    SNAP="${entry%:*}"
    DATE="${entry#*:}"
    DUMP="$ARCHIVE/iyp-$DATE.dump"
    echo "=== [$SNAP] ===" | tee -a "$LOG"

    if [ ! -f "$DUMP" ]; then
        URL="https://archive.ihr.live/ihr/iyp/${DATE:0:4}/${DATE:5:2}/${DATE:8:2}/iyp-$DATE.dump"
        echo "  downloading $URL" | tee -a "$LOG"
        if ! curl -L --no-progress-meter "$URL" -o "$DUMP"; then
            echo "  FAIL download; skipping $SNAP" | tee -a "$LOG"
            rm -f "$DUMP"
            continue
        fi
        echo "  dump size: $(($(fsize "$DUMP")/1024/1024)) MB" | tee -a "$LOG"
    fi

    echo "  staging $DUMP" | tee -a "$LOG"
    cp "$DUMP" "$DUMPS/neo4j.dump"

    echo "  resetting containers + data" | tee -a "$LOG"
    docker stop iyp iyp_loader 2>/dev/null || true
    docker rm iyp iyp_loader 2>/dev/null || true
    rm -rf "$DATA/databases" "$DATA/transactions"

    echo "  docker compose up" | tee -a "$LOG"
    cd "$REPO"
    uid="$(id -u)" gid="$(id -g)" docker compose --profile local up -d 2>&1 \
        | grep -E 'Container iyp' | tee -a "$LOG"

    if ! wait_neo4j | tee -a "$LOG"; then
        echo "  ERROR Neo4j not ready; skipping $SNAP" | tee -a "$LOG"
        continue
    fi

    echo "  running --extract --snapshot $SNAP" | tee -a "$LOG"
    "$VENV_PY" -m analysis.complex_network.network_evolution \
        --extract --snapshot "$SNAP" 2>&1 | tee -a "$LOG"

    echo "  teardown" | tee -a "$LOG"
    docker stop iyp iyp_loader 2>/dev/null || true
    docker rm iyp iyp_loader 2>/dev/null || true
    rm -rf "$DATA/databases" "$DATA/transactions"
    rm -f "$DUMPS/neo4j.dump"
done

echo "=== render $(date -Iseconds) ===" | tee -a "$LOG"
"$VENV_PY" -m analysis.complex_network.network_evolution --render 2>&1 | tee -a "$LOG"
echo "=== network-evolution pipeline done $(date -Iseconds) ===" | tee -a "$LOG"
