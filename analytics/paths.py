"""Project paths for the catalog analytics package."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"
DEMO_DIR = PROJECT_ROOT / "demo" / "synthetic"
DEMO_DB_PATH = DEMO_DIR / "parts_catalog_demo.sqlite"
DEMO_REPORT_DIR = DEMO_DIR / "report"
POWERBI_DIR = PROJECT_ROOT / "powerbi"
POWERQUERY_DIR = PROJECT_ROOT / "powerquery"
