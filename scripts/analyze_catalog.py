#!/usr/bin/env python3
"""Read a parts catalog SQLite file and write report tables.

The connection is read-only. Output from a private catalog can contain
article numbers and shipment totals; keep that output unpublished.
The synthetic demo is the portfolio dataset.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.contract import SYNTHETIC_LABEL
from analytics.export import PublicationGuardError, export_report
from analytics.load import connect_readonly, load_catalog
from analytics.metrics import analyze
from analytics.paths import DEMO_DB_PATH, DEMO_REPORT_DIR
from analytics.synthetic import build_database

PRINTED_KPIS = (
    "shipment_line_count",
    "distinct_shipped_articles",
    "intro_line_count",
    "repeat_line_count",
    "new_article_appearances",
    "repeat_article_appearances",
    "declared_batch_value_rub",
    "part_count",
    "average_catalog_completeness",
    "parts_missing_tech_doc",
    "parts_missing_name_en",
    "parts_filename_without_path",
    "archive_only_parts",
    "price_mismatch_lines",
    "net_weight_mismatch_lines",
    "gross_weight_mismatch_lines",
    "gross_below_net_lines",
    "quality_issue_rows",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="SQLite catalog to read")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Read the synthetic demo database, building it when it is absent",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Directory for CSV, summary.json, sample_analysis.md, and preview.html",
    )
    return parser.parse_args(argv)


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.demo and args.db:
        raise SystemExit("Use either --demo or --db.")
    if args.demo:
        if not DEMO_DB_PATH.exists():
            build_database(DEMO_DB_PATH)
        return DEMO_DB_PATH, args.out or DEMO_REPORT_DIR
    if args.db is None:
        raise SystemExit("Pass --db PATH or --demo.")
    return args.db, args.out or (ROOT / "analytics_output")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    db_path, out_dir = resolve_paths(args)
    connection = connect_readonly(db_path)
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
    print("Read-only catalog analytics. Do not publish output from a private catalog.")
    print(f"Dataset: {analysis.dataset_label}")
    if analysis.dataset_label != SYNTHETIC_LABEL:
        print("This is not the synthetic portfolio dataset.")
    for name in PRINTED_KPIS:
        print(f"{name}: {analysis.kpis[name]}")
    passed = sum(1 for item in analysis.reconciliations if item["ok"])
    print(f"Reconciliations: {passed}/{len(analysis.reconciliations)} passed")
    for item in analysis.reconciliations:
        if not item["ok"]:
            print(f"FAIL {item['name']}: {item['detail']}")
    try:
        export_report(analysis, out_dir)
    except PublicationGuardError as exc:
        print(exc)
        return 2
    print(f"Report written to {out_dir.resolve()}")
    return 0 if analysis.reconciliations_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
