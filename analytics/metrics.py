"""Catalog metrics computed from in-memory rows.

Inputs are plain dictionaries loaded from SQLite. The functions do not
open a database and do not read article text from anywhere except the
rows the caller supplies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from analytics.contract import (
    DEFINITIONS,
    KEY_FIELDS,
    PRICE_ABS_TOLERANCE,
    PRICE_REL_TOLERANCE,
    TABLE_COLUMNS,
    WEIGHT_ABS_TOLERANCE,
    WEIGHT_REL_TOLERANCE,
)


def filled(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def clean_text(value: object) -> str | None:
    if not filled(value):
        return None
    return str(value).strip()


def as_number(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    return float(text)


def flag(condition: bool) -> int:
    return 1 if condition else 0


def values_mismatch(
    quantity: float | None,
    unit_value: float | None,
    total_value: float | None,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> tuple[int, int]:
    """Return (mismatch_flag, applicable_flag).

    A gap equal to the tolerance is not a mismatch.
    """
    if quantity is None or unit_value is None or total_value is None:
        return 0, 0
    expected = quantity * unit_value
    tolerance = max(absolute_tolerance, abs(total_value) * relative_tolerance)
    return flag(abs(expected - total_value) > tolerance), 1


def _delivery_order(deliveries: list[dict]) -> list[dict]:
    return sorted(deliveries, key=lambda row: (str(row["imported_at"]), int(row["id"])))


def _sum_numbers(values: list[float | None]) -> float:
    total = 0.0
    for value in values:
        if value is not None:
            total += value
    return total


@dataclass
class Analysis:
    dataset_label: str
    dataset_notice: str
    kpis: dict[str, float | int]
    definitions: dict[str, str]
    tables: dict[str, list[dict]]
    reconciliations: list[dict]
    compositions: dict[str, list[dict]] = field(default_factory=dict)

    @property
    def reconciliations_ok(self) -> bool:
        return all(item["ok"] for item in self.reconciliations)


def analyze(
    deliveries: list[dict],
    parts: list[dict],
    shipment_lines: list[dict],
    archive_sources: list[dict],
    archive_lines: list[dict],
    dataset_label: str,
    dataset_notice: str = "",
) -> Analysis:
    ordered = _delivery_order(deliveries)
    sort_order = {int(row["id"]): index for index, row in enumerate(ordered, start=1)}
    delivery_by_id = {int(row["id"]): row for row in deliveries}
    if len(delivery_by_id) != len(deliveries):
        raise ValueError("delivery id values must be unique")

    shipped_articles = {str(row["article"]) for row in shipment_lines}
    archive_articles = {str(row["article"]) for row in archive_lines}
    source_name = {int(row["id"]): str(row["filename"]) for row in archive_sources}

    ranked_lines = sorted(
        shipment_lines,
        key=lambda row: (sort_order[int(row["delivery_id"])], int(row["id"])),
    )
    first_line_id: dict[str, int] = {}
    first_delivery_id: dict[str, int] = {}
    for row in ranked_lines:
        article = str(row["article"])
        if article not in first_line_id:
            first_line_id[article] = int(row["id"])
            first_delivery_id[article] = int(row["delivery_id"])

    dim_delivery = [
        {
            "delivery_id": int(row["id"]),
            "folder_name": str(row["folder_name"]),
            "imported_at": str(row["imported_at"]),
            "sort_order": sort_order[int(row["id"])],
        }
        for row in ordered
    ]

    dim_part: list[dict] = []
    for row in sorted(parts, key=lambda item: str(item["article"])):
        article = str(row["article"])
        presence = {name: flag(filled(row.get(name))) for name in KEY_FIELDS}
        filled_count = sum(presence.values())
        dim_part.append(
            {
                "article": article,
                "name_en": clean_text(row.get("name_en")) or "",
                "name_ru": clean_text(row.get("name_ru")) or "",
                "graph_description": clean_text(row.get("graph_description")) or "",
                "tnved": clean_text(row.get("tnved")) or "",
                "manufacturer": clean_text(row.get("manufacturer")) or "",
                "country_origin": clean_text(row.get("country_origin")) or "",
                "tech_doc_present": presence["tech_doc_path"],
                "filename_without_path": flag(
                    filled(row.get("tech_doc_filename")) and not filled(row.get("tech_doc_path"))
                ),
                "filled_field_count": filled_count,
                "key_field_count": len(KEY_FIELDS),
                "completeness_ratio": filled_count / len(KEY_FIELDS),
                "has_name_en": presence["name_en"],
                "has_name_ru": presence["name_ru"],
                "has_graph_description": presence["graph_description"],
                "has_tnved": presence["tnved"],
                "has_manufacturer": presence["manufacturer"],
                "has_country_origin": presence["country_origin"],
                "has_shipment": flag(article in shipped_articles),
                "is_archive_only": flag(
                    article in archive_articles and article not in shipped_articles
                ),
            }
        )
    part_by_article = {row["article"]: row for row in dim_part}

    fact_lines: list[dict] = []
    for row in ranked_lines:
        article = str(row["article"])
        quantity = as_number(row.get("quantity"))
        unit_price = as_number(row.get("unit_price_rub"))
        batch_price = as_number(row.get("batch_price_rub"))
        net_unit = as_number(row.get("net_weight_unit"))
        net_total = as_number(row.get("net_weight_total"))
        gross_unit = as_number(row.get("gross_weight_unit"))
        gross_total = as_number(row.get("gross_weight_total"))
        price_mismatch, price_applicable = values_mismatch(
            quantity, unit_price, batch_price, PRICE_ABS_TOLERANCE, PRICE_REL_TOLERANCE
        )
        net_mismatch, net_applicable = values_mismatch(
            quantity, net_unit, net_total, WEIGHT_ABS_TOLERANCE, WEIGHT_REL_TOLERANCE
        )
        gross_mismatch, gross_applicable = values_mismatch(
            quantity, gross_unit, gross_total, WEIGHT_ABS_TOLERANCE, WEIGHT_REL_TOLERANCE
        )
        gross_below = flag(
            net_total is not None
            and gross_total is not None
            and gross_total + WEIGHT_ABS_TOLERANCE < net_total
        )
        fact_lines.append(
            {
                "line_id": int(row["id"]),
                "delivery_id": int(row["delivery_id"]),
                "article": article,
                "name_en": clean_text(row.get("name_en")) or "",
                "quantity": quantity,
                "unit_price_rub": unit_price,
                "batch_price_rub": batch_price,
                "net_weight_unit": net_unit,
                "net_weight_total": net_total,
                "gross_weight_unit": gross_unit,
                "gross_weight_total": gross_total,
                "country_origin": clean_text(row.get("country_origin")) or "",
                "tnved": clean_text(row.get("tnved")) or "",
                "is_intro_line": flag(int(row["id"]) == first_line_id[article]),
                "price_mismatch": price_mismatch,
                "price_check_applicable": price_applicable,
                "net_weight_mismatch": net_mismatch,
                "net_weight_check_applicable": net_applicable,
                "gross_weight_mismatch": gross_mismatch,
                "gross_weight_check_applicable": gross_applicable,
                "gross_below_net": gross_below,
                "incomplete_price": flag(
                    not (quantity is not None and unit_price is not None and batch_price is not None)
                ),
                "incomplete_net_weight": flag(
                    (net_unit is not None or net_total is not None)
                    and not (quantity is not None and net_unit is not None and net_total is not None)
                ),
                "missing_name_en": flag(not filled(row.get("name_en"))),
                "missing_name_ru": flag(not filled(row.get("name_ru"))),
                "missing_graph_description": flag(not filled(row.get("graph_description"))),
                "missing_tnved": flag(not filled(row.get("tnved"))),
                "missing_quantity": flag(quantity is None),
                "nonpositive_unit_price": flag(unit_price is not None and unit_price <= 0),
                "nonpositive_batch_price": flag(batch_price is not None and batch_price <= 0),
            }
        )

    lines_by_delivery: dict[int, list[dict]] = {row["delivery_id"]: [] for row in dim_delivery}
    for row in fact_lines:
        lines_by_delivery[row["delivery_id"]].append(row)

    summary_rows: list[dict] = []
    delivery_articles: list[dict] = []
    for delivery in dim_delivery:
        delivery_id = delivery["delivery_id"]
        rows = lines_by_delivery.get(delivery_id, [])
        articles = sorted({row["article"] for row in rows})
        new_articles = [
            article for article in articles if first_delivery_id[article] == delivery_id
        ]
        for article in articles:
            is_new = flag(first_delivery_id[article] == delivery_id)
            delivery_articles.append(
                {
                    "delivery_id": delivery_id,
                    "article": article,
                    "is_new_article": is_new,
                    "is_repeat_article": flag(not is_new),
                }
            )
        summary_rows.append(
            {
                "delivery_id": delivery_id,
                "folder_name": delivery["folder_name"],
                "imported_at": delivery["imported_at"],
                "sort_order": delivery["sort_order"],
                "line_count": len(rows),
                "distinct_articles": len(articles),
                "new_articles": len(new_articles),
                "repeat_articles": len(articles) - len(new_articles),
                "intro_lines": sum(row["is_intro_line"] for row in rows),
                "repeat_lines": len(rows) - sum(row["is_intro_line"] for row in rows),
                "total_quantity": _sum_numbers([row["quantity"] for row in rows]),
                "declared_batch_value_rub": _sum_numbers([row["batch_price_rub"] for row in rows]),
                "total_net_weight": _sum_numbers([row["net_weight_total"] for row in rows]),
                "total_gross_weight": _sum_numbers([row["gross_weight_total"] for row in rows]),
                "price_mismatch_lines": sum(row["price_mismatch"] for row in rows),
                "net_weight_mismatch_lines": sum(row["net_weight_mismatch"] for row in rows),
                "gross_weight_mismatch_lines": sum(row["gross_weight_mismatch"] for row in rows),
                "gross_below_net_lines": sum(row["gross_below_net"] for row in rows),
                "lines_missing_name_en": sum(row["missing_name_en"] for row in rows),
                "lines_missing_graph_description": sum(row["missing_graph_description"] for row in rows),
                "lines_missing_tnved": sum(row["missing_tnved"] for row in rows),
                "distinct_tnved": len({row["tnved"] for row in rows if row["tnved"]}),
                "distinct_countries": len({row["country_origin"] for row in rows if row["country_origin"]}),
            }
        )

    archive_rows = []
    for row in sorted(archive_lines, key=lambda item: int(item["id"])):
        article = str(row["article"])
        archive_rows.append(
            {
                "archive_line_id": int(row["id"]),
                "article": article,
                "archive_source": source_name.get(int(row["archive_source_id"]), ""),
                "in_shipment": flag(article in shipped_articles),
            }
        )

    issues = _issues(
        fact_lines=fact_lines,
        dim_part=dim_part,
        folder_by_id={row["delivery_id"]: row["folder_name"] for row in dim_delivery},
    )

    country_rows = _composition(fact_lines, "country_origin")
    tnved_rows = _composition(fact_lines, "tnved")

    delivery_counts: dict[str, set[int]] = {}
    for row in delivery_articles:
        delivery_counts.setdefault(row["article"], set()).add(row["delivery_id"])
    multi_delivery_articles = sum(1 for ids in delivery_counts.values() if len(ids) > 1)

    filled_fields = sum(row["filled_field_count"] for row in dim_part)
    key_slots = sum(row["key_field_count"] for row in dim_part)
    kpis: dict[str, float | int] = {
        "shipment_line_count": len(fact_lines),
        "distinct_shipped_articles": len(shipped_articles),
        "intro_line_count": sum(row["is_intro_line"] for row in fact_lines),
        "repeat_line_count": len(fact_lines) - sum(row["is_intro_line"] for row in fact_lines),
        "declared_batch_value_rub": _sum_numbers([row["batch_price_rub"] for row in fact_lines]),
        "total_quantity": _sum_numbers([row["quantity"] for row in fact_lines]),
        "total_net_weight": _sum_numbers([row["net_weight_total"] for row in fact_lines]),
        "total_gross_weight": _sum_numbers([row["gross_weight_total"] for row in fact_lines]),
        "price_applicable_lines": sum(row["price_check_applicable"] for row in fact_lines),
        "price_mismatch_lines": sum(row["price_mismatch"] for row in fact_lines),
        "net_weight_applicable_lines": sum(row["net_weight_check_applicable"] for row in fact_lines),
        "net_weight_mismatch_lines": sum(row["net_weight_mismatch"] for row in fact_lines),
        "gross_weight_applicable_lines": sum(row["gross_weight_check_applicable"] for row in fact_lines),
        "gross_weight_mismatch_lines": sum(row["gross_weight_mismatch"] for row in fact_lines),
        "gross_below_net_lines": sum(row["gross_below_net"] for row in fact_lines),
        "incomplete_price_lines": sum(row["incomplete_price"] for row in fact_lines),
        "incomplete_net_weight_lines": sum(row["incomplete_net_weight"] for row in fact_lines),
        "part_count": len(dim_part),
        "average_catalog_completeness": (filled_fields / key_slots) if key_slots else 0.0,
        "filled_key_fields": filled_fields,
        "key_field_slots": key_slots,
        "parts_missing_tech_doc": sum(1 for row in dim_part if row["tech_doc_present"] == 0),
        "parts_missing_name_en": sum(1 for row in dim_part if row["has_name_en"] == 0),
        "parts_missing_name_ru": sum(1 for row in dim_part if row["has_name_ru"] == 0),
        "parts_missing_graph_description": sum(
            1 for row in dim_part if row["has_graph_description"] == 0
        ),
        "parts_missing_tnved": sum(1 for row in dim_part if row["has_tnved"] == 0),
        "parts_filename_without_path": sum(row["filename_without_path"] for row in dim_part),
        "archive_only_parts": sum(row["is_archive_only"] for row in dim_part),
        "parts_with_shipment": sum(row["has_shipment"] for row in dim_part),
        "new_article_appearances": sum(row["is_new_article"] for row in delivery_articles),
        "repeat_article_appearances": sum(row["is_repeat_article"] for row in delivery_articles),
        "articles_in_multiple_deliveries": multi_delivery_articles,
        "archive_line_count": len(archive_rows),
        "archive_distinct_articles": len(archive_articles),
        "archive_articles_also_shipped": len(archive_articles & shipped_articles),
        "quality_issue_rows": len(issues),
    }

    tables = {
        "dim_delivery": dim_delivery,
        "dim_part": dim_part,
        "fact_shipment_line": fact_lines,
        "fact_delivery_summary": summary_rows,
        "fact_delivery_article": delivery_articles,
        "fact_archive_line": archive_rows,
        "data_quality_issue": issues,
    }
    for name, columns in TABLE_COLUMNS.items():
        expected = [column for column, _type_name in columns]
        for row in tables[name]:
            missing = [column for column in expected if column not in row]
            extra = [column for column in row if column not in expected]
            if missing or extra:
                raise ValueError(f"{name} column mismatch missing={missing} extra={extra}")

    analysis = Analysis(
        dataset_label=dataset_label,
        dataset_notice=dataset_notice,
        kpis=kpis,
        definitions=dict(DEFINITIONS),
        tables=tables,
        reconciliations=[],
        compositions={"country": country_rows, "tnved": tnved_rows},
    )
    analysis.reconciliations = _reconciliations(analysis, part_by_article)
    return analysis


def _issues(
    fact_lines: list[dict],
    dim_part: list[dict],
    folder_by_id: dict[int, str],
) -> list[dict]:
    line_types = (
        "price_mismatch",
        "net_weight_mismatch",
        "gross_weight_mismatch",
        "gross_below_net",
        "incomplete_price",
        "incomplete_net_weight",
        "missing_name_en",
        "missing_name_ru",
        "missing_graph_description",
        "missing_tnved",
        "missing_quantity",
        "nonpositive_unit_price",
        "nonpositive_batch_price",
    )
    raw: list[dict] = []
    for row in fact_lines:
        for issue_type in line_types:
            if row[issue_type]:
                raw.append(
                    {
                        "grain": "line",
                        "entity_id": str(row["line_id"]),
                        "article": row["article"],
                        "delivery_id": row["delivery_id"],
                        "delivery_folder": folder_by_id.get(row["delivery_id"], ""),
                        "issue_type": issue_type,
                    }
                )
    part_checks = (
        ("missing_name_en", lambda row: row["has_name_en"] == 0),
        ("missing_name_ru", lambda row: row["has_name_ru"] == 0),
        ("missing_graph_description", lambda row: row["has_graph_description"] == 0),
        ("missing_tnved", lambda row: row["has_tnved"] == 0),
        ("missing_tech_doc", lambda row: row["tech_doc_present"] == 0),
        ("filename_without_path", lambda row: row["filename_without_path"] == 1),
    )
    for row in dim_part:
        for issue_type, predicate in part_checks:
            if predicate(row):
                raw.append(
                    {
                        "grain": "part",
                        "entity_id": row["article"],
                        "article": row["article"],
                        "delivery_id": None,
                        "delivery_folder": "",
                        "issue_type": issue_type,
                    }
                )
    raw.sort(
        key=lambda item: (
            item["grain"],
            item["delivery_folder"],
            item["article"],
            item["issue_type"],
            item["entity_id"],
        )
    )
    for index, item in enumerate(raw, start=1):
        item["issue_id"] = index
    return raw


def _composition(fact_lines: list[dict], column: str) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in fact_lines:
        label = row[column] or "(missing)"
        grouped.setdefault(label, []).append(row)
    result = []
    for label, rows in grouped.items():
        result.append(
            {
                "label": label,
                "line_count": len(rows),
                "distinct_articles": len({row["article"] for row in rows}),
                "declared_batch_value_rub": _sum_numbers([row["batch_price_rub"] for row in rows]),
            }
        )
    result.sort(key=lambda item: (-item["line_count"], item["label"]))
    return result


def _close(left: float, right: float, places: int = 9) -> bool:
    return abs(left - right) <= 10 ** (-places)


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def _reconciliations(analysis: Analysis, part_by_article: dict[str, dict]) -> list[dict]:
    kpis = analysis.kpis
    lines = analysis.tables["fact_shipment_line"]
    summary = analysis.tables["fact_delivery_summary"]
    articles = analysis.tables["fact_delivery_article"]
    issues = analysis.tables["data_quality_issue"]
    checks = [
        _check(
            "line_count_matches_summary",
            sum(row["line_count"] for row in summary) == kpis["shipment_line_count"],
            "sum of delivery line counts equals shipment lines",
        ),
        _check(
            "new_appearances_match_distinct_articles",
            kpis["new_article_appearances"] == kpis["distinct_shipped_articles"],
            "each shipped article is new in exactly one delivery",
        ),
        _check(
            "intro_lines_match_distinct_articles",
            kpis["intro_line_count"] == kpis["distinct_shipped_articles"],
            "each shipped article has one introduction line",
        ),
        _check(
            "intro_plus_repeat_lines",
            kpis["intro_line_count"] + kpis["repeat_line_count"] == kpis["shipment_line_count"],
            "introduction lines and later lines cover every shipment line",
        ),
        _check(
            "delivery_new_plus_repeat_articles",
            all(
                row["new_articles"] + row["repeat_articles"] == row["distinct_articles"]
                for row in summary
            ),
            "new and repeat article counts partition each delivery",
        ),
        _check(
            "delivery_intro_plus_repeat_lines",
            all(row["intro_lines"] + row["repeat_lines"] == row["line_count"] for row in summary),
            "introduction and later lines partition each delivery",
        ),
        _check(
            "summary_batch_matches_lines",
            _close(
                sum(row["declared_batch_value_rub"] for row in summary),
                float(kpis["declared_batch_value_rub"]),
            ),
            "delivery declared values add up to the catalog total",
        ),
        _check(
            "summary_quantity_matches_lines",
            _close(sum(row["total_quantity"] for row in summary), float(kpis["total_quantity"])),
            "delivery quantities add up to the catalog total",
        ),
        _check(
            "summary_new_matches_kpi",
            sum(row["new_articles"] for row in summary) == kpis["new_article_appearances"],
            "delivery new-article counts add up",
        ),
        _check(
            "summary_repeat_matches_kpi",
            sum(row["repeat_articles"] for row in summary) == kpis["repeat_article_appearances"],
            "delivery repeat-article counts add up",
        ),
        _check(
            "appearance_flags_cover_pairs",
            all(row["is_new_article"] + row["is_repeat_article"] == 1 for row in articles)
            and len(articles) == kpis["new_article_appearances"] + kpis["repeat_article_appearances"],
            "every delivery-article pair is either new or repeat",
        ),
        _check(
            "completeness_ratio",
            kpis["key_field_slots"] == 0
            or _close(
                float(kpis["average_catalog_completeness"]),
                kpis["filled_key_fields"] / kpis["key_field_slots"],
            ),
            "average completeness equals filled fields over slots",
        ),
        _check(
            "shipped_part_flag",
            sum(row["has_shipment"] for row in analysis.tables["dim_part"])
            == len({row["article"] for row in lines if row["article"] in part_by_article}),
            "has_shipment counts parts that appear on a shipment line",
        ),
        _check(
            "price_mismatch_issues",
            sum(1 for row in issues if row["issue_type"] == "price_mismatch" and row["grain"] == "line")
            == kpis["price_mismatch_lines"],
            "price mismatch issues match the line flag",
        ),
        _check(
            "net_mismatch_issues",
            sum(1 for row in issues if row["issue_type"] == "net_weight_mismatch")
            == kpis["net_weight_mismatch_lines"],
            "net weight mismatch issues match the line flag",
        ),
        _check(
            "gross_mismatch_issues",
            sum(1 for row in issues if row["issue_type"] == "gross_weight_mismatch")
            == kpis["gross_weight_mismatch_lines"],
            "gross weight mismatch issues match the line flag",
        ),
        _check(
            "composition_lines",
            sum(row["line_count"] for row in analysis.compositions["country"])
            == kpis["shipment_line_count"]
            and sum(row["line_count"] for row in analysis.compositions["tnved"])
            == kpis["shipment_line_count"],
            "country and TNVED compositions cover every shipment line",
        ),
        _check(
            "composition_value",
            _close(
                sum(row["declared_batch_value_rub"] for row in analysis.compositions["country"]),
                float(kpis["declared_batch_value_rub"]),
            ),
            "country declared values add up to the catalog total",
        ),
    ]
    return checks
