"""Hand-checked metrics for the synthetic catalog, plus report contracts."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path

from analytics.contract import MEASURES, MODEL_TABLES, SYNTHETIC_LABEL, TABLE_COLUMNS
from analytics.export import PublicationGuardError, assert_demo_target_is_synthetic, export_report
from analytics.load import connect_readonly, load_catalog, require_catalog_schema
from analytics.metrics import Analysis, analyze, values_mismatch
from analytics.paths import DEMO_REPORT_DIR, PROJECT_ROOT, SCHEMA_PATH
from analytics.powerbi_project import (
    DATA_ROOT_PLACEHOLDER,
    PAGE_SCHEMA,
    PBIP_SCHEMA,
    PBIR_SCHEMA,
    PBISM_SCHEMA,
    REPORT_SCHEMA,
    VISUAL_SCHEMA,
    write_powerbi_project,
)
from analytics.synthetic import build_database

ROOT = PROJECT_ROOT

EXPECTED_KPIS = {
    "shipment_line_count": 10,
    "distinct_shipped_articles": 5,
    "intro_line_count": 5,
    "repeat_line_count": 5,
    "declared_batch_value_rub": 2330.0,
    "total_quantity": 41.0,
    "total_net_weight": 9.5,
    "total_gross_weight": 14.75,
    "price_applicable_lines": 8,
    "price_mismatch_lines": 1,
    "net_weight_applicable_lines": 8,
    "net_weight_mismatch_lines": 1,
    "gross_weight_applicable_lines": 7,
    "gross_weight_mismatch_lines": 1,
    "gross_below_net_lines": 1,
    "incomplete_price_lines": 2,
    "incomplete_net_weight_lines": 1,
    "part_count": 6,
    "filled_key_fields": 35,
    "key_field_slots": 42,
    "average_catalog_completeness": 35 / 42,
    "parts_missing_tech_doc": 3,
    "parts_missing_name_en": 2,
    "parts_missing_name_ru": 0,
    "parts_missing_graph_description": 1,
    "parts_missing_tnved": 1,
    "parts_filename_without_path": 1,
    "archive_only_parts": 1,
    "parts_with_shipment": 5,
    "new_article_appearances": 5,
    "repeat_article_appearances": 3,
    "articles_in_multiple_deliveries": 2,
    "archive_line_count": 2,
    "archive_distinct_articles": 2,
    "archive_articles_also_shipped": 1,
    "quality_issue_rows": 22,
}

EXPECTED_LINE_FLAGS = {
    1: {"is_intro_line": 1, "price_mismatch": 0, "net_weight_mismatch": 0, "gross_below_net": 0},
    2: {"is_intro_line": 1, "missing_name_en": 1, "price_mismatch": 0},
    3: {"is_intro_line": 1, "price_mismatch": 1, "price_check_applicable": 1, "gross_weight_check_applicable": 0},
    4: {"is_intro_line": 0, "price_mismatch": 0},
    5: {"is_intro_line": 0},
    6: {
        "is_intro_line": 0,
        "net_weight_mismatch": 1,
        "gross_weight_mismatch": 1,
        "gross_below_net": 1,
        "missing_name_en": 1,
    },
    7: {
        "is_intro_line": 1,
        "incomplete_price": 1,
        "incomplete_net_weight": 1,
        "missing_graph_description": 1,
        "missing_tnved": 1,
        "price_check_applicable": 0,
    },
    8: {"is_intro_line": 0},
    9: {"is_intro_line": 1, "nonpositive_unit_price": 1, "nonpositive_batch_price": 1, "price_mismatch": 0},
    10: {"is_intro_line": 0, "missing_quantity": 1, "incomplete_price": 1, "price_check_applicable": 0},
}

EXPECTED_DELIVERIES = {
    "SHIP-A": {
        "line_count": 4,
        "distinct_articles": 3,
        "new_articles": 3,
        "repeat_articles": 0,
        "intro_lines": 3,
        "repeat_lines": 1,
        "total_quantity": 21.0,
        "declared_batch_value_rub": 1740.0,
        "total_net_weight": 5.25,
        "total_gross_weight": 9.5,
        "price_mismatch_lines": 1,
    },
    "SHIP-B": {
        "line_count": 3,
        "distinct_articles": 3,
        "new_articles": 1,
        "repeat_articles": 2,
        "declared_batch_value_rub": 200.0,
        "total_net_weight": 2.0,
        "total_gross_weight": 0.75,
        "net_weight_mismatch_lines": 1,
        "gross_below_net_lines": 1,
    },
    "SHIP-C": {
        "line_count": 3,
        "distinct_articles": 2,
        "new_articles": 1,
        "repeat_articles": 1,
        "total_quantity": 9.0,
        "declared_batch_value_rub": 390.0,
        "total_net_weight": 2.25,
        "total_gross_weight": 4.5,
    },
}

EXPECTED_ISSUES = {
    ("line", "2", "missing_name_en"),
    ("line", "3", "price_mismatch"),
    ("line", "6", "missing_name_en"),
    ("line", "6", "net_weight_mismatch"),
    ("line", "6", "gross_weight_mismatch"),
    ("line", "6", "gross_below_net"),
    ("line", "7", "incomplete_price"),
    ("line", "7", "incomplete_net_weight"),
    ("line", "7", "missing_graph_description"),
    ("line", "7", "missing_tnved"),
    ("line", "9", "nonpositive_unit_price"),
    ("line", "9", "nonpositive_batch_price"),
    ("line", "10", "incomplete_price"),
    ("line", "10", "missing_quantity"),
    ("part", "HIC-200", "missing_name_en"),
    ("part", "HIC-200", "missing_tech_doc"),
    ("part", "HIC-300", "missing_graph_description"),
    ("part", "HIC-300", "missing_tnved"),
    ("part", "HIC-300", "missing_tech_doc"),
    ("part", "HIC-300", "filename_without_path"),
    ("part", "HIC-500", "missing_name_en"),
    ("part", "HIC-500", "missing_tech_doc"),
}


def _analysis_from_db(db_path: Path) -> Analysis:
    connection = connect_readonly(db_path)
    try:
        loaded = load_catalog(connection)
    finally:
        connection.close()
    return analyze(
        deliveries=loaded["deliveries"],
        parts=loaded["parts"],
        shipment_lines=loaded["shipment_lines"],
        archive_sources=loaded["archive_sources"],
        archive_lines=loaded["archive_lines"],
        dataset_label=loaded["dataset_label"],
        dataset_notice=loaded["dataset_notice"],
    )


class MetricTests(unittest.TestCase):
    def test_price_and_weight_tolerance_boundaries(self) -> None:
        self.assertEqual(values_mismatch(10, 1, 10.05, 0.05, 0.005), (0, 1))
        self.assertEqual(values_mismatch(10, 1, 10.06, 0.05, 0.005), (1, 1))
        self.assertEqual(values_mismatch(1, 0, 0.001, 0.001, 0.005), (0, 1))
        self.assertEqual(values_mismatch(1, 0, 0.0011, 0.001, 0.005), (1, 1))
        self.assertEqual(values_mismatch(None, 1, 1, 0.05, 0.005), (0, 0))

    def test_blank_text_is_incomplete(self) -> None:
        analysis = analyze(
            deliveries=[{"id": 1, "folder_name": "ONLY", "imported_at": "2026-01-01"}],
            parts=[
                {
                    "article": "BLANK",
                    "name_en": "   ",
                    "name_ru": "Имя",
                    "graph_description": None,
                    "tnved": "1",
                    "manufacturer": "Maker",
                    "country_origin": "DE",
                    "tech_doc_filename": "BLANK.docx",
                    "tech_doc_path": "",
                }
            ],
            shipment_lines=[],
            archive_sources=[],
            archive_lines=[],
            dataset_label="unit",
        )
        part = analysis.tables["dim_part"][0]
        self.assertEqual(part["has_name_en"], 0)
        self.assertEqual(part["filename_without_path"], 1)
        self.assertEqual(part["filled_field_count"], 4)

    def test_first_delivery_follows_imported_at_before_id(self) -> None:
        analysis = analyze(
            deliveries=[
                {"id": 2, "folder_name": "LATER", "imported_at": "2026-05-01"},
                {"id": 1, "folder_name": "EARLIER", "imported_at": "2026-04-01"},
            ],
            parts=[{"article": "A", "name_en": "Part", "name_ru": "Деталь"}],
            shipment_lines=[
                {"id": 10, "delivery_id": 2, "article": "A", "quantity": 1, "unit_price_rub": 2, "batch_price_rub": 2},
                {"id": 11, "delivery_id": 1, "article": "A", "quantity": 1, "unit_price_rub": 2, "batch_price_rub": 2},
            ],
            archive_sources=[],
            archive_lines=[],
            dataset_label="unit",
        )
        intro = {row["line_id"]: row["is_intro_line"] for row in analysis.tables["fact_shipment_line"]}
        self.assertEqual(intro[11], 1)
        self.assertEqual(intro[10], 0)
        by_folder = {row["folder_name"]: row for row in analysis.tables["fact_delivery_summary"]}
        self.assertEqual(by_folder["EARLIER"]["new_articles"], 1)
        self.assertEqual(by_folder["LATER"]["repeat_articles"], 1)

    def test_synthetic_catalog_matches_hand_calculation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo.sqlite"
            build_database(db_path, SCHEMA_PATH)
            analysis = _analysis_from_db(db_path)
        self.assertEqual(analysis.dataset_label, SYNTHETIC_LABEL)
        self.assertTrue(analysis.reconciliations_ok)
        for name, expected in EXPECTED_KPIS.items():
            if isinstance(expected, float):
                self.assertAlmostEqual(float(analysis.kpis[name]), expected, places=9, msg=name)
            else:
                self.assertEqual(analysis.kpis[name], expected, name)
        self.assertAlmostEqual(float(analysis.kpis["average_catalog_completeness"]), 35 / 42, places=12)
        lines = {row["line_id"]: row for row in analysis.tables["fact_shipment_line"]}
        for line_id, flags in EXPECTED_LINE_FLAGS.items():
            for flag_name, expected in flags.items():
                self.assertEqual(lines[line_id][flag_name], expected, f"line {line_id} {flag_name}")
        deliveries = {row["folder_name"]: row for row in analysis.tables["fact_delivery_summary"]}
        for folder, expected in EXPECTED_DELIVERIES.items():
            for name, value in expected.items():
                if isinstance(value, float):
                    self.assertAlmostEqual(deliveries[folder][name], value, places=9, msg=folder + name)
                else:
                    self.assertEqual(deliveries[folder][name], value, folder + name)
        issues = {
            (row["grain"], row["entity_id"], row["issue_type"])
            for row in analysis.tables["data_quality_issue"]
        }
        self.assertEqual(issues, EXPECTED_ISSUES)
        countries = {row["label"]: row for row in analysis.compositions["country"]}
        self.assertEqual(countries["DE"]["line_count"], 6)
        self.assertAlmostEqual(countries["DE"]["declared_batch_value_rub"], 1990.0, places=9)
        self.assertEqual(countries["CN"]["line_count"], 3)
        self.assertAlmostEqual(countries["CN"]["declared_batch_value_rub"], 340.0, places=9)
        self.assertEqual(countries["IT"]["line_count"], 1)
        self.assertEqual(countries["IT"]["declared_batch_value_rub"], 0.0)
        tnved = {row["label"]: row for row in analysis.compositions["tnved"]}
        self.assertEqual(tnved["8482109000"]["line_count"], 4)
        self.assertAlmostEqual(tnved["8482109000"]["declared_batch_value_rub"], 1900.0, places=9)
        self.assertEqual(tnved["(missing)"]["line_count"], 1)
        self.assertEqual(tnved["8484100000"]["declared_batch_value_rub"], 90.0)

    def test_readonly_connection_rejects_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo.sqlite"
            build_database(db_path, SCHEMA_PATH)
            db_path.chmod(stat.S_IREAD)
            try:
                connection = connect_readonly(db_path)
                try:
                    with self.assertRaises(sqlite3.OperationalError):
                        connection.execute("UPDATE deliveries SET folder_name = 'NO'")
                    loaded = load_catalog(connection)
                    self.assertEqual(len(loaded["shipment_lines"]), 10)
                finally:
                    connection.close()
            finally:
                db_path.chmod(stat.S_IREAD | stat.S_IWRITE)

    def test_private_catalog_schema_is_compatible(self) -> None:
        private_db = ROOT / "storage" / "parts_catalog.db"
        if not private_db.exists():
            self.skipTest("private catalog is not on this machine")
        connection = connect_readonly(private_db)
        try:
            require_catalog_schema(connection)
            names = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertIn("shipment_lines", names)
        finally:
            connection.close()


class ReportContractTests(unittest.TestCase):
    def test_export_reconciles_csv_sums_and_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo.sqlite"
            out_dir = Path(tmp) / "report"
            build_database(db_path, SCHEMA_PATH)
            analysis = _analysis_from_db(db_path)
            export_report(analysis, out_dir)
            with (out_dir / "fact_shipment_line.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertNotIn("questions", rows[0])
            self.assertNotIn("answers", rows[0])
            self.assertEqual(len(rows), 10)
            self.assertEqual(sum(int(row["is_intro_line"]) for row in rows), 5)
            self.assertAlmostEqual(
                sum(float(row["batch_price_rub"]) for row in rows if row["batch_price_rub"]),
                2330.0,
                places=9,
            )
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            preview = (out_dir / "preview.html").read_text(encoding="utf-8")
            self.assertIn("October 2026 portfolio extension", preview)
            self.assertIn("2,330.00", preview)
            self.assertIn("not revenue", preview.lower())
            found = dict(re.findall(r'data-kpi="([^"]+)" data-value="([^"]+)"', preview))
            for name, raw_value in found.items():
                self.assertEqual(json.loads(raw_value), summary["kpis"][name])
            sample = (out_dir / "sample_analysis.md").read_text(encoding="utf-8")
            self.assertIn("2,330.00", sample)
            self.assertIn("Not production customs history", sample)
            self.assertTrue(all(item["ok"] for item in summary["reconciliations"]))

    def test_non_synthetic_output_cannot_land_in_the_demo_tree(self) -> None:
        with self.assertRaises(PublicationGuardError):
            assert_demo_target_is_synthetic("unspecified_local_catalog", DEMO_REPORT_DIR)
        assert_demo_target_is_synthetic(SYNTHETIC_LABEL, DEMO_REPORT_DIR)

    def test_powerbi_project_uses_documented_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_powerbi_project(root)
            pbip = json.loads((root / "CustomsPartsAnalytics.pbip").read_text(encoding="utf-8"))
            self.assertEqual(pbip["$schema"], PBIP_SCHEMA)
            self.assertEqual(pbip["version"], "1.0")
            report = root / "CustomsPartsAnalytics.Report"
            model = root / "CustomsPartsAnalytics.SemanticModel"
            pbir = json.loads((report / "definition.pbir").read_text(encoding="utf-8"))
            self.assertEqual(pbir["$schema"], PBIR_SCHEMA)
            self.assertEqual(pbir["version"], "4.0")
            self.assertEqual(
                pbir["datasetReference"]["byPath"]["path"],
                "../CustomsPartsAnalytics.SemanticModel",
            )
            pbism = json.loads((model / "definition.pbism").read_text(encoding="utf-8"))
            self.assertEqual(pbism["$schema"], PBISM_SCHEMA)
            self.assertEqual(pbism["version"], "4.0")
            page = json.loads(
                (report / "definition" / "pages" / "overview" / "page.json").read_text(encoding="utf-8")
            )
            visual = json.loads(
                (
                    report
                    / "definition"
                    / "pages"
                    / "overview"
                    / "visuals"
                    / "overview_card_01"
                    / "visual.json"
                ).read_text(encoding="utf-8")
            )
            report_json = json.loads((report / "definition" / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(page["$schema"], PAGE_SCHEMA)
            self.assertEqual(visual["$schema"], VISUAL_SCHEMA)
            self.assertEqual(report_json["$schema"], REPORT_SCHEMA)
            self.assertEqual(visual["visual"]["visualType"], "card")
            measures = (model / "definition" / "tables" / "_Measures.tmdl").read_text(encoding="utf-8")
            expressions = (model / "definition" / "expressions.tmdl").read_text(encoding="utf-8")
            self.assertIn(DATA_ROOT_PLACEHOLDER, expressions)
            self.assertIn("IsParameterQuery=true", expressions)
            for measure in MEASURES:
                self.assertIn(measure["expression"], measures)
                self.assertIn(measure["kpi"], EXPECTED_KPIS)
            for table in MODEL_TABLES:
                body = (model / "definition" / "tables" / f"{table}.tmdl").read_text(encoding="utf-8")
                self.assertIn(f"/{table}.csv", body)
                for column, _type_name in TABLE_COLUMNS[table]:
                    self.assertIn(f"sourceColumn: {column}", body)
            self.assertEqual(list((root).rglob("*.pbix")), [])
            dax = (root / "measures.dax").read_text(encoding="utf-8")
            self.assertIn("Not executed", dax)

    def test_checked_in_demo_matches_the_metric_code(self) -> None:
        summary_path = ROOT / "demo" / "synthetic" / "report" / "summary.json"
        preview_path = ROOT / "demo" / "synthetic" / "report" / "preview.html"
        self.assertTrue(summary_path.is_file(), "run scripts/build_synthetic_catalog.py")
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo.sqlite"
            build_database(db_path, SCHEMA_PATH)
            fresh = _analysis_from_db(db_path)
        checked = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(checked["dataset_label"], SYNTHETIC_LABEL)
        for name, value in checked["kpis"].items():
            if isinstance(value, float):
                self.assertAlmostEqual(float(fresh.kpis[name]), value, places=9, msg=name)
            else:
                self.assertEqual(fresh.kpis[name], value, name)
        preview = preview_path.read_text(encoding="utf-8")
        self.assertIn("2,330.00", preview)
        self.assertIn("October 2026 portfolio extension", preview)

    def test_publishable_tree_has_no_private_markers(self) -> None:
        markers = (
            "RLT" + "00206",
            "19" + "651",
            "13" + "662",
            "5502" + "0578",
            "users" + ".json",
            "pbkdf" + "2",
            "gho" + "_",
            "ghp" + "_",
            "Тех" + "нич",
            "для " + "дт",
        )
        roots = [
            ROOT / "analytics",
            ROOT / "tests",
            ROOT / "demo" / "synthetic",
            ROOT / "powerbi",
            ROOT / "powerquery",
            ROOT / "sql" / "schema.sql",
            ROOT / "scripts" / "analyze_catalog.py",
            ROOT / "scripts" / "build_synthetic_catalog.py",
        ]
        hits: list[str] = []
        for root in roots:
            files = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
            for path in files:
                if path.suffix == ".pyc" or "__pycache__" in path.parts:
                    continue
                text = path.read_bytes().decode("utf-8", errors="replace")
                for marker in markers:
                    if marker in text:
                        hits.append(f"{path.relative_to(ROOT)}:{marker}")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
