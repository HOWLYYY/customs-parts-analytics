// Power Query for the synthetic catalog export.
// Set DataRoot to the absolute path of demo/synthetic/report before refresh.
// The PBIP parameter default is "/ABSOLUTE/PATH/TO/demo/synthetic/report".
let
    Root = DataRoot,
    Source = Csv.Document(File.Contents(Root & "/fact_shipment_line.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"line_id", Int64.Type}, {"delivery_id", Int64.Type}, {"article", type text}, {"name_en", type text}, {"quantity", type number}, {"unit_price_rub", type number}, {"batch_price_rub", type number}, {"net_weight_unit", type number}, {"net_weight_total", type number}, {"gross_weight_unit", type number}, {"gross_weight_total", type number}, {"country_origin", type text}, {"tnved", type text}, {"is_intro_line", Int64.Type}, {"price_mismatch", Int64.Type}, {"price_check_applicable", Int64.Type}, {"net_weight_mismatch", Int64.Type}, {"net_weight_check_applicable", Int64.Type}, {"gross_weight_mismatch", Int64.Type}, {"gross_weight_check_applicable", Int64.Type}, {"gross_below_net", Int64.Type}, {"incomplete_price", Int64.Type}, {"incomplete_net_weight", Int64.Type}, {"missing_name_en", Int64.Type}, {"missing_name_ru", Int64.Type}, {"missing_graph_description", Int64.Type}, {"missing_tnved", Int64.Type}, {"missing_quantity", Int64.Type}, {"nonpositive_unit_price", Int64.Type}, {"nonpositive_batch_price", Int64.Type}}, "en-US")
in
    Typed
