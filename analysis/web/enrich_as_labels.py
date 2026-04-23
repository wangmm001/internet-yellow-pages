"""Utilities for enriching AS node labels with organization names.

Reads data_cache/complex_network/as_organization.csv (122k rows,
asn,org_name,org_countries) and builds a dict {asn_int: org_name}.

De-duplication heuristic (per ASN, when multiple rows exist):
  1. Prefer rows that look like org names (not IP/address-style strings).
  2. Among candidates, prefer shorter names.
  3. Tie-break by alphabetical order.
"""
import csv
import os
import re
from pathlib import Path

# Default path — mirrors the DATA_DIR convention in complex_network/utils.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAP_CSV = str(
    Path(os.environ.get('IYP_ANALYSIS_DATA_DIR',
                        _REPO_ROOT / 'data_cache' / 'complex_network'))
    / 'as_organization.csv'
)

_ADDRESS_RE = re.compile(
    r'\d{1,3}\.\d{1,3}\.\d{1,3}|\b\d{5}\b|P\.?O\.?\s*Box',
    re.IGNORECASE,
)


def _address_like(name: str) -> bool:
    return bool(_ADDRESS_RE.search(name))


def load_as_org_map(csv_path: str = DEFAULT_MAP_CSV) -> dict:
    """Return {asn_int: org_name} with de-duplication heuristic.

    Raises OSError if csv_path does not exist.
    """
    candidates: dict = {}  # asn -> list[str]
    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                asn = int(row['asn'])
            except (KeyError, ValueError):
                continue
            name = (row.get('org_name') or '').strip()
            if not name:
                continue
            candidates.setdefault(asn, []).append(name)

    result: dict = {}
    for asn, names in candidates.items():
        # Prefer non-address-like names
        clean = [n for n in names if not _address_like(n)] or names
        # Shortest first, then alpha
        clean.sort(key=lambda n: (len(n), n))
        result[asn] = clean[0]
    return result
