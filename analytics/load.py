"""Read a catalog database without writing to it."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from analytics.contract import SYNTHETIC_LABEL

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "deliveries": ("id", "folder_name", "imported_at"),
    "parts": (
        "article",
        "name_en",
        "name_ru",
        "graph_description",
        "tnved",
        "manufacturer",
        "country_origin",
        "tech_doc_filename",
        "tech_doc_path",
    ),
    "shipment_lines": (
        "id",
        "delivery_id",
        "article",
        "name_en",
        "name_ru",
        "graph_description",
        "tnved",
        "country_origin",
        "quantity",
        "unit_price_rub",
        "batch_price_rub",
        "net_weight_unit",
        "net_weight_total",
        "gross_weight_unit",
        "gross_weight_total",
    ),
    "archive_sources": ("id", "filename"),
    "archive_lines": ("id", "archive_source_id", "article"),
}


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    path = db_path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Catalog database not found: {path}")
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def require_catalog_schema(connection: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        )
    }
    missing_tables = [table for table in REQUIRED_COLUMNS if table not in existing]
    if missing_tables:
        raise ValueError(f"Catalog is missing tables: {', '.join(missing_tables)}")
    problems: list[str] = []
    for table, columns in REQUIRED_COLUMNS.items():
        found = _columns(connection, table)
        absent = [column for column in columns if column not in found]
        if absent:
            problems.append(f"{table}: {', '.join(absent)}")
    if problems:
        raise ValueError("Catalog is missing columns: " + "; ".join(problems))


def _rows(connection: sqlite3.Connection, sql: str) -> list[dict]:
    return [dict(row) for row in connection.execute(sql)]


def load_catalog(connection: sqlite3.Connection) -> dict:
    require_catalog_schema(connection)
    meta: dict[str, str] = {}
    tables = {
        row["name"]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if "dataset_meta" in tables:
        for row in connection.execute("SELECT key, value FROM dataset_meta"):
            meta[str(row["key"])] = str(row["value"])
    label = meta.get("label") or "unspecified_local_catalog"
    notice = meta.get("notice") or ""
    return {
        "dataset_label": label,
        "dataset_notice": notice,
        "synthetic": label == SYNTHETIC_LABEL,
        "deliveries": _rows(
            connection,
            "SELECT id, folder_name, excel_filename, imported_at FROM deliveries",
        ),
        "parts": _rows(connection, "SELECT * FROM parts"),
        "shipment_lines": _rows(connection, "SELECT * FROM shipment_lines"),
        "archive_sources": _rows(connection, "SELECT id, filename, imported_at FROM archive_sources"),
        "archive_lines": _rows(connection, "SELECT * FROM archive_lines"),
    }
