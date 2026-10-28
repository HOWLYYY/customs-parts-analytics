"""Write a PBIP/TMDL/PBIR project that follows Microsoft's published schemas.

Power BI Desktop is not available on this Mac, so this module does not
claim the project was opened or refreshed in Desktop. The JSON files use
the schema URLs current in the microsoft/json-schemas repository on
28 October 2026:

- PBIP shortcut 1.0.0
- semantic model definitionProperties 1.0.0, version 4.0 (TMDL folder)
- report definitionProperties 2.0.0, version 4.0 (PBIR folder)
- PBIR report 3.3.0, page 2.1.0, visualContainer 2.13.0
- pages metadata 1.1.0 and version metadata 1.0.0
- TMDL as documented for compatibility level 1567
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from analytics.contract import MEASURES, MODEL_TABLES, TABLE_COLUMNS

PBIP_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json"
PBISM_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json"
PBIR_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json"
PLATFORM_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json"
REPORT_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
VISUAL_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json"
PAGES_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"
VERSION_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json"

PROJECT_NAME = "CustomsPartsAnalytics"
DATA_ROOT_PLACEHOLDER = "/ABSOLUTE/PATH/TO/demo/synthetic/report"
_NAMESPACE = uuid.UUID("6f4d9a1e-2c7b-4e55-9a10-8c3d5e7f1a20")


def _tag(name: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, name))


def _json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _m_type(column_type: str) -> str:
    if column_type == "int":
        return "Int64.Type"
    if column_type == "double":
        return "type number"
    return "type text"


def power_query(table: str) -> str:
    pairs = ", ".join(
        f'{{"{name}", {_m_type(column_type)}}}'
        for name, column_type in TABLE_COLUMNS[table]
    )
    return (
        "let\n"
        "    Root = DataRoot,\n"
        f'    Source = Csv.Document(File.Contents(Root & "/{table}.csv"), '
        "[Delimiter = \",\", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),\n"
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),\n"
        f'    Typed = Table.TransformColumnTypes(Promoted, {{{pairs}}}, "en-US")\n'
        "in\n"
        "    Typed"
    )


def _tmdl_column(table: str, name: str, column_type: str) -> list[str]:
    data_type = {"int": "int64", "double": "double", "text": "string"}[column_type]
    lines = [
        f"\tcolumn {name}",
        f"\t\tdataType: {data_type}",
        f"\t\tlineageTag: {_tag(f'{table}.{name}')}",
        f"\t\tsourceColumn: {name}",
        "\t\tsummarizeBy: none",
    ]
    if table == "dim_part" and name == "article":
        lines.append("\t\tisKey")
    if table == "dim_delivery" and name == "delivery_id":
        lines.append("\t\tisKey")
    if column_type == "double":
        lines.insert(2, '\t\tformatString: "#,0.00"')
    return lines


def _table_tmdl(table: str) -> str:
    lines = [
        f"table {table}",
        f"\tlineageTag: {_tag(f'table.{table}')}",
        "",
        f"\tpartition {table} = m",
        "\t\tmode: import",
        "\t\tsource =",
    ]
    for m_line in power_query(table).splitlines():
        lines.append(f"\t\t\t\t{m_line}")
    lines.append("")
    for name, column_type in TABLE_COLUMNS[table]:
        lines.extend(_tmdl_column(table, name, column_type))
        lines.append("")
    lines.append("\tannotation PBI_ResultType = Table")
    lines.append("")
    return "\n".join(lines)


def _measures_tmdl() -> str:
    lines = [
        "table _Measures",
        f"\tlineageTag: {_tag('table._Measures')}",
        "",
        "\tpartition _Measures = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        '\t\t\t\t    Source = Table.FromRows({{0}}, {"MeasureKey"})',
        "\t\t\t\tin",
        "\t\t\t\t    Source",
        "",
        "\tcolumn MeasureKey",
        "\t\tdataType: int64",
        "\t\tisHidden",
        f"\t\tlineageTag: {_tag('_Measures.MeasureKey')}",
        "\t\tsourceColumn: MeasureKey",
        "\t\tsummarizeBy: none",
        "",
    ]
    for measure in MEASURES:
        lines.append(f"\tmeasure '{measure['name']}' = {measure['expression']}")
        lines.append(f"\t\tformatString: \"{measure['format']}\"")
        lines.append(f"\t\tdisplayFolder: {measure['folder']}")
        lines.append(f"\t\tdescription: \"{measure['description']}\"")
        lines.append(f"\t\tlineageTag: {_tag('measure.' + measure['name'])}")
        lines.append("")
    lines.append("\tannotation PBI_ResultType = Table")
    lines.append("")
    return "\n".join(lines)


def _model_tmdl() -> str:
    tables = list(MODEL_TABLES) + ["_Measures"]
    query_order = json.dumps(tables, separators=(",", ":"))
    lines = [
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: en-US",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "\tannotation __PBI_TimeIntelligenceEnabled = 0",
        f"\tannotation PBI_QueryOrder = {query_order}",
        "",
    ]
    for table in tables:
        lines.append(f"\tref table {table}")
    lines.append("")
    return "\n".join(lines)


def _relationships_tmdl() -> str:
    pairs = (
        ("line_delivery", "fact_shipment_line.delivery_id", "dim_delivery.delivery_id"),
        ("line_part", "fact_shipment_line.article", "dim_part.article"),
        ("summary_delivery", "fact_delivery_summary.delivery_id", "dim_delivery.delivery_id"),
        ("appearance_delivery", "fact_delivery_article.delivery_id", "dim_delivery.delivery_id"),
        ("appearance_part", "fact_delivery_article.article", "dim_part.article"),
        ("archive_part", "fact_archive_line.article", "dim_part.article"),
        ("issue_delivery", "data_quality_issue.delivery_id", "dim_delivery.delivery_id"),
        ("issue_part", "data_quality_issue.article", "dim_part.article"),
    )
    blocks = []
    for name, left, right in pairs:
        blocks.append(
            "\n".join(
                [
                    f"relationship {name}",
                    f"\tfromColumn: {left}",
                    f"\ttoColumn: {right}",
                    "\tfromCardinality: many",
                    "\ttoCardinality: one",
                    "",
                ]
            )
        )
    return "\n".join(blocks)


def _expressions_tmdl() -> str:
    return "\n".join(
        [
            "expression DataRoot = "
            f"\"{DATA_ROOT_PLACEHOLDER}\" meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]",
            f"\tlineageTag: {_tag('expression.DataRoot')}",
            "\tannotation PBI_ResultType = Text",
            "",
        ]
    )


def _measure_field(measure_name: str) -> dict:
    return {
        "field": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "_Measures"}},
                "Property": measure_name,
            }
        },
        "queryRef": f"_Measures.{measure_name}",
        "nativeQueryRef": measure_name,
    }


def _column_field(table: str, column: str) -> dict:
    return {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": column,
            }
        },
        "queryRef": f"{table}.{column}",
        "nativeQueryRef": column,
    }


def _visual(name: str, x: int, y: int, width: int, height: int, z: int, visual: dict) -> dict:
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": z,
            "height": height,
            "width": width,
            "tabOrder": z,
        },
        "visual": visual,
    }


def _card(measure_name: str) -> dict:
    return {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [_measure_field(measure_name)]}}},
        "drillFilterOtherVisuals": True,
    }


def _table(table: str, columns: list[str]) -> dict:
    return {
        "visualType": "tableEx",
        "query": {
            "queryState": {
                "Values": {"projections": [_column_field(table, column) for column in columns]}
            }
        },
        "drillFilterOtherVisuals": True,
    }


def _column_chart(category_table: str, category_column: str, measure_name: str) -> dict:
    return {
        "visualType": "clusteredColumnChart",
        "query": {
            "queryState": {
                "Category": {"projections": [_column_field(category_table, category_column)]},
                "Y": {"projections": [_measure_field(measure_name)]},
            }
        },
        "drillFilterOtherVisuals": True,
    }


def _page(name: str, display_name: str) -> dict:
    return {
        "$schema": PAGE_SCHEMA,
        "name": name,
        "displayName": display_name,
        "displayOption": "FitToPage",
        "height": 720,
        "width": 1280,
    }


def _platform(item_type: str, display_name: str, logical_id: str) -> dict:
    return {
        "$schema": PLATFORM_SCHEMA,
        "metadata": {"type": item_type, "displayName": display_name},
        "config": {"version": "2.0", "logicalId": logical_id},
    }


def write_power_query_scripts(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    header = (
        "// Power Query for the synthetic catalog export.\n"
        "// Set DataRoot to the absolute path of demo/synthetic/report before refresh.\n"
        f'// The PBIP parameter default is "{DATA_ROOT_PLACEHOLDER}".\n'
    )
    (directory / "DataRoot.pq").write_text(
        header + f'"{DATA_ROOT_PLACEHOLDER}" meta [IsParameterQuery = true, Type = "Text"]\n',
        encoding="utf-8",
    )
    for table in MODEL_TABLES:
        (directory / f"{table}.pq").write_text(header + power_query(table) + "\n", encoding="utf-8")


def write_powerbi_project(directory: Path) -> Path:
    report = directory / f"{PROJECT_NAME}.Report"
    model = directory / f"{PROJECT_NAME}.SemanticModel"
    definition = model / "definition"
    tables = definition / "tables"
    pages = report / "definition" / "pages"
    for folder in (tables, pages):
        folder.mkdir(parents=True, exist_ok=True)

    (directory / f"{PROJECT_NAME}.pbip").write_text(
        _json(
            {
                "$schema": PBIP_SCHEMA,
                "version": "1.0",
                "artifacts": [{"report": {"path": f"{PROJECT_NAME}.Report"}}],
                "settings": {"enableAutoRecovery": True},
            }
        ),
        encoding="utf-8",
    )
    (model / "definition.pbism").write_text(
        _json({"$schema": PBISM_SCHEMA, "version": "4.0", "settings": {}}),
        encoding="utf-8",
    )
    (model / ".platform").write_text(
        _json(_platform("SemanticModel", PROJECT_NAME, _tag("platform.semantic"))),
        encoding="utf-8",
    )
    (definition / "database.tmdl").write_text(
        "database\n\tcompatibilityLevel: 1567\n",
        encoding="utf-8",
    )
    (definition / "model.tmdl").write_text(_model_tmdl(), encoding="utf-8")
    (definition / "relationships.tmdl").write_text(_relationships_tmdl(), encoding="utf-8")
    (definition / "expressions.tmdl").write_text(_expressions_tmdl(), encoding="utf-8")
    for table in MODEL_TABLES:
        (tables / f"{table}.tmdl").write_text(_table_tmdl(table), encoding="utf-8")
    (tables / "_Measures.tmdl").write_text(_measures_tmdl(), encoding="utf-8")

    (report / "definition.pbir").write_text(
        _json(
            {
                "$schema": PBIR_SCHEMA,
                "version": "4.0",
                "datasetReference": {
                    "byPath": {"path": f"../{PROJECT_NAME}.SemanticModel"}
                },
            }
        ),
        encoding="utf-8",
    )
    (report / ".platform").write_text(
        _json(_platform("Report", PROJECT_NAME, _tag("platform.report"))),
        encoding="utf-8",
    )
    report_definition = report / "definition"
    report_definition.mkdir(parents=True, exist_ok=True)
    (report_definition / "version.json").write_text(
        _json({"$schema": VERSION_SCHEMA, "version": "2.0.0"}),
        encoding="utf-8",
    )
    (report_definition / "report.json").write_text(
        _json(
            {
                "$schema": REPORT_SCHEMA,
                "themeCollection": {
                    "baseTheme": {
                        "name": "CY24SU10",
                        "reportVersionAtImport": {
                            "visual": "2.13.0",
                            "page": "2.1.0",
                            "report": "3.3.0",
                        },
                        "type": "SharedResources",
                    }
                },
                "settings": {
                    "useStylableVisualContainerHeader": True,
                    "exportDataMode": "AllowSummarized",
                    "defaultDrillFilterOtherVisuals": True,
                    "allowChangeFilterTypes": True,
                },
            }
        ),
        encoding="utf-8",
    )

    page_names = ("overview", "shipments", "data_quality")
    (pages / "pages.json").write_text(
        _json(
            {
                "$schema": PAGES_SCHEMA,
                "pageOrder": list(page_names),
                "activePageName": "overview",
            }
        ),
        encoding="utf-8",
    )
    titles = {
        "overview": "Overview",
        "shipments": "Shipments",
        "data_quality": "Data quality",
    }
    for name in page_names:
        page_dir = pages / name
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "page.json").write_text(_json(_page(name, titles[name])), encoding="utf-8")

    overview_measures = (
        "Total Shipment Lines",
        "Distinct Shipped Articles",
        "Intro Lines",
        "Repeat Lines",
        "Declared Batch Value RUB",
        "Average Catalog Completeness",
        "Parts Missing Tech Doc",
        "Price Mismatch Lines",
        "Net Weight Mismatch Lines",
        "Gross Below Net Lines",
    )
    for index, measure_name in enumerate(overview_measures):
        visual_name = f"overview_card_{index + 1:02d}"
        visual_dir = pages / "overview" / "visuals" / visual_name
        visual_dir.mkdir(parents=True, exist_ok=True)
        column = index % 5
        row = index // 5
        payload = _visual(
            visual_name,
            20 + column * 250,
            20 + row * 150,
            230,
            130,
            index,
            _card(measure_name),
        )
        (visual_dir / "visual.json").write_text(_json(payload), encoding="utf-8")

    shipment_table = _visual(
        "shipment_summary_table",
        20,
        20,
        760,
        420,
        0,
        _table(
            "fact_delivery_summary",
            [
                "folder_name",
                "line_count",
                "distinct_articles",
                "new_articles",
                "repeat_articles",
                "declared_batch_value_rub",
                "price_mismatch_lines",
                "net_weight_mismatch_lines",
            ],
        ),
    )
    shipment_chart = _visual(
        "shipment_value_chart",
        800,
        20,
        460,
        420,
        1,
        _column_chart("dim_delivery", "folder_name", "Declared Batch Value RUB"),
    )
    for payload in (shipment_table, shipment_chart):
        visual_dir = pages / "shipments" / "visuals" / payload["name"]
        visual_dir.mkdir(parents=True, exist_ok=True)
        (visual_dir / "visual.json").write_text(_json(payload), encoding="utf-8")

    issue_table = _visual(
        "issue_table",
        20,
        20,
        760,
        640,
        0,
        _table(
            "data_quality_issue",
            ["grain", "delivery_folder", "article", "issue_type"],
        ),
    )
    issue_chart = _visual(
        "issue_chart",
        800,
        20,
        460,
        420,
        1,
        _column_chart("data_quality_issue", "issue_type", "Quality Issue Rows"),
    )
    for payload in (issue_table, issue_chart):
        visual_dir = pages / "data_quality" / "visuals" / payload["name"]
        visual_dir.mkdir(parents=True, exist_ok=True)
        (visual_dir / "visual.json").write_text(_json(payload), encoding="utf-8")

    measures_dax = ["// DAX measures on _Measures. Not executed in this repository.", ""]
    for measure in MEASURES:
        measures_dax.append(f"// {measure['description']}")
        measures_dax.append(f"{measure['name']} = {measure['expression']}")
        measures_dax.append("")
    (directory / "measures.dax").write_text("\n".join(measures_dax), encoding="utf-8")
    return directory
