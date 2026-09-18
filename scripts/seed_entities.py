#!/usr/bin/env python3
"""
Seed Layer and 34 Entity master records, plus initial sample earnings calendar entries.
"""
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import DB_PATH

LAYERS = [
    ("L2_HYPERSCALER", "하이퍼스케일러", "Hyperscalers", 1),
    ("L3_COMPUTE", "컴퓨팅/가속기", "Compute & Accelerators", 2),
    ("L4_FOUNDRY", "파운드리/장비", "Foundry & Equipment", 3),
    ("L5_MEMORY", "메모리/스토리지", "Memory & Storage", 4),
    ("L6_OPTICAL", "광통신/네트워킹", "Optical & Networking", 5),
    ("L7_INFRA", "인프라/특수", "Infrastructure & Specialized", 6),
    ("L8_POWER", "전력/에너지", "Power & Energy", 7),
]

ENTITIES = [
    # L2_HYPERSCALER (7)
    ("GOOGL", "Alphabet Inc.", "구글(알파벳)", "L2_HYPERSCALER", "NASDAQ", "0001652044", "US", "SEC", "12"),
    ("AMZN", "Amazon.com Inc.", "아마존", "L2_HYPERSCALER", "NASDAQ", "0001018724", "US", "SEC", "12"),
    ("MSFT", "Microsoft Corp.", "마이크로소프트", "L2_HYPERSCALER", "NASDAQ", "0000789019", "US", "SEC", "06"),
    ("META", "Meta Platforms Inc.", "메타", "L2_HYPERSCALER", "NASDAQ", "0001326801", "US", "SEC", "12"),
    ("ORCL", "Oracle Corp.", "오라클", "L2_HYPERSCALER", "NYSE", "0001341439", "US", "SEC", "05"),
    ("CRWV", "CoreWeave Inc.", "코어위브", "L2_HYPERSCALER", "NASDAQ", "0001925345", "US", "SEC", "12"),
    ("NBIS", "Nebius Group N.V.", "네비우스", "L2_HYPERSCALER", "NASDAQ", "0001513845", "NL", "SEC", "12"),

    # L3_COMPUTE (5)
    ("NVDA", "NVIDIA Corp.", "엔비디아", "L3_COMPUTE", "NASDAQ", "0001045810", "US", "SEC", "01"),
    ("AMD", "Advanced Micro Devices Inc.", "AMD", "L3_COMPUTE", "NASDAQ", "0000002488", "US", "SEC", "12"),
    ("AVGO", "Broadcom Inc.", "브로드컴", "L3_COMPUTE", "NASDAQ", "0001730168", "US", "SEC", "10"),
    ("ARM", "Arm Holdings plc", "Arm", "L3_COMPUTE", "NASDAQ", "0001973239", "UK", "SEC", "03"),
    ("INTC", "Intel Corp.", "인텔", "L3_COMPUTE", "NASDAQ", "0000050863", "US", "SEC", "12"),

    # L4_FOUNDRY (7)
    ("TSM", "Taiwan Semiconductor Manufacturing Co.", "TSMC", "L4_FOUNDRY", "NYSE", "0001046179", "TW", "SEC", "12"),
    ("ASML", "ASML Holding N.V.", "ASML", "L4_FOUNDRY", "NASDAQ", "0000937966", "NL", "SEC", "12"),
    ("AMAT", "Applied Materials Inc.", "어플라이드 머티어리얼즈", "L4_FOUNDRY", "NASDAQ", "0000006951", "US", "SEC", "10"),
    ("LRCX", "Lam Research Corp.", "램리서치", "L4_FOUNDRY", "NASDAQ", "0000707549", "US", "SEC", "06"),
    ("KLAC", "KLA Corp.", "KLA", "L4_FOUNDRY", "NASDAQ", "0000314606", "US", "SEC", "06"),
    ("ASX", "ASE Technology Holding Co.", "ASE (日月光)", "L4_FOUNDRY", "NYSE", "0001732646", "TW", "SEC", "12"),
    ("AMKR", "Amkor Technology Inc.", "앰코 테크놀로지", "L4_FOUNDRY", "NASDAQ", "0001047537", "US", "SEC", "12"),

    # L5_MEMORY (5)
    ("000660.KS", "SK Hynix Inc.", "SK하이닉스", "L5_MEMORY", "KRX", None, "KR", "DART", "12"),
    ("005930.KS", "Samsung Electronics Co.", "삼성전자", "L5_MEMORY", "KRX", None, "KR", "DART", "12"),
    ("MU", "Micron Technology Inc.", "마이크론 테크놀로지", "L5_MEMORY", "NASDAQ", "0000723125", "US", "SEC", "08"),
    ("WDC", "Western Digital Corp.", "웨스턴 디지털", "L5_MEMORY", "NASDAQ", "0000106040", "US", "SEC", "06"),
    ("6600.T", "Kioxia Holdings Corp.", "키옥시아", "L5_MEMORY", "TSE", None, "JP", "MANUAL", "03"),

    # L6_OPTICAL (3)
    ("MRVL", "Marvell Technology Inc.", "마벨 테크놀로지", "L6_OPTICAL", "NASDAQ", "0001835632", "US", "SEC", "01"),
    ("COHR", "Coherent Corp.", "코히어런트", "L6_OPTICAL", "NYSE", "0000863894", "US", "SEC", "06"),
    ("ANET", "Arista Networks Inc.", "아리스타 네트웍스", "L6_OPTICAL", "NYSE", "0001596532", "US", "SEC", "12"),

    # L7_INFRA (3)
    ("SPACEX", "SpaceX / xAI", "스페이스X / xAI", "L7_INFRA", "UNLISTED", None, "US", "MANUAL", "12"),
    ("9984.T", "SoftBank Group Corp.", "소프트뱅크 그룹", "L7_INFRA", "TSE", None, "JP", "MANUAL", "03"),
    ("AAPL", "Apple Inc.", "애플", "L7_INFRA", "NASDAQ", "0000320193", "US", "SEC", "09"),

    # L8_POWER (4)
    ("VRT", "Vertiv Holdings Co.", "버티브 홀딩스", "L8_POWER", "NYSE", "0001674101", "US", "SEC", "12"),
    ("ETN", "Eaton Corporation plc", "이튼", "L8_POWER", "NYSE", "0001551182", "IE", "SEC", "12"),
    ("GEV", "GE Vernova Inc.", "GE 버노바", "L8_POWER", "NYSE", "0001996810", "US", "SEC", "12"),
    ("SBGSF", "Schneider Electric SE", "슈나이더 일렉트릭", "L8_POWER", "OTC", "0001158654", "FR", "SEC", "12"),
]

# Sample upcoming earnings calendar to demonstrate calendar UI immediately
CALENDAR_SEEDS = [
    ("NVDA", "2026", "Q3", "2026-09-24", "17:00", "CONFIRMED"),
    ("GOOGL", "2026", "Q3", "2026-10-01", "16:30", "UPCOMING"),
    ("AMZN", "2026", "Q3", "2026-10-06", "17:30", "UPCOMING"),
    ("META", "2026", "Q3", "2026-10-08", "17:00", "UPCOMING"),
    ("MSFT", "2026", "Q1", "2026-10-15", "17:30", "UPCOMING"),
    ("TSM", "2026", "Q3", "2026-10-16", "02:00", "UPCOMING"),
    ("ASML", "2026", "Q3", "2026-10-21", "09:00", "UPCOMING"),
    ("AAPL", "2026", "Q4", "2026-10-29", "17:00", "UPCOMING"),
    ("MU", "2026", "Q4", "2026-09-27", "16:30", "CONFIRMED"),
    ("VRT", "2026", "Q3", "2026-10-23", "11:00", "UPCOMING"),
    ("000660.KS", "2026", "Q3", "2026-10-24", "09:00", "UPCOMING"),
    ("005930.KS", "2026", "Q3", "2026-10-31", "09:00", "UPCOMING"),
]

def seed():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 1. Seed Layers
    cur.executemany(
        """
        INSERT OR REPLACE INTO layer (code, name_ko, name_en, sort_order)
        VALUES (?, ?, ?, ?)
        """,
        LAYERS
    )
    print(f"✅ Seeded {len(LAYERS)} layers.")

    # 2. Seed Entities
    cur.executemany(
        """
        INSERT OR REPLACE INTO entity (
            ticker, name_en, name_ko, layer_code, exchange, sec_cik, country, data_source, fiscal_year_end
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ENTITIES
    )
    print(f"✅ Seeded {len(ENTITIES)} entities.")

    # 3. Seed Calendar samples
    for ticker, fy, fq, exp_date, call_time, status in CALENDAR_SEEDS:
        cur.execute("SELECT id FROM entity WHERE ticker = ?", (ticker,))
        row = cur.fetchone()
        if row:
            entity_id = row[0]
            cur.execute(
                """
                INSERT OR REPLACE INTO earning_calendar (
                    entity_id, fiscal_year, fiscal_quarter, expected_date, call_time_et, status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (entity_id, fy, fq, exp_date, call_time, status)
            )
    print(f"✅ Seeded {len(CALENDAR_SEEDS)} upcoming earnings calendar items.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed()
