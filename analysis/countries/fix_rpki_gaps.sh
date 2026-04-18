#!/usr/bin/env bash
# Reload old dump → probe schema → patch RPKI zeros → teardown.
# Usage: ./fix_rpki_gaps.sh 2024-07-08
set -euo pipefail

TARGET="${1:?usage: $0 YYYY-MM-DD}"
SNAP="${TARGET:0:7}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
ARCHIVE="$REPO/dumps_archive"
DUMPS="$REPO/dumps"
DATA="$REPO/data"
VENV_PY="${VENV_PY:-$REPO/.venv/bin/python}"
[ -x "$VENV_PY" ] || VENV_PY="$(command -v python3)"
DUMP_FILE="$ARCHIVE/iyp-$TARGET.dump"
LOG="[rpki-fix $SNAP]"

[ -f "$DUMP_FILE" ] || { echo "$LOG dump missing: $DUMP_FILE"; exit 1; }

echo "$LOG staging dump"
sg docker -c "docker stop iyp iyp_loader 2>/dev/null || true"
sg docker -c "docker rm iyp iyp_loader 2>/dev/null || true"
rm -rf "$DATA/databases" "$DATA/transactions"
cp "$DUMP_FILE" "$DUMPS/neo4j.dump"

echo "$LOG starting Neo4j"
cd "$REPO"
sg docker -c "uid=$(id -u) gid=$(id -g) docker compose --profile local up -d"

echo "$LOG waiting for readiness"
for i in $(seq 1 360); do
    sleep 10
    if "$VENV_PY" -c "
from neo4j import GraphDatabase
try:
    d = GraphDatabase.driver('bolt://localhost:7687')
    with d.session() as s:
        s.run('MATCH (n) RETURN count(n) AS c').single()
except Exception:
    raise SystemExit(1)
" 2>/dev/null; then
        echo "$LOG ready after ${i}0s"
        break
    fi
done

echo "$LOG running probe+patch"
"$VENV_PY" -m analysis.countries.fix_rpki_gaps --snapshot "$SNAP"

echo "$LOG teardown"
sg docker -c "docker stop iyp iyp_loader 2>/dev/null || true"
sg docker -c "docker rm iyp iyp_loader 2>/dev/null || true"
rm -rf "$DATA/databases" "$DATA/transactions"
rm -f "$DUMPS/neo4j.dump"
echo "$LOG done $(date -Iseconds)"
