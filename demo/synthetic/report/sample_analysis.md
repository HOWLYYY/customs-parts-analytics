# Sample catalog analysis

Synthetic data for an October 2026 portfolio extension. Not production customs history.

This file is generated from the same metric run as `summary.json` and `preview.html`.
Declared batch value is the sum of `batch_price_rub` on shipment lines. It is not revenue.

## KPI results

| KPI | Value |
| --- | ---: |
| shipment_line_count | 10 |
| distinct_shipped_articles | 5 |
| intro_line_count | 5 |
| repeat_line_count | 5 |
| declared_batch_value_rub | 2,330.00 |
| total_quantity | 41.000 |
| total_net_weight | 9.500 |
| total_gross_weight | 14.750 |
| price_applicable_lines | 8 |
| price_mismatch_lines | 1 |
| net_weight_applicable_lines | 8 |
| net_weight_mismatch_lines | 1 |
| gross_weight_applicable_lines | 7 |
| gross_weight_mismatch_lines | 1 |
| gross_below_net_lines | 1 |
| incomplete_price_lines | 2 |
| incomplete_net_weight_lines | 1 |
| part_count | 6 |
| average_catalog_completeness | 83.33% |
| filled_key_fields | 35 |
| key_field_slots | 42 |
| parts_missing_tech_doc | 3 |
| parts_missing_name_en | 2 |
| parts_missing_name_ru | 0 |
| parts_missing_graph_description | 1 |
| parts_missing_tnved | 1 |
| parts_filename_without_path | 1 |
| archive_only_parts | 1 |
| parts_with_shipment | 5 |
| new_article_appearances | 5 |
| repeat_article_appearances | 3 |
| articles_in_multiple_deliveries | 2 |
| archive_line_count | 2 |
| archive_distinct_articles | 2 |
| archive_articles_also_shipped | 1 |
| quality_issue_rows | 22 |

## Definitions

### catalog_completeness

A key field is filled when it is not null and, for text, not blank. The seven key fields are name_en, name_ru, graph_description, tnved, manufacturer, country_origin, and tech_doc_path. Average completeness is filled key fields divided by parts times 7.

### repeat_vs_new

Deliveries are ordered by imported_at, then id. An article's introduction line is its earliest shipment line in that order. A delivery-article pair is new when that delivery is the article's first shipment; otherwise it is a repeat appearance. The sum of new appearances equals the number of distinct shipped articles.

### declared_batch_value

Declared batch value is the sum of shipment_lines.batch_price_rub. Blank amounts are left out of the sum. This is not revenue, margin, or turnover.

### price_consistency

A price check applies when quantity, unit_price_rub, and batch_price_rub are all present. It mismatches when the absolute gap between quantity * unit_price_rub and batch_price_rub is greater than max(0.05, 0.005 * abs(batch_price_rub)).

### weight_consistency

A weight check applies only when quantity, the unit weight, and the total weight are all present. Absence of gross weight is not itself an issue. The mismatch tolerance is max(0.001, 0.005 * abs(total)). Gross below net applies when both totals are present and gross_weight_total + 0.001 < net_weight_total.

### missing_docs

A part is missing its tech doc when tech_doc_path is blank. Filename without path means tech_doc_filename is filled and tech_doc_path is not. Archive-only parts are articles present in archive_lines and absent from shipment_lines.

## Reconciliations

- PASS `line_count_matches_summary`: sum of delivery line counts equals shipment lines
- PASS `new_appearances_match_distinct_articles`: each shipped article is new in exactly one delivery
- PASS `intro_lines_match_distinct_articles`: each shipped article has one introduction line
- PASS `intro_plus_repeat_lines`: introduction lines and later lines cover every shipment line
- PASS `delivery_new_plus_repeat_articles`: new and repeat article counts partition each delivery
- PASS `delivery_intro_plus_repeat_lines`: introduction and later lines partition each delivery
- PASS `summary_batch_matches_lines`: delivery declared values add up to the catalog total
- PASS `summary_quantity_matches_lines`: delivery quantities add up to the catalog total
- PASS `summary_new_matches_kpi`: delivery new-article counts add up
- PASS `summary_repeat_matches_kpi`: delivery repeat-article counts add up
- PASS `appearance_flags_cover_pairs`: every delivery-article pair is either new or repeat
- PASS `completeness_ratio`: average completeness equals filled fields over slots
- PASS `shipped_part_flag`: has_shipment counts parts that appear on a shipment line
- PASS `price_mismatch_issues`: price mismatch issues match the line flag
- PASS `net_mismatch_issues`: net weight mismatch issues match the line flag
- PASS `gross_mismatch_issues`: gross weight mismatch issues match the line flag
- PASS `composition_lines`: country and TNVED compositions cover every shipment line
- PASS `composition_value`: country declared values add up to the catalog total
