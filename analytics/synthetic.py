"""Deterministic synthetic catalog used by the public demo and the tests.

The rows are fiction. Folder names, articles, invoices, and companies
do not come from the private catalog.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from analytics.contract import SYNTHETIC_LABEL, SYNTHETIC_NOTICE
from analytics.paths import SCHEMA_PATH

UPDATED_AT = "2026-03-10 09:00:00"

DELIVERIES: tuple[dict, ...] = (
    {
        "id": 1,
        "folder_name": "SHIP-A",
        "excel_filename": "ship_a_demo.xlsx",
        "imported_at": "2026-01-15 09:00:00",
    },
    {
        "id": 2,
        "folder_name": "SHIP-B",
        "excel_filename": "ship_b_demo.xlsx",
        "imported_at": "2026-02-20 09:00:00",
    },
    {
        "id": 3,
        "folder_name": "SHIP-C",
        "excel_filename": "ship_c_demo.xlsx",
        "imported_at": "2026-03-10 09:00:00",
    },
)

PARTS: tuple[dict, ...] = (
    {
        "article": "HIC-100",
        "name_en": "Bearing",
        "name_ru": "Подшипник",
        "graph_description": "Bearing assembly",
        "tnved": "8482109000",
        "manufacturer": "Helios Works",
        "country_origin": "DE",
        "tech_doc_filename": "HIC-100.docx",
        "tech_doc_path": "docs/HIC-100.docx",
        "updated_from_delivery_id": 3,
    },
    {
        "article": "HIC-200",
        "name_en": None,
        "name_ru": "Уплотнение",
        "graph_description": "Rubber seal",
        "tnved": "4016930000",
        "manufacturer": "Helios Works",
        "country_origin": "CN",
        "tech_doc_filename": None,
        "tech_doc_path": None,
        "updated_from_delivery_id": 2,
    },
    {
        "article": "HIC-300",
        "name_en": "Filter element",
        "name_ru": "Фильтр",
        "graph_description": None,
        "tnved": None,
        "manufacturer": "Helios Works",
        "country_origin": "IT",
        "tech_doc_filename": "HIC-300.docx",
        "tech_doc_path": None,
        "updated_from_delivery_id": 2,
    },
    {
        "article": "HIC-400",
        "name_en": "Gasket kit",
        "name_ru": "Прокладка",
        "graph_description": "Gasket kit",
        "tnved": "8484100000",
        "manufacturer": "Helios Works",
        "country_origin": "DE",
        "tech_doc_filename": "HIC-400.docx",
        "tech_doc_path": "docs/HIC-400.docx",
        "updated_from_delivery_id": 3,
    },
    {
        "article": "HIC-500",
        "name_en": None,
        "name_ru": "Клапан",
        "graph_description": "Valve body",
        "tnved": "8481800000",
        "manufacturer": "Archive Mills",
        "country_origin": "PL",
        "tech_doc_filename": None,
        "tech_doc_path": None,
        "updated_from_delivery_id": None,
    },
    {
        "article": "HIC-600",
        "name_en": "O-ring",
        "name_ru": "Кольцо",
        "graph_description": "O-ring",
        "tnved": "4016930000",
        "manufacturer": "Helios Works",
        "country_origin": "CN",
        "tech_doc_filename": "HIC-600.docx",
        "tech_doc_path": "docs/HIC-600.docx",
        "updated_from_delivery_id": 1,
    },
)

def _line(**values: object) -> dict:
    return values


LINES: tuple[dict, ...] = (
    _line(
        id=1, delivery_id=1, article="HIC-100", name_en="Bearing", name_ru="Подшипник",
        graph_description="Bearing assembly", tnved="8482109000", country_origin="DE",
        quantity=10, unit_price_rub=100, batch_price_rub=1000,
        net_weight_unit=0.25, net_weight_total=2.5, gross_weight_unit=0.5, gross_weight_total=5,
    ),
    _line(
        id=2, delivery_id=1, article="HIC-200", name_en=None, name_ru="Уплотнение",
        graph_description="Rubber seal", tnved="4016930000", country_origin="CN",
        quantity=4, unit_price_rub=50, batch_price_rub=200,
        net_weight_unit=0.25, net_weight_total=1, gross_weight_unit=0.5, gross_weight_total=2,
    ),
    _line(
        id=3, delivery_id=1, article="HIC-600", name_en="O-ring", name_ru="Кольцо",
        graph_description="O-ring", tnved="4016930000", country_origin="CN",
        quantity=2, unit_price_rub=25, batch_price_rub=40,
        net_weight_unit=0.25, net_weight_total=0.5, gross_weight_unit=None, gross_weight_total=None,
    ),
    _line(
        id=4, delivery_id=1, article="HIC-100", name_en="Bearing", name_ru="Подшипник",
        graph_description="Bearing assembly", tnved="8482109000", country_origin="DE",
        quantity=5, unit_price_rub=100, batch_price_rub=500,
        net_weight_unit=0.25, net_weight_total=1.25, gross_weight_unit=0.5, gross_weight_total=2.5,
    ),
    _line(
        id=5, delivery_id=2, article="HIC-100", name_en="Bearing", name_ru="Подшипник",
        graph_description="Bearing assembly", tnved="8482109000", country_origin="DE",
        quantity=1, unit_price_rub=100, batch_price_rub=100,
        net_weight_unit=0.25, net_weight_total=0.25, gross_weight_unit=0.5, gross_weight_total=0.5,
    ),
    _line(
        id=6, delivery_id=2, article="HIC-200", name_en=None, name_ru="Уплотнение",
        graph_description="Rubber seal", tnved="4016930000", country_origin="CN",
        quantity=2, unit_price_rub=50, batch_price_rub=100,
        net_weight_unit=0.25, net_weight_total=0.75, gross_weight_unit=0.5, gross_weight_total=0.25,
    ),
    _line(
        id=7, delivery_id=2, article="HIC-300", name_en="Filter element", name_ru="Фильтр",
        graph_description=None, tnved=None, country_origin="IT",
        quantity=8, unit_price_rub=10, batch_price_rub=None,
        net_weight_unit=None, net_weight_total=1, gross_weight_unit=None, gross_weight_total=None,
    ),
    _line(
        id=8, delivery_id=3, article="HIC-100", name_en="Bearing", name_ru="Подшипник",
        graph_description="Bearing assembly", tnved="8482109000", country_origin="DE",
        quantity=3, unit_price_rub=100, batch_price_rub=300,
        net_weight_unit=0.25, net_weight_total=0.75, gross_weight_unit=0.5, gross_weight_total=1.5,
    ),
    _line(
        id=9, delivery_id=3, article="HIC-400", name_en="Gasket kit", name_ru="Прокладка",
        graph_description="Gasket kit", tnved="8484100000", country_origin="DE",
        quantity=6, unit_price_rub=0, batch_price_rub=0,
        net_weight_unit=0.25, net_weight_total=1.5, gross_weight_unit=0.5, gross_weight_total=3,
    ),
    _line(
        id=10, delivery_id=3, article="HIC-400", name_en="Gasket kit", name_ru="Прокладка",
        graph_description="Gasket kit", tnved="8484100000", country_origin="DE",
        quantity=None, unit_price_rub=15, batch_price_rub=90,
        net_weight_unit=None, net_weight_total=None, gross_weight_unit=None, gross_weight_total=None,
    ),
)

ARCHIVE_SOURCES: tuple[dict, ...] = (
    {
        "id": 1,
        "filename": "historical_descriptions_demo.csv",
        "imported_at": "2026-01-01 08:00:00",
    },
)

ARCHIVE_LINES: tuple[dict, ...] = (
    {"id": 1, "archive_source_id": 1, "article": "HIC-500", "excel_row": 2},
    {"id": 2, "archive_source_id": 1, "article": "HIC-600", "excel_row": 3},
)


def build_database(db_path: Path, schema_path: Path | None = None) -> Path:
    """Create a new SQLite file. An existing file at db_path is replaced."""
    schema = (schema_path or SCHEMA_PATH).read_text(encoding="utf-8")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
        connection.execute(
            """
            CREATE TABLE dataset_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO dataset_meta (key, value) VALUES (?, ?)",
            (("label", SYNTHETIC_LABEL), ("notice", SYNTHETIC_NOTICE)),
        )
        connection.executemany(
            """
            INSERT INTO deliveries (id, folder_name, excel_filename, imported_at)
            VALUES (:id, :folder_name, :excel_filename, :imported_at)
            """,
            DELIVERIES,
        )
        part_rows = []
        for part in PARTS:
            part_rows.append(
                {
                    "article": part["article"],
                    "name_en": part["name_en"],
                    "name_ru": part["name_ru"],
                    "graph_description": part["graph_description"],
                    "tnved": part["tnved"],
                    "manufacturer": part["manufacturer"],
                    "country_origin": part["country_origin"],
                    "tech_doc_filename": part["tech_doc_filename"],
                    "tech_doc_path": part["tech_doc_path"],
                    "updated_from_delivery_id": part["updated_from_delivery_id"],
                    "updated_at": UPDATED_AT,
                }
            )
        connection.executemany(
            """
            INSERT INTO parts (
                article, name_en, name_ru, graph_description, tnved, manufacturer,
                country_origin, tech_doc_filename, tech_doc_path,
                updated_from_delivery_id, updated_at
            ) VALUES (
                :article, :name_en, :name_ru, :graph_description, :tnved, :manufacturer,
                :country_origin, :tech_doc_filename, :tech_doc_path,
                :updated_from_delivery_id, :updated_at
            )
            """,
            part_rows,
        )
        line_rows = []
        for line in LINES:
            line_rows.append(
                {
                    **line,
                    "excel_row": line["id"],
                    "excel_filename": next(
                        row["excel_filename"]
                        for row in DELIVERIES
                        if row["id"] == line["delivery_id"]
                    ),
                    "invoice": f"INV-2026-{line['delivery_id']:03d}",
                }
            )
        connection.executemany(
            """
            INSERT INTO shipment_lines (
                id, delivery_id, article, name_en, name_ru, graph_description, tnved,
                country_origin, quantity, unit_price_rub, batch_price_rub,
                net_weight_unit, net_weight_total, gross_weight_unit, gross_weight_total,
                excel_filename, excel_row, invoice
            ) VALUES (
                :id, :delivery_id, :article, :name_en, :name_ru, :graph_description, :tnved,
                :country_origin, :quantity, :unit_price_rub, :batch_price_rub,
                :net_weight_unit, :net_weight_total, :gross_weight_unit, :gross_weight_total,
                :excel_filename, :excel_row, :invoice
            )
            """,
            line_rows,
        )
        connection.executemany(
            """
            INSERT INTO archive_sources (id, filename, imported_at)
            VALUES (:id, :filename, :imported_at)
            """,
            ARCHIVE_SOURCES,
        )
        connection.executemany(
            """
            INSERT INTO archive_lines (id, archive_source_id, article, excel_row)
            VALUES (:id, :archive_source_id, :article, :excel_row)
            """,
            ARCHIVE_LINES,
        )
        connection.commit()
    finally:
        connection.close()
    return db_path
