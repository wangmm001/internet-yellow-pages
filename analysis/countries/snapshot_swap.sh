#!/usr/bin/env bash
# Swap Neo4j database dumps for time-series analysis.
#
# WARNING: destructive. Backs up current dump then REMOVES the loaded
# database before loading a new one.
#
# Usage:
#   ./snapshot_swap.sh 2025-04-08     # swap to 2025-04-08 dump
#   ./snapshot_swap.sh 2026-04-08     # swap back
#
# Requires:
#   - docker (user must be able to run `sg docker -c ...`)
#   - curl, rm, cp, mkdir
#   - ~20 GB free for backup + ~15 GB for download + ~200 GB for loaded DB
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <YYYY-MM-DD>"
    echo "Example: $0 2025-04-08"
    exit 1
fi

TARGET="$1"
YEAR="${TARGET:0:4}"
MONTH="${TARGET:5:2}"
DAY="${TARGET:8:2}"

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
DUMPS="$REPO/dumps"
DATA="$REPO/data"
BACKUP_DIR="$REPO/data_cache/dumps_backup"
DUMP_URL="https://archive.ihr.live/ihr/iyp/$YEAR/$MONTH/$DAY/iyp-$TARGET.dump"

mkdir -p "$BACKUP_DIR"

echo "────────────────────────────────────────────────"
echo "  Target dump:  $DUMP_URL"
echo "  Repo root:    $REPO"
echo "────────────────────────────────────────────────"
echo

# Probe availability
echo "[1/7] probe target dump URL…"
if ! curl -sIf "$DUMP_URL" --max-time 30 > /dev/null; then
    echo "ERROR: dump not available at $DUMP_URL"
    exit 1
fi
SIZE=$(curl -sI "$DUMP_URL" --max-time 30 | awk -v IGNORECASE=1 '/content-length/{print $2}' | tr -d '\r')
echo "  Size: ~$((SIZE / 1024 / 1024 / 1024)) GB"

# Check disk
FREE_GB=$(df -BG "$REPO" | awk 'NR==2{gsub(/G/,"",$4); print $4}')
echo "[2/7] disk free: ${FREE_GB}G (need ≥ 40G download + backup buffer)"
if [ "$FREE_GB" -lt 40 ]; then
    echo "ERROR: insufficient free disk"; exit 1
fi

# Backup current dump (if present)
if [ -f "$DUMPS/neo4j.dump" ]; then
    CUR_SIZE=$(stat -c%s "$DUMPS/neo4j.dump" 2>/dev/null || echo 0)
    BAK_NAME="neo4j-$(date +%F-%H%M%S).dump"
    echo "[3/7] backing up current dump → $BACKUP_DIR/$BAK_NAME  (~$((CUR_SIZE/1024/1024/1024))G)"
    cp "$DUMPS/neo4j.dump" "$BACKUP_DIR/$BAK_NAME"
else
    echo "[3/7] no current dump to back up"
fi

# Stop Neo4j
echo "[4/7] stopping Neo4j container…"
if sg docker -c 'docker ps --format "{{.Names}}"' | grep -q '^iyp$'; then
    sg docker -c 'docker stop iyp' || true
fi

# Remove current DB
echo "[5/7] removing current loaded database (frees ~184G)…"
if [ -d "$DATA/databases" ]; then
    rm -rf "$DATA/databases" "$DATA/transactions"
    echo "  removed"
fi

# Download new dump
echo "[6/7] downloading $TARGET dump…"
curl -L --progress-bar "$DUMP_URL" -o "$DUMPS/neo4j.dump"

# Restart via docker compose (loader will pick up)
echo "[7/7] restarting compose (loader will populate DB)…"
cd "$REPO"
uid="$(id -u)" gid="$(id -g)" sg docker -c 'docker compose --profile local up -d'

echo
echo "Swap initiated. Neo4j loader runs in background."
echo "Watch progress:  sg docker -c 'docker logs -f iyp'"
echo "Test connection (after a few minutes):"
echo "  python3 -c \"from analysis.complex_network.utils import run_query; print(run_query('MATCH (n) RETURN count(n) as c'))\""
