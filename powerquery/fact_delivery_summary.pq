// Power Query for the synthetic catalog export.
// Set DataRoot to the absolute path of demo/synthetic/report before refresh.
// The PBIP parameter default is "/ABSOLUTE/PATH/TO/demo/synthetic/report".
let
    Root = DataRoot,
    Source = Csv.Document(File.Contents(Root & "/fact_delivery_summary.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"delivery_id", Int64.Type}, {"folder_name", type text}, {"imported_at", type text}, {"sort_order", Int64.Type}, {"line_count", Int64.Type}, {"distinct_articles", Int64.Type}, {"new_articles", Int64.Type}, {"repeat_articles", Int64.Type}, {"intro_lines", Int64.Type}, {"repeat_lines", Int64.Type}, {"total_quantity", type number}, {"declared_batch_value_rub", type number}, {"total_net_weight", type number}, {"total_gross_weight", type number}, {"price_mismatch_lines", Int64.Type}, {"net_weight_mismatch_lines", Int64.Type}, {"gross_weight_mismatch_lines", Int64.Type}, {"gross_below_net_lines", Int64.Type}, {"lines_missing_name_en", Int64.Type}, {"lines_missing_graph_description", Int64.Type}, {"lines_missing_tnved", Int64.Type}, {"distinct_tnved", Int64.Type}, {"distinct_countries", Int64.Type}}, "en-US")
in
    Typed
