#!/usr/bin/env bash
# Incremental Phase 2 driver: for each dump, only run the 4 DC extractors
# (facilities / facility_members / facility_ixps / peeringdb_nets).
# Skips dumps where facilities.csv already exists non-empty.
#
# Resumable. ~6 min/dump × 10 = ~1h total.
set -uo pipefail

REPO="/home/wangmm/internet-yellow-pages"
SCRATCH="/home/wangmm/work/memory/dns/gtld/iyp_scratch"
LOG="$REPO/analysis/new_angles/run_dc_timeseries.log"
cd "$REPO"

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
    for i in $(seq 1 120); do
        sleep 10
        if python3 -c "
from neo4j import GraphDatabase
try:
    d = GraphDatabase.driver('bolt://localhost:7687')
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
    return 1
}

run_one() {
    local snap="$1"
    local dump="$REPO/dumps_archive/iyp-${snap}.dump"
    local out="$REPO/data_cache/new_angles/${snap}/facilities.csv"

    if [ ! -f "$dump" ]; then
        echo "MISSING $dump — skip"
        return 1
    fi
    if [ -s "$out" ]; then
        echo "SKIP $snap (facilities.csv already exists)"
        return 0
    fi

    echo
    echo "=== $(date -Iseconds) $snap ==="
    ensure_symlink "$SCRATCH/data" "$REPO/data"
    ensure_symlink "$SCRATCH/dumps" "$REPO/dumps"

    sg docker -c "docker stop iyp iyp_loader 2>/dev/null; docker rm iyp iyp_loader 2>/dev/null" >/dev/null 2>&1
    rm -rf "$SCRATCH/data/databases" "$SCRATCH/data/transactions"
    rm -f "$SCRATCH/dumps/neo4j.dump"

    cp "$dump" "$SCRATCH/dumps/neo4j.dump"
    sg docker -c "uid=$(id -u) gid=$(id -g) docker compose --profile local up -d" 2>&1

    if ! wait_for_neo4j; then
        echo "   ABORT $snap"
        return 1
    fi

    # Run only the 4 DC extractors
    IYP_SNAPSHOT="$snap" python3 -c "
from analysis.new_angles import extract_data as e
print(f'[dc] snap={e._SNAP}  out={e.OUT_DIR}', flush=True)
e.extract_facilities()
e.extract_facility_members()
e.extract_facility_ixps()
e.extract_peeringdb_nets()
" 2>&1

    sg docker -c "docker stop iyp iyp_loader 2>/dev/null; docker rm iyp iyp_loader 2>/dev/null" >/dev/null 2>&1
    rm -rf "$SCRATCH/data/databases" "$SCRATCH/data/transactions"
    rm -f "$SCRATCH/dumps/neo4j.dump"
    echo "=== done $snap $(date -Iseconds) ==="
}

echo "=== run_dc_timeseries start $(date -Iseconds) ===" | tee -a "$LOG"
for snap in $DUMPS; do
    run_one "$snap" 2>&1 | tee -a "$LOG"
done
echo "=== run_dc_timeseries end $(date -Iseconds) ===" | tee -a "$LOG"
