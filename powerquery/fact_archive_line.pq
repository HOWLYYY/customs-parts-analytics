// Power Query for the synthetic catalog export.
// Set DataRoot to the absolute path of demo/synthetic/report before refresh.
// The PBIP parameter default is "/ABSOLUTE/PATH/TO/demo/synthetic/report".
let
    Root = DataRoot,
    Source = Csv.Document(File.Contents(Root & "/fact_archive_line.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"archive_line_id", Int64.Type}, {"article", type text}, {"archive_source", type text}, {"in_shipment", Int64.Type}}, "en-US")
in
    Typed
