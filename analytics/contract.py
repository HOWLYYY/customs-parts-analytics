"""Shared column, measure, and tolerance definitions.

The export tables, tests, Power Query scripts, and TMDL model all read
this module so the report contract cannot drift from the metric code.
"""

from __future__ import annotations

SYNTHETIC_LABEL = "synthetic_october_2026_portfolio"
SYNTHETIC_NOTICE = (
    "Synthetic data for an October 2026 portfolio extension. "
    "Not production customs history."
)

# Absolute floor, then a relative share of the stated total.
PRICE_ABS_TOLERANCE = 0.05
PRICE_REL_TOLERANCE = 0.005
WEIGHT_ABS_TOLERANCE = 0.001
WEIGHT_REL_TOLERANCE = 0.005

KEY_FIELDS: tuple[str, ...] = (
    "name_en",
    "name_ru",
    "graph_description",
    "tnved",
    "manufacturer",
    "country_origin",
    "tech_doc_path",
)

# Tables loaded by Power Query. kpi_summary.csv is a report extract, not a model table.
MODEL_TABLES: tuple[str, ...] = (
    "dim_delivery",
    "dim_part",
    "fact_shipment_line",
    "fact_delivery_summary",
    "fact_delivery_article",
    "fact_archive_line",
    "data_quality_issue",
)

ColumnType = str  # "int" | "double" | "text"

TABLE_COLUMNS: dict[str, tuple[tuple[str, ColumnType], ...]] = {
    "dim_delivery": (
        ("delivery_id", "int"),
        ("folder_name", "text"),
        ("imported_at", "text"),
        ("sort_order", "int"),
    ),
    "dim_part": (
        ("article", "text"),
        ("name_en", "text"),
        ("name_ru", "text"),
        ("graph_description", "text"),
        ("tnved", "text"),
        ("manufacturer", "text"),
        ("country_origin", "text"),
        ("tech_doc_present", "int"),
        ("filename_without_path", "int"),
        ("filled_field_count", "int"),
        ("key_field_count", "int"),
        ("completeness_ratio", "double"),
        ("has_name_en", "int"),
        ("has_name_ru", "int"),
        ("has_graph_description", "int"),
        ("has_tnved", "int"),
        ("has_manufacturer", "int"),
        ("has_country_origin", "int"),
        ("has_shipment", "int"),
        ("is_archive_only", "int"),
    ),
    "fact_shipment_line": (
        ("line_id", "int"),
        ("delivery_id", "int"),
        ("article", "text"),
        ("name_en", "text"),
        ("quantity", "double"),
        ("unit_price_rub", "double"),
        ("batch_price_rub", "double"),
        ("net_weight_unit", "double"),
        ("net_weight_total", "double"),
        ("gross_weight_unit", "double"),
        ("gross_weight_total", "double"),
        ("country_origin", "text"),
        ("tnved", "text"),
        ("is_intro_line", "int"),
        ("price_mismatch", "int"),
        ("price_check_applicable", "int"),
        ("net_weight_mismatch", "int"),
        ("net_weight_check_applicable", "int"),
        ("gross_weight_mismatch", "int"),
        ("gross_weight_check_applicable", "int"),
        ("gross_below_net", "int"),
        ("incomplete_price", "int"),
        ("incomplete_net_weight", "int"),
        ("missing_name_en", "int"),
        ("missing_name_ru", "int"),
        ("missing_graph_description", "int"),
        ("missing_tnved", "int"),
        ("missing_quantity", "int"),
        ("nonpositive_unit_price", "int"),
        ("nonpositive_batch_price", "int"),
    ),
    "fact_delivery_summary": (
        ("delivery_id", "int"),
        ("folder_name", "text"),
        ("imported_at", "text"),
        ("sort_order", "int"),
        ("line_count", "int"),
        ("distinct_articles", "int"),
        ("new_articles", "int"),
        ("repeat_articles", "int"),
        ("intro_lines", "int"),
        ("repeat_lines", "int"),
        ("total_quantity", "double"),
        ("declared_batch_value_rub", "double"),
        ("total_net_weight", "double"),
        ("total_gross_weight", "double"),
        ("price_mismatch_lines", "int"),
        ("net_weight_mismatch_lines", "int"),
        ("gross_weight_mismatch_lines", "int"),
        ("gross_below_net_lines", "int"),
        ("lines_missing_name_en", "int"),
        ("lines_missing_graph_description", "int"),
        ("lines_missing_tnved", "int"),
        ("distinct_tnved", "int"),
        ("distinct_countries", "int"),
    ),
    "fact_delivery_article": (
        ("delivery_id", "int"),
        ("article", "text"),
        ("is_new_article", "int"),
        ("is_repeat_article", "int"),
    ),
    "fact_archive_line": (
        ("archive_line_id", "int"),
        ("article", "text"),
        ("archive_source", "text"),
        ("in_shipment", "int"),
    ),
    "data_quality_issue": (
        ("issue_id", "int"),
        ("grain", "text"),
        ("entity_id", "text"),
        ("article", "text"),
        ("delivery_id", "int"),
        ("delivery_folder", "text"),
        ("issue_type", "text"),
    ),
}

# DAX is not executed on this machine. These expressions are the model
# contract; Python tests reconcile the same sums on the exported columns.
MEASURES: tuple[dict[str, str], ...] = (
    {
        "name": "Total Shipment Lines",
        "expression": "COUNTROWS ( fact_shipment_line )",
        "format": "#,0",
        "folder": "Volume",
        "description": "Count of shipment lines.",
        "kpi": "shipment_line_count",
    },
    {
        "name": "Distinct Shipped Articles",
        "expression": "DISTINCTCOUNT ( fact_shipment_line[article] )",
        "format": "#,0",
        "folder": "Volume",
        "description": "Distinct articles present on shipment lines.",
        "kpi": "distinct_shipped_articles",
    },
    {
        "name": "Intro Lines",
        "expression": "SUM ( fact_shipment_line[is_intro_line] )",
        "format": "#,0",
        "folder": "Repeat articles",
        "description": "Lines that are the first shipment line for an article.",
        "kpi": "intro_line_count",
    },
    {
        "name": "Repeat Lines",
        "expression": "[Total Shipment Lines] - [Intro Lines]",
        "format": "#,0",
        "folder": "Repeat articles",
        "description": "Shipment lines after an article's introduction line.",
        "kpi": "repeat_line_count",
    },
    {
        "name": "Declared Batch Value RUB",
        "expression": "SUM ( fact_shipment_line[batch_price_rub] )",
        "format": "#,0.00",
        "folder": "Value",
        "description": "Sum of batch_price_rub. Declared line value, not revenue.",
        "kpi": "declared_batch_value_rub",
    },
    {
        "name": "Total Quantity",
        "expression": "SUM ( fact_shipment_line[quantity] )",
        "format": "#,0.00",
        "folder": "Volume",
        "description": "Sum of shipment line quantity. Blank quantities are excluded.",
        "kpi": "total_quantity",
    },
    {
        "name": "Total Net Weight",
        "expression": "SUM ( fact_shipment_line[net_weight_total] )",
        "format": "#,0.000",
        "folder": "Volume",
        "description": "Sum of net_weight_total. Blank totals are excluded.",
        "kpi": "total_net_weight",
    },
    {
        "name": "Total Gross Weight",
        "expression": "SUM ( fact_shipment_line[gross_weight_total] )",
        "format": "#,0.000",
        "folder": "Volume",
        "description": "Sum of gross_weight_total. Blank totals are excluded.",
        "kpi": "total_gross_weight",
    },
    {
        "name": "Price Mismatch Lines",
        "expression": "SUM ( fact_shipment_line[price_mismatch] )",
        "format": "#,0",
        "folder": "Data quality",
        "description": "Lines where quantity times unit price disagrees with batch price.",
        "kpi": "price_mismatch_lines",
    },
    {
        "name": "Net Weight Mismatch Lines",
        "expression": "SUM ( fact_shipment_line[net_weight_mismatch] )",
        "format": "#,0",
        "folder": "Data quality",
        "description": "Lines where quantity times unit net weight disagrees with the net total.",
        "kpi": "net_weight_mismatch_lines",
    },
    {
        "name": "Gross Weight Mismatch Lines",
        "expression": "SUM ( fact_shipment_line[gross_weight_mismatch] )",
        "format": "#,0",
        "folder": "Data quality",
        "description": "Lines where quantity times unit gross weight disagrees with the gross total.",
        "kpi": "gross_weight_mismatch_lines",
    },
    {
        "name": "Gross Below Net Lines",
        "expression": "SUM ( fact_shipment_line[gross_below_net] )",
        "format": "#,0",
        "folder": "Data quality",
        "description": "Lines where both weight totals are present and gross is below net.",
        "kpi": "gross_below_net_lines",
    },
    {
        "name": "Catalog Parts",
        "expression": "COUNTROWS ( dim_part )",
        "format": "#,0",
        "folder": "Catalog completeness",
        "description": "Rows in the canonical parts card.",
        "kpi": "part_count",
    },
    {
        "name": "Average Catalog Completeness",
        "expression": "DIVIDE ( SUM ( dim_part[filled_field_count] ), SUM ( dim_part[key_field_count] ) )",
        "format": "0.00%",
        "folder": "Catalog completeness",
        "description": "Filled key fields divided by key-field slots.",
        "kpi": "average_catalog_completeness",
    },
    {
        "name": "Parts Missing Tech Doc",
        "expression": "CALCULATE ( COUNTROWS ( dim_part ), dim_part[tech_doc_present] = 0 )",
        "format": "#,0",
        "folder": "Catalog completeness",
        "description": "Parts with no tech_doc_path.",
        "kpi": "parts_missing_tech_doc",
    },
    {
        "name": "Parts Missing English Name",
        "expression": "CALCULATE ( COUNTROWS ( dim_part ), dim_part[has_name_en] = 0 )",
        "format": "#,0",
        "folder": "Catalog completeness",
        "description": "Parts with a blank name_en.",
        "kpi": "parts_missing_name_en",
    },
    {
        "name": "Parts Missing Graph Description",
        "expression": "CALCULATE ( COUNTROWS ( dim_part ), dim_part[has_graph_description] = 0 )",
        "format": "#,0",
        "folder": "Catalog completeness",
        "description": "Parts with a blank graph_description.",
        "kpi": "parts_missing_graph_description",
    },
    {
        "name": "Parts Missing TNVED",
        "expression": "CALCULATE ( COUNTROWS ( dim_part ), dim_part[has_tnved] = 0 )",
        "format": "#,0",
        "folder": "Catalog completeness",
        "description": "Parts with a blank tnved code.",
        "kpi": "parts_missing_tnved",
    },
    {
        "name": "Filename Without Tech Doc Path",
        "expression": "CALCULATE ( COUNTROWS ( dim_part ), dim_part[filename_without_path] = 1 )",
        "format": "#,0",
        "folder": "Catalog completeness",
        "description": "Parts that name a tech-doc file but have no stored path.",
        "kpi": "parts_filename_without_path",
    },
    {
        "name": "Archive Only Parts",
        "expression": "CALCULATE ( COUNTROWS ( dim_part ), dim_part[is_archive_only] = 1 )",
        "format": "#,0",
        "folder": "Catalog completeness",
        "description": "Parts that appear in the archive and on no shipment line.",
        "kpi": "archive_only_parts",
    },
    {
        "name": "New Article Appearances",
        "expression": "SUM ( fact_delivery_article[is_new_article] )",
        "format": "#,0",
        "folder": "Repeat articles",
        "description": "Delivery-article pairs whose delivery is the article's first shipment.",
        "kpi": "new_article_appearances",
    },
    {
        "name": "Repeat Article Appearances",
        "expression": "SUM ( fact_delivery_article[is_repeat_article] )",
        "format": "#,0",
        "folder": "Repeat articles",
        "description": "Delivery-article pairs that follow the article's first shipment.",
        "kpi": "repeat_article_appearances",
    },
    {
        "name": "Archive Lines",
        "expression": "COUNTROWS ( fact_archive_line )",
        "format": "#,0",
        "folder": "Volume",
        "description": "Rows imported from archive workbooks.",
        "kpi": "archive_line_count",
    },
    {
        "name": "Quality Issue Rows",
        "expression": "COUNTROWS ( data_quality_issue )",
        "format": "#,0",
        "folder": "Data quality",
        "description": "Part and line data-quality issues exported by the analytics job.",
        "kpi": "quality_issue_rows",
    },
)

DEFINITIONS: dict[str, str] = {
    "catalog_completeness": (
        "A key field is filled when it is not null and, for text, not blank. "
        "The seven key fields are name_en, name_ru, graph_description, tnved, "
        "manufacturer, country_origin, and tech_doc_path. "
        "Average completeness is filled key fields divided by parts times 7."
    ),
    "repeat_vs_new": (
        "Deliveries are ordered by imported_at, then id. "
        "An article's introduction line is its earliest shipment line in that order. "
        "A delivery-article pair is new when that delivery is the article's first shipment; "
        "otherwise it is a repeat appearance. "
        "The sum of new appearances equals the number of distinct shipped articles."
    ),
    "declared_batch_value": (
        "Declared batch value is the sum of shipment_lines.batch_price_rub. "
        "Blank amounts are left out of the sum. This is not revenue, margin, or turnover."
    ),
    "price_consistency": (
        "A price check applies when quantity, unit_price_rub, and batch_price_rub "
        "are all present. It mismatches when the absolute gap between "
        "quantity * unit_price_rub and batch_price_rub is greater than "
        f"max({PRICE_ABS_TOLERANCE}, {PRICE_REL_TOLERANCE} * abs(batch_price_rub))."
    ),
    "weight_consistency": (
        "A weight check applies only when quantity, the unit weight, and the total "
        "weight are all present. Absence of gross weight is not itself an issue. "
        "The mismatch tolerance is "
        f"max({WEIGHT_ABS_TOLERANCE}, {WEIGHT_REL_TOLERANCE} * abs(total)). "
        "Gross below net applies when both totals are present and "
        f"gross_weight_total + {WEIGHT_ABS_TOLERANCE} < net_weight_total."
    ),
    "missing_docs": (
        "A part is missing its tech doc when tech_doc_path is blank. "
        "Filename without path means tech_doc_filename is filled and tech_doc_path is not. "
        "Archive-only parts are articles present in archive_lines and absent from shipment_lines."
    ),
}
