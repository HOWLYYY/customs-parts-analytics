// Power Query for the synthetic catalog export.
// Set DataRoot to the absolute path of demo/synthetic/report before refresh.
// The PBIP parameter default is "/ABSOLUTE/PATH/TO/demo/synthetic/report".
let
    Root = DataRoot,
    Source = Csv.Document(File.Contents(Root & "/dim_part.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"article", type text}, {"name_en", type text}, {"name_ru", type text}, {"graph_description", type text}, {"tnved", type text}, {"manufacturer", type text}, {"country_origin", type text}, {"tech_doc_present", Int64.Type}, {"filename_without_path", Int64.Type}, {"filled_field_count", Int64.Type}, {"key_field_count", Int64.Type}, {"completeness_ratio", type number}, {"has_name_en", Int64.Type}, {"has_name_ru", Int64.Type}, {"has_graph_description", Int64.Type}, {"has_tnved", Int64.Type}, {"has_manufacturer", Int64.Type}, {"has_country_origin", Int64.Type}, {"has_shipment", Int64.Type}, {"is_archive_only", Int64.Type}}, "en-US")
in
    Typed
