"""
JTech Tally Bridge - SQLite database

Defines connection helpers, the full schema for every entity
the bridge stores, and a lightweight migration runner that
applies ALTER TABLE statements on top of older databases.

Schema versions:
  v1: initial Phase 1/2/3/4 schema (companies, masters, vouchers,
      report_snapshots)
  v2: added TALLY_PROFILE setting support (no schema change)
  v3: added sync_runs table, last_sync_at columns on companies,
      GST fields on vouchers, hsn_code/rate on inventory allocations
"""

import sqlite3
from config.settings import DATABASE_PATH

SCHEMA_VERSION = 3


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


SCHEMA_SQL = """
-- ---------- Phase 1 ----------
CREATE TABLE IF NOT EXISTS companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL COLLATE NOCASE UNIQUE,
    reserved_name   TEXT,
    starting_from   TEXT,
    books_from      TEXT,
    first_seen_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_master_sync_at TEXT,
    last_voucher_sync_at TEXT
);

CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

-- ---------- Phase 2 - masters ----------
CREATE TABLE IF NOT EXISTS groups (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id        INTEGER NOT NULL,
    name              TEXT NOT NULL,
    reserved_name     TEXT,
    parent            TEXT,
    primary_group     TEXT,
    is_revenue        TEXT,
    is_deemed_positive TEXT,
    is_reserved       TEXT,
    first_seen_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS ledgers (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id               INTEGER NOT NULL,
    name                     TEXT NOT NULL,
    reserved_name            TEXT,
    parent_group             TEXT,
    opening_balance_raw      TEXT,
    opening_balance_amount   REAL,
    closing_balance_raw      TEXT,
    closing_balance_amount   REAL,
    first_seen_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS voucher_types (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id        INTEGER NOT NULL,
    name              TEXT NOT NULL,
    reserved_name     TEXT,
    parent            TEXT,
    numbering_method TEXT,
    is_deemed_positive TEXT,
    is_reserved       TEXT,
    is_active         TEXT,
    use_for_pos       TEXT,
    first_seen_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS stock_groups (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    INTEGER NOT NULL,
    name          TEXT NOT NULL,
    reserved_name TEXT,
    parent        TEXT,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS stock_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    name            TEXT NOT NULL,
    reserved_name   TEXT,
    parent          TEXT,
    uom             TEXT,
    opening_qty_raw TEXT,
    opening_qty     REAL,
    opening_rate    REAL,
    opening_value   REAL,
    closing_qty     REAL,
    closing_value   REAL,
    is_batch_wise   TEXT,
    godown          TEXT,
    hsn_code        TEXT,
    gst_rate        REAL,
    first_seen_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS units (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    INTEGER NOT NULL,
    name          TEXT NOT NULL,
    reserved_name TEXT,
    decimal_places INTEGER,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS cost_categories (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    INTEGER NOT NULL,
    name          TEXT NOT NULL,
    reserved_name TEXT,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS cost_centres (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    INTEGER NOT NULL,
    name          TEXT NOT NULL,
    reserved_name TEXT,
    parent        TEXT,
    category      TEXT,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS godowns (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    INTEGER NOT NULL,
    name          TEXT NOT NULL,
    reserved_name TEXT,
    parent        TEXT,
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- ---------- Phase 3 - transactions ----------
CREATE TABLE IF NOT EXISTS vouchers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    remote_id       TEXT,
    voucher_type    TEXT NOT NULL,
    voucher_number  TEXT,
    voucher_date    TEXT,
    party           TEXT,
    party_gstin     TEXT,
    place_of_supply TEXT,
    narration       TEXT,
    amount          REAL,
    is_deemed_positive TEXT,
    is_gst_applicable TEXT,
    gst_registration_type TEXT,
    guid            TEXT,
    source_xml      TEXT,
    imported_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, voucher_type, voucher_number),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS voucher_ledger_allocations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id      INTEGER NOT NULL,
    ledger          TEXT NOT NULL,
    group_name      TEXT,
    is_deemed_positive TEXT,
    amount          REAL NOT NULL,
    FOREIGN KEY(voucher_id) REFERENCES vouchers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS voucher_inventory_allocations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id      INTEGER NOT NULL,
    stock_item      TEXT NOT NULL,
    godown          TEXT,
    qty             REAL,
    rate            REAL,
    amount          REAL,
    is_batch_wise   TEXT,
    batch_name      TEXT,
    hsn_code        TEXT,
    gst_rate        REAL,
    cgst_amount     REAL,
    sgst_amount     REAL,
    igst_amount     REAL,
    cess_amount     REAL,
    FOREIGN KEY(voucher_id) REFERENCES vouchers(id) ON DELETE CASCADE
);

-- ---------- Phase 4 - report snapshots ----------
CREATE TABLE IF NOT EXISTS report_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL,
    report_type TEXT NOT NULL,
    params_json TEXT,
    result_json TEXT NOT NULL,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

-- ---------- Tier 1.1 - sync runs audit log ----------
CREATE TABLE IF NOT EXISTS sync_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL,
    sync_type       TEXT NOT NULL,        -- 'masters' / 'vouchers' / 'reconcile'
    reader_name     TEXT,                 -- 'ledger_reader', 'voucher_reader', etc.
    started_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    TEXT,
    records_read    INTEGER DEFAULT 0,
    records_persisted INTEGER DEFAULT 0,
    errors_count    INTEGER DEFAULT 0,
    error_details_json TEXT,
    triggered_by    TEXT DEFAULT 'cli',   -- 'cli' / 'scheduler' / 'web'
    status          TEXT DEFAULT 'running', -- 'running' / 'completed' / 'failed'
    duration_seconds REAL,
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE INDEX IF NOT EXISTS idx_sync_runs_company_started
    ON sync_runs(company_id, started_at);
CREATE INDEX IF NOT EXISTS idx_sync_runs_status
    ON sync_runs(status);

CREATE INDEX IF NOT EXISTS idx_ledgers_company
    ON ledgers(company_id);
CREATE INDEX IF NOT EXISTS idx_vouchers_company_date
    ON vouchers(company_id, voucher_date);
CREATE INDEX IF NOT EXISTS idx_vouchers_company_type
    ON vouchers(company_id, voucher_type);
CREATE INDEX IF NOT EXISTS idx_vla_voucher
    ON voucher_ledger_allocations(voucher_id);
CREATE INDEX IF NOT EXISTS idx_via_voucher
    ON voucher_inventory_allocations(voucher_id);
CREATE INDEX IF NOT EXISTS idx_vla_ledger
    ON voucher_ledger_allocations(ledger);
"""


# --- Migration plan ---
# Each migration runs as a series of idempotent statements. SQLite
# supports ALTER TABLE ADD COLUMN; we use PRAGMA table_info to check
# whether a column already exists before adding it.

MIGRATIONS = {
    3: [
        # sync_runs table (added in SCHEMA_SQL, so the CREATE IF NOT
        # EXISTS is sufficient - no ALTER needed).

        # companies: incremental sync timestamps
        ("companies", "last_master_sync_at", "TEXT"),
        ("companies", "last_voucher_sync_at", "TEXT"),

        # vouchers: GST-related header fields
        ("vouchers", "party_gstin", "TEXT"),
        ("vouchers", "place_of_supply", "TEXT"),
        ("vouchers", "is_gst_applicable", "TEXT"),
        ("vouchers", "gst_registration_type", "TEXT"),

        # voucher_inventory_allocations: GST line-level fields
        ("voucher_inventory_allocations", "hsn_code", "TEXT"),
        ("voucher_inventory_allocations", "gst_rate", "REAL"),
        ("voucher_inventory_allocations", "cgst_amount", "REAL"),
        ("voucher_inventory_allocations", "sgst_amount", "REAL"),
        ("voucher_inventory_allocations", "igst_amount", "REAL"),
        ("voucher_inventory_allocations", "cess_amount", "REAL"),

        # stock_items: GST classification
        ("stock_items", "hsn_code", "TEXT"),
        ("stock_items", "gst_rate", "REAL"),
    ],
}


def _column_exists(conn, table, column):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _apply_migration(conn, target_version):
    statements = MIGRATIONS.get(target_version, [])
    for table, column, col_type in statements:
        if not _column_exists(conn, table, column):
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
            )
            print(f"  migrated: {table}.{column} ({col_type})")


def initialize_database():
    with get_connection() as connection:
        connection.executescript(SCHEMA_SQL)

        version_count = connection.execute(
            "SELECT COUNT(*) FROM schema_version"
        ).fetchone()[0]

        if not version_count:
            connection.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            current_version = SCHEMA_VERSION
        else:
            current_version = connection.execute(
                "SELECT version FROM schema_version"
            ).fetchone()[0]

        # Apply each missing migration in order
        for v in sorted(MIGRATIONS.keys()):
            if current_version < v:
                print(f"Applying migration to schema v{v}...")
                _apply_migration(connection, v)
                connection.execute(
                    "UPDATE schema_version SET version = ?", (v,)
                )
                current_version = v

    return DATABASE_PATH


def reset_database():
    """Dangerous: drop and recreate all tables. Used by tests only."""

    with get_connection() as connection:
        connection.executescript(
            """
            DROP TABLE IF EXISTS voucher_inventory_allocations;
            DROP TABLE IF EXISTS voucher_ledger_allocations;
            DROP TABLE IF EXISTS vouchers;
            DROP TABLE IF EXISTS report_snapshots;
            DROP TABLE IF EXISTS sync_runs;
            DROP TABLE IF EXISTS godowns;
            DROP TABLE IF EXISTS cost_centres;
            DROP TABLE IF EXISTS cost_categories;
            DROP TABLE IF EXISTS units;
            DROP TABLE IF EXISTS stock_items;
            DROP TABLE IF EXISTS stock_groups;
            DROP TABLE IF EXISTS voucher_types;
            DROP TABLE IF EXISTS ledgers;
            DROP TABLE IF EXISTS groups;
            DROP TABLE IF EXISTS companies;
            DROP TABLE IF EXISTS app_settings;
            DROP TABLE IF EXISTS schema_version;
            """
        )

    return initialize_database()
