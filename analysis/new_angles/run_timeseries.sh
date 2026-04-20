#!/usr/bin/env bash
# Time-series extraction: loop every dump in dumps_archive/, load it
# into Neo4j using /dev/sda1 scratch, run extract_data.py --snapshot,
# tear down, move on. CSVs land in data_cache/new_angles/<YYYY-MM-DD>/.
#
# Resumable: skips snapshots whose as_country.csv already exists and
# is non-empty.
#
# Usage:
#   bash analysis/new_angles/run_timeseries.sh           # all dumps
#   DUMPS="2024-01-15 2024-04-22" bash run_timeseries.sh # subset
set -uo pipefail

REPO="/home/wangmm/internet-yellow-pages"
SCRATCH="/home/wangmm/work/memory/dns/gtld/iyp_scratch"
LOG="$REPO/analysis/new_angles/run_timeseries.log"
cd "$REPO"

# Default: every dump in dumps_archive/ except the one already extracted.
if [ -z "${DUMPS:-}" ]; then
    DUMPS=""
    for d in dumps_archive/iyp-*.dump; do
        snap="$(basename "$d" .dump | sed 's/^iyp-//')"
        DUMPS="$DUMPS $snap"
    done
fi

ensure_symlink() {
    local target="$1" link="$2"
    mkdir -p "$target"
    if [ -L "$link" ]; then
        [ "$(readlink "$link")" = "$target" ] && return
        rm -f "$link"
    elif [ -e "$link" ]; then
        rm -rf "$link"
    fi
    ln -s "$target" "$link"
}

wait_for_neo4j() {
    # Poll bolt port; succeed when we can count nodes, max ~20 min.
    for i in $(seq 1 120); do
        sleep 10
        if python3 -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687')
try:
    with d.session() as s:
        s.run('MATCH (n) RETURN count(n) AS c').single()
    print('ready')
except Exception:
    exit(1)
" 2>/dev/null | grep -q ready; then
            echo "   neo4j ready after ${i}0s"
            return 0
        fi
    done
    echo "   neo4j failed to become ready in 20 min"
    return 1
}

run_one() {
    local snap="$1"
    local dump="$REPO/dumps_archive/iyp-${snap}.dump"
    local out_as="$REPO/data_cache/new_angles/${snap}/as_country.csv"

    if [ ! -f "$dump" ]; then
        echo "MISSING $dump — skip"
        return 1
    fi
    if [ -s "$out_as" ]; then
        echo "SKIP $snap (already extracted)"
        return 0
    fi

    echo
    echo "=== $(date -Iseconds) $snap ==="
    ensure_symlink "$SCRATCH/data" "$REPO/data"
    ensure_symlink "$SCRATCH/dumps" "$REPO/dumps"

    # Teardown any previous container
    sg docker -c "docker stop iyp iyp_loader 2>/dev/null; docker rm iyp iyp_loader 2>/dev/null" >/dev/null 2>&1
    rm -rf "$SCRATCH/data/databases" "$SCRATCH/data/transactions"
    rm -f "$SCRATCH/dumps/neo4j.dump"

    echo "   staging dump"
    cp "$dump" "$SCRATCH/dumps/neo4j.dump"

    echo "   docker compose up -d"
    sg docker -c "uid=$(id -u) gid=$(id -g) docker compose --profile local up -d" 2>&1

    if ! wait_for_neo4j; then
        sg docker -c "docker logs iyp_loader --tail 30"
        echo "   ABORT $snap"
        return 1
    fi

    echo "   extract → data_cache/new_angles/${snap}/"
    IYP_SNAPSHOT="$snap" python3 -m analysis.new_angles.extract_data 2>&1

    echo "   teardown"
    sg docker -c "docker stop iyp iyp_loader 2>/dev/null; docker rm iyp iyp_loader 2>/dev/null" >/dev/null 2>&1
    rm -rf "$SCRATCH/data/databases" "$SCRATCH/data/transactions"
    rm -f "$SCRATCH/dumps/neo4j.dump"
    echo "=== done $snap $(date -Iseconds) ==="
}

echo "=== run_timeseries start $(date -Iseconds) ===" | tee -a "$LOG"
for snap in $DUMPS; do
    run_one "$snap" 2>&1 | tee -a "$LOG"
done
echo "=== run_timeseries end $(date -Iseconds) ===" | tee -a "$LOG"
