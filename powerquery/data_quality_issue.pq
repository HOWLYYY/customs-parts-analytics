// Power Query for the synthetic catalog export.
// Set DataRoot to the absolute path of demo/synthetic/report before refresh.
// The PBIP parameter default is "/ABSOLUTE/PATH/TO/demo/synthetic/report".
let
    Root = DataRoot,
    Source = Csv.Document(File.Contents(Root & "/data_quality_issue.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"issue_id", Int64.Type}, {"grain", type text}, {"entity_id", type text}, {"article", type text}, {"delivery_id", Int64.Type}, {"delivery_folder", type text}, {"issue_type", type text}}, "en-US")
in
    Typed
