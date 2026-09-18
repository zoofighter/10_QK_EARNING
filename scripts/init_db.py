#!/usr/bin/env python3
"""
Initialize SQLite database and directories for QK_EARNING application.
Creates all 11 tables plus FTS5 virtual search table.
"""
import sqlite3
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import DB_PATH, FILINGS_DIR, DATA_DIR

SCHEMA_SQL = """
-- 1. Layer Master
CREATE TABLE IF NOT EXISTS layer (
    code TEXT PRIMARY KEY,
    name_ko TEXT NOT NULL,
    name_en TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- 2. Entity Master (Companies)
CREATE TABLE IF NOT EXISTS entity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    name_en TEXT NOT NULL,
    name_ko TEXT NOT NULL,
    layer_code TEXT NOT NULL,
    exchange TEXT,
    sec_cik TEXT,
    country TEXT NOT NULL DEFAULT 'US',
    data_source TEXT NOT NULL DEFAULT 'SEC',
    fiscal_year_end TEXT DEFAULT '12',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (layer_code) REFERENCES layer(code) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_entity_ticker ON entity(ticker);
CREATE INDEX IF NOT EXISTS idx_entity_layer ON entity(layer_code);
CREATE INDEX IF NOT EXISTS idx_entity_cik ON entity(sec_cik);

-- 3. Filing Documents (10-Q, 10-K, 8-K, 20-F, 6-K)
CREATE TABLE IF NOT EXISTS filing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    filing_type TEXT NOT NULL,
    fiscal_year TEXT,
    fiscal_quarter TEXT,
    period_end_date TEXT,
    filed_date TEXT NOT NULL,
    accession_number TEXT,
    source_url TEXT,
    local_file_path TEXT,
    raw_text TEXT,
    status TEXT NOT NULL DEFAULT 'DOWNLOADED', -- DOWNLOADED, PARSED, REVIEWED, ERROR
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (entity_id) REFERENCES entity(id) ON DELETE CASCADE,
    UNIQUE (entity_id, filing_type, fiscal_year, fiscal_quarter, accession_number)
);

CREATE INDEX IF NOT EXISTS idx_filing_entity ON filing(entity_id);
CREATE INDEX IF NOT EXISTS idx_filing_filed_date ON filing(filed_date DESC);
CREATE INDEX IF NOT EXISTS idx_filing_type ON filing(filing_type);

-- 4. Filing Full-Text Search (SQLite FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS filing_fts USING fts5(
    filing_id UNINDEXED,
    ticker,
    filing_type,
    fiscal_period,
    content
);

-- 5. Earning Calls
CREATE TABLE IF NOT EXISTS earning_call (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    fiscal_year TEXT NOT NULL,
    fiscal_quarter TEXT NOT NULL,
    call_date TEXT,
    call_time_et TEXT,
    transcript_text TEXT,
    source_url TEXT,
    local_file_path TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (entity_id) REFERENCES entity(id) ON DELETE CASCADE,
    UNIQUE (entity_id, fiscal_year, fiscal_quarter)
);

CREATE INDEX IF NOT EXISTS idx_call_entity ON earning_call(entity_id);
CREATE INDEX IF NOT EXISTS idx_call_date ON earning_call(call_date DESC);

-- 6. Financial Metrics (Extracted / Normalized)
CREATE TABLE IF NOT EXISTS financial_metric (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    fiscal_year TEXT NOT NULL,
    fiscal_quarter TEXT NOT NULL,
    metric_type TEXT NOT NULL, -- revenue, eps, op_margin_pct, capex, guidance_rev_next_q, etc.
    value REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    original_currency TEXT DEFAULT 'USD', -- KRW, JPY, EUR, TWD, USD
    fx_rate REAL DEFAULT 1.0, -- Exchange rate applied (e.g. 1350 for KRW/USD)
    unit TEXT DEFAULT 'M', -- M=million, B=billion, T=trillion, pct=%, ratio
    source TEXT DEFAULT 'AUTO', -- AUTO, MANUAL, LLM
    filing_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (entity_id) REFERENCES entity(id) ON DELETE CASCADE,
    FOREIGN KEY (filing_id) REFERENCES filing(id) ON DELETE SET NULL,
    UNIQUE (entity_id, fiscal_year, fiscal_quarter, metric_type)
);

CREATE INDEX IF NOT EXISTS idx_metric_lookup ON financial_metric(entity_id, fiscal_year, fiscal_quarter);
CREATE INDEX IF NOT EXISTS idx_metric_type ON financial_metric(metric_type);

-- 7. Consensus & Beat/Miss
CREATE TABLE IF NOT EXISTS consensus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    fiscal_year TEXT NOT NULL,
    fiscal_quarter TEXT NOT NULL,
    metric_type TEXT NOT NULL DEFAULT 'revenue',
    consensus_value REAL,
    actual_value REAL,
    surprise_pct REAL,
    beat_miss_status TEXT, -- BEAT, INLINE, MISS
    post_earning_return_1d REAL,
    post_earning_return_5d REAL,
    source TEXT DEFAULT 'MANUAL',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (entity_id) REFERENCES entity(id) ON DELETE CASCADE,
    UNIQUE (entity_id, fiscal_year, fiscal_quarter, metric_type)
);

CREATE INDEX IF NOT EXISTS idx_consensus_entity ON consensus(entity_id);

-- 8. Earning Calendar
CREATE TABLE IF NOT EXISTS earning_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    fiscal_year TEXT NOT NULL,
    fiscal_quarter TEXT NOT NULL,
    expected_date TEXT NOT NULL,
    actual_date TEXT,
    call_time_et TEXT,
    status TEXT DEFAULT 'UPCOMING', -- UPCOMING, CONFIRMED, COMPLETED, POSTPONED
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (entity_id) REFERENCES entity(id) ON DELETE CASCADE,
    UNIQUE (entity_id, fiscal_year, fiscal_quarter)
);

CREATE INDEX IF NOT EXISTS idx_calendar_expected ON earning_calendar(expected_date ASC);

-- 9. Stock Price (OHLCV)
CREATE TABLE IF NOT EXISTS stock_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    adj_close REAL,
    volume INTEGER,
    FOREIGN KEY (entity_id) REFERENCES entity(id) ON DELETE CASCADE,
    UNIQUE (entity_id, date)
);

CREATE INDEX IF NOT EXISTS idx_price_lookup ON stock_price(entity_id, date DESC);

-- 10. Industry Indicator (TSMC Rev, Memory Spot, Hyperscaler CapEx)
CREATE TABLE IF NOT EXISTS industry_indicator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_type TEXT NOT NULL, -- TSMC_MONTHLY_REV, DRAM_SPOT, NAND_SPOT, SEMI_BILLING, HYPERSCALER_CAPEX
    date TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    source TEXT,
    note TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE (indicator_type, date)
);

CREATE INDEX IF NOT EXISTS idx_indicator_type_date ON industry_indicator(indicator_type, date DESC);

-- 11. Keyword Analysis
CREATE TABLE IF NOT EXISTS keyword_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    earning_call_id INTEGER,
    entity_id INTEGER NOT NULL,
    fiscal_year TEXT NOT NULL,
    fiscal_quarter TEXT NOT NULL,
    keyword TEXT NOT NULL,
    keyword_group TEXT NOT NULL, -- AI/ML, CapEx, Demand, Margin, Guidance, Inventory, China
    frequency INTEGER NOT NULL DEFAULT 0,
    context_snippets TEXT, -- JSON or concatenated text
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (earning_call_id) REFERENCES earning_call(id) ON DELETE SET NULL,
    FOREIGN KEY (entity_id) REFERENCES entity(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_keyword_lookup ON keyword_analysis(entity_id, keyword);

-- 12. LLM Summary
CREATE TABLE IF NOT EXISTS llm_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id INTEGER,
    earning_call_id INTEGER,
    entity_id INTEGER NOT NULL,
    summary_type TEXT NOT NULL, -- FILING_SUMMARY, CALL_QA_HIGHLIGHT, LAYER_COMPARISON
    content_md TEXT NOT NULL,
    model_used TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (filing_id) REFERENCES filing(id) ON DELETE SET NULL,
    FOREIGN KEY (earning_call_id) REFERENCES earning_call(id) ON DELETE SET NULL,
    FOREIGN KEY (entity_id) REFERENCES entity(id) ON DELETE CASCADE
);
"""

def init_database():
    """Create data directories and initialize tables."""
    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for folder in ["10-Q", "10-K", "8-K", "20-F", "6-K", "earning_calls"]:
        (FILINGS_DIR / folder).mkdir(parents=True, exist_ok=True)

    print(f"📁 Verified data directories at {DATA_DIR}")

    # Connect to SQLite
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        print(f"✅ Successfully initialized database schema at: {DB_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
