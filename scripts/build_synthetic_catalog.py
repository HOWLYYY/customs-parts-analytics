#!/usr/bin/env python3
"""Build the synthetic catalog, report extracts, and Power BI project files."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.load import connect_readonly, load_catalog
from analytics.metrics import analyze
from analytics.paths import DEMO_DB_PATH, DEMO_REPORT_DIR, POWERBI_DIR, POWERQUERY_DIR
from analytics.powerbi_project import write_power_query_scripts, write_powerbi_project
from analytics.synthetic import build_database
from scripts.analyze_catalog import main as analyze_main


def main() -> int:
    build_database(DEMO_DB_PATH)
    connection = connect_readonly(DEMO_DB_PATH)
    try:
        loaded = load_catalog(connection)
    finally:
        connection.close()
    analysis = analyze(
        deliveries=loaded["deliveries"],
        parts=loaded["parts"],
        shipment_lines=loaded["shipment_lines"],
        archive_sources=loaded["archive_sources"],
        archive_lines=loaded["archive_lines"],
        dataset_label=loaded["dataset_label"],
        dataset_notice=loaded["dataset_notice"],
    )
    if not analysis.reconciliations_ok:
        print("Synthetic catalog failed reconciliation.")
        return 1
    write_powerbi_project(POWERBI_DIR)
    write_power_query_scripts(POWERQUERY_DIR)
    return analyze_main(["--demo", "--out", str(DEMO_REPORT_DIR)])


if __name__ == "__main__":
    raise SystemExit(main())
