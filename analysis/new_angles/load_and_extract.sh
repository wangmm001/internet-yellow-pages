#!/usr/bin/env bash
# One-off: stage 2024-10-08 dump, load Neo4j, run extract_data.py, tear down.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
DUMP="$REPO/dumps_archive/iyp-2024-10-08.dump"
DUMPS="$REPO/dumps"
DATA="$REPO/data"
VENV_PY="${VENV_PY:-$REPO/.venv/bin/python}"
[ -x "$VENV_PY" ] || VENV_PY="$(command -v python3)"
LOG="$REPO/analysis/new_angles/extract.log"

echo "=== start $(date -Iseconds) ===" | tee "$LOG"

[ -f "$DUMP" ] || { echo "missing $DUMP" | tee -a "$LOG"; exit 1; }

echo "staging dump $DUMP → $DUMPS/neo4j.dump" | tee -a "$LOG"
mkdir -p "$DUMPS" "$DATA"
cp "$DUMP" "$DUMPS/neo4j.dump"

echo "stopping any iyp containers" | tee -a "$LOG"
sg docker -c "docker stop iyp iyp_loader 2>/dev/null || true"
sg docker -c "docker rm iyp iyp_loader 2>/dev/null || true"
rm -rf "$DATA/databases" "$DATA/transactions"

echo "starting docker compose --profile local" | tee -a "$LOG"
cd "$REPO"
sg docker -c "uid=$(id -u) gid=$(id -g) docker compose --profile local up -d" 2>&1 \
    | tee -a "$LOG"

echo "waiting for Neo4j (up to 30 min)" | tee -a "$LOG"
for i in $(seq 1 180); do
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
        echo "Neo4j ready after ${i}0s" | tee -a "$LOG"
        break
    fi
done

echo "running extract_data.py" | tee -a "$LOG"
"$VENV_PY" -m analysis.new_angles.extract_data 2>&1 | tee -a "$LOG"
EXIT=$?

echo "tearing down" | tee -a "$LOG"
sg docker -c "docker stop iyp iyp_loader 2>/dev/null || true"
sg docker -c "docker rm iyp iyp_loader 2>/dev/null || true"
rm -rf "$DATA/databases" "$DATA/transactions"
rm -f "$DUMPS/neo4j.dump"

echo "=== done exit=$EXIT $(date -Iseconds) ===" | tee -a "$LOG"
exit $EXIT
