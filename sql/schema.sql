PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS deliveries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_name     TEXT NOT NULL UNIQUE,
    excel_filename  TEXT NOT NULL,
    imported_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS parts (
    article                 TEXT PRIMARY KEY,
    sr_no                   INTEGER,
    invoice                 TEXT,
    invoice_date            TEXT,
    tnved                   TEXT,
    graph_description       TEXT,
    name_en                 TEXT,
    questions               TEXT,
    answers                 TEXT,
    name_ru                 TEXT,
    manufacturer            TEXT,
    trademark               TEXT,
    country_origin          TEXT,
    brand                   TEXT,
    model                   TEXT,
    tech_doc_display        TEXT,
    tech_doc_filename       TEXT,
    tech_doc_path           TEXT,
    quantity                REAL,
    unit_code               TEXT,
    unit_name               TEXT,
    unit_price_rub          REAL,
    batch_price_rub         REAL,
    net_weight_unit         REAL,
    net_weight_total        REAL,
    gross_weight_unit       REAL,
    gross_weight_total      REAL,
    delivery_terms          TEXT,
    consignment             TEXT,
    consignment_date        TEXT,
    container               TEXT,
    freight_cost            REAL,
    ds                      TEXT,
    ds_date                 TEXT,
    ds_valid_until          TEXT,
    updated_from_delivery_id INTEGER REFERENCES deliveries (id),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shipment_lines (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    delivery_id         INTEGER NOT NULL REFERENCES deliveries (id) ON DELETE CASCADE,
    article             TEXT NOT NULL REFERENCES parts (article),
    sr_no               INTEGER,
    invoice             TEXT,
    invoice_date        TEXT,
    tnved               TEXT,
    graph_description   TEXT,
    name_en             TEXT,
    questions           TEXT,
    answers             TEXT,
    name_ru             TEXT,
    manufacturer        TEXT,
    trademark           TEXT,
    country_origin      TEXT,
    brand               TEXT,
    model               TEXT,
    tech_doc_display    TEXT,
    tech_doc_link       TEXT,
    quantity            REAL,
    unit_code           TEXT,
    unit_name           TEXT,
    unit_price_rub      REAL,
    batch_price_rub     REAL,
    net_weight_unit     REAL,
    net_weight_total    REAL,
    gross_weight_unit   REAL,
    gross_weight_total  REAL,
    delivery_terms      TEXT,
    consignment         TEXT,
    consignment_date    TEXT,
    container           TEXT,
    freight_cost        REAL,
    ds                  TEXT,
    ds_date             TEXT,
    ds_valid_until      TEXT,
    excel_filename      TEXT,
    excel_row           INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_parts_name_en ON parts (name_en);
CREATE INDEX IF NOT EXISTS idx_parts_name_ru ON parts (name_ru);
CREATE INDEX IF NOT EXISTS idx_shipment_lines_delivery ON shipment_lines (delivery_id);
CREATE INDEX IF NOT EXISTS idx_shipment_lines_article ON shipment_lines (article);

-- Архив: исторические описания без техничек (AllDevs и т.п.)
CREATE TABLE IF NOT EXISTS archive_sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filename        TEXT NOT NULL UNIQUE,
    imported_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS archive_lines (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    archive_source_id   INTEGER NOT NULL REFERENCES archive_sources (id) ON DELETE CASCADE,
    article             TEXT NOT NULL,
    invoice             TEXT,
    sr_no               INTEGER,
    invoice_date        TEXT,
    tnved               TEXT,
    graph_description   TEXT,
    name_en             TEXT,
    name_ru             TEXT,
    questions           TEXT,
    answers             TEXT,
    manufacturer        TEXT,
    trademark           TEXT,
    country_origin      TEXT,
    brand               TEXT,
    model               TEXT,
    quantity            REAL,
    unit_code           TEXT,
    unit_name           TEXT,
    unit_price_rub      REAL,
    batch_price_rub     REAL,
    net_weight_unit     REAL,
    net_weight_total    REAL,
    gross_weight_unit   REAL,
    gross_weight_total  REAL,
    delivery_terms      TEXT,
    consignment         TEXT,
    consignment_date    TEXT,
    container           TEXT,
    freight_cost        REAL,
    ds                  TEXT,
    ds_date             TEXT,
    ds_valid_until      TEXT,
    excel_row           INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_archive_lines_article ON archive_lines (article);
CREATE INDEX IF NOT EXISTS idx_archive_lines_invoice ON archive_lines (invoice);
CREATE INDEX IF NOT EXISTS idx_archive_lines_source ON archive_lines (archive_source_id);

CREATE VIEW IF NOT EXISTS v_part_search AS
SELECT
    p.article,
    p.name_en,
    p.name_ru,
    p.graph_description,
    p.tnved,
    p.manufacturer,
    p.trademark,
    p.country_origin,
    p.brand,
    p.model,
    p.tech_doc_filename,
    p.tech_doc_path,
    d.folder_name AS last_delivery_folder,
    d.imported_at AS last_updated
FROM parts p
LEFT JOIN deliveries d ON d.id = p.updated_from_delivery_id;

CREATE VIEW IF NOT EXISTS v_archive_part_search AS
SELECT
    p.article,
    p.name_en,
    p.name_ru,
    p.graph_description,
    p.tnved,
    p.manufacturer,
    p.trademark,
    p.country_origin,
    p.brand,
    p.model,
    p.tech_doc_filename,
    p.tech_doc_path,
    al.invoice AS archive_invoice,
    s.filename AS archive_file,
    s.imported_at AS archive_imported_at
FROM parts p
JOIN archive_lines al ON al.article = p.article
JOIN archive_sources s ON s.id = al.archive_source_id
WHERE p.updated_from_delivery_id IS NULL
   OR p.tech_doc_path IS NULL
   OR p.tech_doc_path = '';
