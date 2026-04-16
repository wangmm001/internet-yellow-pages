# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Internet Yellow Pages (IYP) is a knowledge database built on Neo4j that aggregates information about Internet resources (ASNs, IP prefixes, domain names, IXPs, etc.) from ~30 data sources. Data is collected by **crawlers**, enriched by **post-processors**, and stored as a graph with typed nodes and relationships.

## Setup

```bash
python3 -m venv --upgrade-deps .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.json.example config.json  # then edit neo4j credentials and API keys
pre-commit install
```

A running Neo4j instance is required. For local development use Docker:
```bash
mkdir -p dumps data
# Download a dump to dumps/neo4j.dump, then:
uid="$(id -u)" gid="$(id -g)" docker compose --profile local up
```

## Running Crawlers

Run a single crawler standalone:
```bash
python3 -m iyp.crawlers.<org>.<crawler_name>
```

Run a crawler with its unit test (checks that relationships were created):
```bash
python3 -m iyp.crawlers.<org>.<crawler_name> --unit-test
```

Build the full database (runs all crawlers from config.json, then post-processors):
```bash
python3 create_db.py
```

## Linting and Code Style

Pre-commit hooks handle formatting automatically. The toolchain is: autoflake, isort (with `neo4j` as third-party), autopep8 (aggressive=3), docformatter, double-quote-string-fixer, flake8.

- Max line length: 120 characters
- Max doc length: 88 characters
- Strings use single quotes (enforced by double-quote-string-fixer)
- Run manually: `pre-commit run --all-files`

There are no automated test suites beyond per-crawler `unit_test()` methods, which verify that expected relationship types exist in the database after a crawl.

## Architecture

### Core (`iyp/__init__.py`)

- **`IYP`** class: Neo4j connection wrapper. Provides `batch_get_nodes_by_single_prop()`, `batch_get_nodes()`, `get_node()`, `batch_add_links()`, `add_links()`, `batch_add_properties()` for graph operations. All batch operations auto-commit in chunks of `BATCH_SIZE` (50,000).
- **`BaseCrawler`**: Base class for all crawlers. Provides `self.iyp` (IYP instance), `self.reference` (provenance metadata dict), `link_generator()`, `unit_test()`, and temp directory management.
- **`BasePostProcess`**: Base class for post-processing scripts (e.g., `iyp/post/ip2prefix.py`).
- **Property formatters** (`prop_formatters` dict): Automatically normalizes `asn` (int), `ip` (compressed), `prefix` (compressed), `country_code` (uppercase). Be aware these transform values during node/link creation.

### Crawlers (`iyp/crawlers/<org>/<name>.py`)

Each crawler module must define:
- `ORG`: organization name string
- `URL`: data source URL string
- `NAME`: unique crawler name as `directory.file` (e.g., `ripe.as_names`)
- `Crawler` class extending `BaseCrawler` with `run()` and `unit_test()` methods
- `main()` function with argparse supporting `--unit-test`

The constructor signature is always `Crawler(ORG, URL, NAME)` -- do not change this interface as `create_db.py` depends on it.

### Post-processors (`iyp/post/`)

Run after all crawlers. Derive cross-dataset relationships (e.g., mapping IPs to prefixes, adding address family labels, extracting hostnames from URLs).

### Database Pipeline (`create_db.py`)

Spins up a fresh Neo4j Docker container, runs all crawlers listed in `config.json["iyp"]["crawlers"]`, runs post-processors from `config.json["iyp"]["post"]`, stops the container, and dumps the database.

### Configuration (`config.json`)

Controls which crawlers/post-processors to run and stores API keys for data sources (PeeringDB, Cloudflare, OpenINTEL, etc.) plus Neo4j connection settings.

## Crawler Development Conventions

- Use `logging.{info,warning,error}` -- never print to stdout/stderr or call `sys.exit()`. Raise exceptions instead.
- Use sets to track unique nodes; avoid creating duplicate nodes/relationships.
- Use batch functions (`batch_get_nodes_by_single_prop`, `batch_add_links`) by default.
- Pass `all=False` to `batch_get_nodes_by_single_prop` unless you genuinely need every node of that type.
- Don't manipulate/filter data -- IYP combines sources and detecting differences is a feature.
- Attach data-source-specific properties to relationships, not nodes. Nodes should only contain shared ID properties.
- Every link must include `reference_org`, `reference_url_data`, `reference_name`, and `reference_time_fetch` (provided via `self.reference`).
- Each crawler directory must have a `README.md` describing the dataset and how it is modeled.

## Git Branch Naming

`<type>/<issue|issue-number>/{<additional-fixes>}` where type is one of: `wip`, `feat`, `bug`, `exp`.
