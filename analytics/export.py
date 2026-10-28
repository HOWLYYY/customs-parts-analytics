"""Write report tables, a KPI summary, and a portable HTML preview."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

from analytics.contract import SYNTHETIC_LABEL, TABLE_COLUMNS
from analytics.metrics import Analysis
from analytics.paths import DEMO_DIR, POWERBI_DIR, PROJECT_ROOT


class PublicationGuardError(ValueError):
    """Raised when a private catalog would be written into the demo tree."""


def assert_demo_target_is_synthetic(dataset_label: str, out_dir: Path) -> None:
    """Keep private catalog extracts out of the folders that are published."""
    if dataset_label == SYNTHETIC_LABEL:
        return
    resolved = out_dir.expanduser().resolve()
    protected = [DEMO_DIR.resolve(), POWERBI_DIR.resolve()]
    for folder in protected:
        if resolved == folder or folder in resolved.parents:
            raise PublicationGuardError(
                "Refusing to write a non-synthetic catalog into the demo or Power BI folders. "
                "Choose another --out directory."
            )


def _canonical(value: object) -> object:
    if isinstance(value, float):
        return json.loads(json.dumps(value))
    return value


def _csv_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return format(value, ".12g")
    return str(value)


def write_table(path: Path, table: str, rows: list[dict]) -> None:
    columns = [name for name, _type_name in TABLE_COLUMNS[table]]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row.get(column)) for column in columns})


def summary_payload(analysis: Analysis) -> dict:
    return {
        "dataset_label": analysis.dataset_label,
        "dataset_notice": analysis.dataset_notice,
        "portfolio_extension": "October 2026",
        "kpis": {key: _canonical(value) for key, value in analysis.kpis.items()},
        "definitions": analysis.definitions,
        "reconciliations": analysis.reconciliations,
        "compositions": analysis.compositions,
        "deliveries": analysis.tables["fact_delivery_summary"],
        "issues": analysis.tables["data_quality_issue"],
    }


def _fmt_number(value: object) -> str:
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.3f}".rstrip("0").rstrip(".")
    if isinstance(value, float):
        return f"{value:,.0f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _fmt_kpi(name: str, value: object) -> str:
    if name == "average_catalog_completeness" and isinstance(value, (int, float)):
        return f"{float(value) * 100:.2f}%"
    if name in {"declared_batch_value_rub"} and isinstance(value, (int, float)):
        return f"{float(value):,.2f}"
    if name in {"total_net_weight", "total_gross_weight", "total_quantity"} and isinstance(value, (int, float)):
        return f"{float(value):,.3f}"
    return _fmt_number(value)


def render_preview(analysis: Analysis) -> str:
    payload = summary_payload(analysis)
    kpis = payload["kpis"]
    cards = (
        "shipment_line_count",
        "distinct_shipped_articles",
        "intro_line_count",
        "repeat_line_count",
        "new_article_appearances",
        "repeat_article_appearances",
        "declared_batch_value_rub",
        "total_quantity",
        "total_net_weight",
        "total_gross_weight",
        "part_count",
        "average_catalog_completeness",
        "parts_missing_tech_doc",
        "parts_missing_name_en",
        "parts_filename_without_path",
        "archive_only_parts",
        "price_applicable_lines",
        "price_mismatch_lines",
        "net_weight_applicable_lines",
        "net_weight_mismatch_lines",
        "gross_weight_applicable_lines",
        "gross_weight_mismatch_lines",
        "gross_below_net_lines",
        "quality_issue_rows",
    )
    card_html = []
    for name in cards:
        value = kpis[name]
        card_html.append(
            "<article class=\"card\">"
            f"<p class=\"label\">{html.escape(name.replace('_', ' '))}</p>"
            f"<p class=\"value\" data-kpi=\"{html.escape(name)}\" "
            f"data-value=\"{html.escape(json.dumps(value))}\">{html.escape(_fmt_kpi(name, value))}</p>"
            "</article>"
        )
    delivery_head = (
        "folder_name",
        "line_count",
        "distinct_articles",
        "new_articles",
        "repeat_articles",
        "total_quantity",
        "declared_batch_value_rub",
        "price_mismatch_lines",
        "net_weight_mismatch_lines",
        "gross_below_net_lines",
    )
    delivery_rows = []
    for row in payload["deliveries"]:
        cells = "".join(f"<td>{html.escape(_fmt_kpi(column, row[column]) if column in kpis or column.endswith('_rub') or column.startswith('total_') else _fmt_number(row[column]))}</td>" for column in delivery_head)
        delivery_rows.append(f"<tr>{cells}</tr>")
    composition_rows = []
    for row in payload["compositions"]["country"]:
        composition_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['label']))}</td>"
            f"<td>{row['line_count']}</td>"
            f"<td>{row['distinct_articles']}</td>"
            f"<td>{row['declared_batch_value_rub']:,.2f}</td>"
            "</tr>"
        )
    issue_rows = []
    for row in payload["issues"]:
        issue_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['grain']))}</td>"
            f"<td>{html.escape(str(row['delivery_folder']))}</td>"
            f"<td>{html.escape(str(row['article']))}</td>"
            f"<td>{html.escape(str(row['issue_type']))}</td>"
            "</tr>"
        )
    reconciliation = []
    for item in payload["reconciliations"]:
        mark = "pass" if item["ok"] else "fail"
        reconciliation.append(
            f"<li class=\"{mark}\"><strong>{html.escape(item['name'])}</strong> "
            f"{html.escape(item['detail'])}</li>"
        )
    definitions = []
    for name, text in payload["definitions"].items():
        definitions.append(f"<h3>{html.escape(name.replace('_', ' '))}</h3><p>{html.escape(text)}</p>")
    notice = html.escape(payload["dataset_notice"] or payload["dataset_label"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Customs parts analytics preview</title>
<style>
body {{ margin: 0; font-family: Georgia, "Iowan Old Style", serif; color: #1c2430; background: #f4f1ea; }}
main {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 64px; }}
h1 {{ font-size: 2rem; margin-bottom: 0.2rem; }}
h2 {{ margin-top: 2rem; font-size: 1.3rem; }}
.banner {{ background: #1f4b3a; color: #f4f1ea; padding: 14px 16px; border-radius: 8px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }}
.card {{ background: white; border: 1px solid #d9d2c5; border-radius: 8px; padding: 12px; }}
.label {{ margin: 0; color: #5c6770; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }}
.value {{ margin: 8px 0 0; font-size: 1.45rem; }}
table {{ width: 100%; border-collapse: collapse; background: white; }}
th, td {{ border-bottom: 1px solid #e4ddd2; text-align: left; padding: 8px; font-size: 0.92rem; }}
th {{ background: #ebe4d8; }}
li.pass strong {{ color: #1f4b3a; }}
li.fail strong {{ color: #8c2f2f; }}
</style>
</head>
<body>
<main>
<p class="banner">October 2026 portfolio extension. {notice}</p>
<h1>Customs parts catalog</h1>
<p>Portable preview of the tested metrics. Declared batch value is the sum of line <code>batch_price_rub</code>, not revenue.</p>
<section class="cards">{''.join(card_html)}</section>
<h2>Shipment composition</h2>
<table>
<thead><tr>{''.join(f'<th>{html.escape(column)}</th>' for column in delivery_head)}</tr></thead>
<tbody>{''.join(delivery_rows)}</tbody>
</table>
<h2>Origin of shipment lines</h2>
<table>
<thead><tr><th>country</th><th>lines</th><th>articles</th><th>declared batch value RUB</th></tr></thead>
<tbody>{''.join(composition_rows)}</tbody>
</table>
<h2>Data-quality issues</h2>
<table>
<thead><tr><th>grain</th><th>delivery</th><th>article</th><th>issue</th></tr></thead>
<tbody>{''.join(issue_rows)}</tbody>
</table>
<h2>Reconciliations</h2>
<ul>{''.join(reconciliation)}</ul>
<h2>Definitions</h2>
{''.join(definitions)}
</main>
</body>
</html>
"""


def render_sample_analysis(analysis: Analysis) -> str:
    payload = summary_payload(analysis)
    lines = [
        "# Sample catalog analysis",
        "",
        payload["dataset_notice"] or payload["dataset_label"],
        "",
        "This file is generated from the same metric run as `summary.json` and `preview.html`.",
        "Declared batch value is the sum of `batch_price_rub` on shipment lines. It is not revenue.",
        "",
        "## KPI results",
        "",
        "| KPI | Value |",
        "| --- | ---: |",
    ]
    for name, value in payload["kpis"].items():
        lines.append(f"| {name} | {_fmt_kpi(name, value)} |")
    lines.extend(["", "## Definitions", ""])
    for name, text in payload["definitions"].items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append(text)
        lines.append("")
    lines.append("## Reconciliations")
    lines.append("")
    for item in payload["reconciliations"]:
        status = "PASS" if item["ok"] else "FAIL"
        lines.append(f"- {status} `{item['name']}`: {item['detail']}")
    lines.append("")
    return "\n".join(lines)


def export_report(analysis: Analysis, out_dir: Path) -> Path:
    assert_demo_target_is_synthetic(analysis.dataset_label, out_dir)
    if not analysis.reconciliations_ok:
        failed = [item["name"] for item in analysis.reconciliations if not item["ok"]]
        raise RuntimeError(f"Refusing to export a report that fails reconciliation: {failed}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for table, rows in analysis.tables.items():
        write_table(out_dir / f"{table}.csv", table, rows)
    payload = summary_payload(analysis)
    (out_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    kpi_path = out_dir / "kpi_summary.csv"
    with kpi_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("metric", "value"),
            lineterminator="\n",
        )
        writer.writeheader()
        for name, value in payload["kpis"].items():
            writer.writerow({"metric": name, "value": _csv_cell(value)})
    (out_dir / "sample_analysis.md").write_text(render_sample_analysis(analysis), encoding="utf-8")
    (out_dir / "preview.html").write_text(render_preview(analysis), encoding="utf-8")
    return out_dir


def project_root() -> Path:
    return PROJECT_ROOT
