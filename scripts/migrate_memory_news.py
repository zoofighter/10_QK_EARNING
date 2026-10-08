#!/usr/bin/env python3
"""
Migrate Memory Claude data (contracts, fab_capacity, datacenter_capacity)
and News data (news.sqlite) into QK_EARNING database (data/qk_earning.db).
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
QK_DB_PATH = BASE_DIR / "data" / "qk_earning.db"
MEMORY_DB_PATH = Path("/Users/boon/Dropbox/03_code/b_0910_memory_claude/data/memory_claude.db")
NEWS_DB_PATH = Path("/Users/boon/Dropbox/03_code/b_0826_news_research/db/news.sqlite")

def migrate_schemas_and_data():
    qk_conn = sqlite3.connect(str(QK_DB_PATH))
    qk_conn.execute("PRAGMA foreign_keys = OFF;") # To allow bulk inserts
    qk_cur = qk_conn.cursor()

    print("Creating tables in qk_earning.db...")

    # 1. mega_contracts / contracts
    qk_cur.execute("""
    CREATE TABLE IF NOT EXISTS contracts (
        contract_id     TEXT PRIMARY KEY,
        buyer_id        TEXT NOT NULL,
        seller_id       TEXT NOT NULL,
        contract_type   TEXT NOT NULL,
        value_b         REAL,
        currency        TEXT DEFAULT 'USD',
        announced_date  TEXT,
        start_date      TEXT,
        end_date        TEXT,
        description     TEXT,
        product_type    TEXT,
        confidence      TEXT DEFAULT 'C3',
        source          TEXT,
        raw_source      TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    );
    """)
    qk_cur.execute("CREATE INDEX IF NOT EXISTS idx_contract_buyer ON contracts(buyer_id);")
    qk_cur.execute("CREATE INDEX IF NOT EXISTS idx_contract_seller ON contracts(seller_id);")

    # 2. fab_capacity
    qk_cur.execute("""
    CREATE TABLE IF NOT EXISTS fab_capacity (
        fab_id              TEXT PRIMARY KEY,
        entity_id           TEXT NOT NULL,
        fab_name            TEXT NOT NULL,
        location_city       TEXT,
        location_country    TEXT,
        process_node        TEXT,
        fab_type            TEXT DEFAULT 'FAB',
        wspm_current        REAL,
        wspm_target         REAL,
        ramp_start_date     TEXT,
        ramp_end_date       TEXT,
        capex_invested_b    REAL,
        utilization_pct     REAL,
        yield_pct           REAL,
        status              TEXT DEFAULT 'OPERATING',
        key_customers       TEXT,
        key_notes           TEXT,
        raw_source          TEXT,
        created_at          TEXT DEFAULT (datetime('now')),
        updated_at          TEXT DEFAULT (datetime('now'))
    );
    """)
    qk_cur.execute("CREATE INDEX IF NOT EXISTS idx_fab_entity ON fab_capacity(entity_id);")
    qk_cur.execute("CREATE INDEX IF NOT EXISTS idx_fab_status ON fab_capacity(status);")

    # 3. datacenter_capacity
    qk_cur.execute("""
    CREATE TABLE IF NOT EXISTS datacenter_capacity (
        dc_id               TEXT PRIMARY KEY,
        entity_id           TEXT NOT NULL,
        dc_name             TEXT NOT NULL,
        location_state      TEXT,
        location_country    TEXT DEFAULT 'USA',
        power_mw_current    REAL,
        power_mw_target     REAL,
        power_source        TEXT,
        cooling_type        TEXT,
        gpu_cluster_target  INTEGER,
        primary_chips       TEXT,
        online_date         TEXT,
        status              TEXT DEFAULT 'CONSTRUCTION',
        capex_est_b         REAL,
        key_notes           TEXT,
        source              TEXT,
        created_at          TEXT DEFAULT (datetime('now')),
        updated_at          TEXT DEFAULT (datetime('now'))
    );
    """)
    qk_cur.execute("CREATE INDEX IF NOT EXISTS idx_dc_entity ON datacenter_capacity(entity_id);")
    qk_cur.execute("CREATE INDEX IF NOT EXISTS idx_dc_status ON datacenter_capacity(status);")

    # 4. company news table
    qk_cur.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        url          TEXT UNIQUE NOT NULL,
        title        TEXT NOT NULL,
        snippet      TEXT,
        source       TEXT NOT NULL,
        company      TEXT NOT NULL,
        ticker       TEXT,
        query        TEXT,
        score        INTEGER DEFAULT 0,
        published    TEXT,
        collected_at TEXT NOT NULL
    );
    """)
    qk_cur.execute("CREATE INDEX IF NOT EXISTS idx_news_ticker ON news(ticker);")
    qk_cur.execute("CREATE INDEX IF NOT EXISTS idx_news_company ON news(company);")
    qk_cur.execute("CREATE INDEX IF NOT EXISTS idx_news_score ON news(score DESC);")
    qk_cur.execute("CREATE INDEX IF NOT EXISTS idx_news_published ON news(published DESC);")

    qk_conn.commit()

    # Migrate Memory Claude data
    if MEMORY_DB_PATH.exists():
        print(f"Migrating from {MEMORY_DB_PATH}...")
        mem_conn = sqlite3.connect(str(MEMORY_DB_PATH))
        mem_cur = mem_conn.cursor()

        # contracts
        mem_cur.execute("SELECT contract_id, buyer_id, seller_id, contract_type, value_b, currency, announced_date, start_date, end_date, description, product_type, confidence, source, raw_source FROM contracts")
        contracts = mem_cur.fetchall()
        qk_cur.executemany("""
        INSERT OR REPLACE INTO contracts (
            contract_id, buyer_id, seller_id, contract_type, value_b, currency,
            announced_date, start_date, end_date, description, product_type,
            confidence, source, raw_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, contracts)
        print(f"  -> Migrated {len(contracts)} contracts")

        # fab_capacity
        mem_cur.execute("SELECT fab_id, entity_id, fab_name, location_city, location_country, process_node, fab_type, wspm_current, wspm_target, ramp_start_date, ramp_end_date, capex_invested_b, utilization_pct, yield_pct, status, key_customers, key_notes, raw_source FROM fab_capacity")
        fabs = mem_cur.fetchall()
        qk_cur.executemany("""
        INSERT OR REPLACE INTO fab_capacity (
            fab_id, entity_id, fab_name, location_city, location_country, process_node,
            fab_type, wspm_current, wspm_target, ramp_start_date, ramp_end_date,
            capex_invested_b, utilization_pct, yield_pct, status, key_customers,
            key_notes, raw_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, fabs)
        print(f"  -> Migrated {len(fabs)} fabs")

        # datacenter_capacity
        mem_cur.execute("SELECT dc_id, entity_id, dc_name, location_state, location_country, power_mw_current, power_mw_target, power_source, cooling_type, gpu_cluster_target, primary_chips, online_date, status, capex_est_b, key_notes, source FROM datacenter_capacity")
        dcs = mem_cur.fetchall()
        qk_cur.executemany("""
        INSERT OR REPLACE INTO datacenter_capacity (
            dc_id, entity_id, dc_name, location_state, location_country, power_mw_current,
            power_mw_target, power_source, cooling_type, gpu_cluster_target,
            primary_chips, online_date, status, capex_est_b, key_notes, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dcs)
        print(f"  -> Migrated {len(dcs)} datacenters")

        mem_conn.close()
    else:
        print(f"Warning: {MEMORY_DB_PATH} not found.")

    # Migrate News data
    if NEWS_DB_PATH.exists():
        print(f"Migrating news from {NEWS_DB_PATH}...")
        news_conn = sqlite3.connect(str(NEWS_DB_PATH))
        news_cur = news_conn.cursor()

        news_cur.execute("SELECT url, title, snippet, source, company, ticker, query, score, published, collected_at FROM news")
        news_rows = news_cur.fetchall()
        qk_cur.executemany("""
        INSERT OR IGNORE INTO news (
            url, title, snippet, source, company, ticker, query, score, published, collected_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, news_rows)
        print(f"  -> Migrated {len(news_rows)} news articles")
        news_conn.close()
    else:
        print(f"Warning: {NEWS_DB_PATH} not found.")

    qk_conn.commit()
    qk_conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_schemas_and_data()
