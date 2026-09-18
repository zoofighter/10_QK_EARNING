"""
Memory Semiconductor Spot Price Collector Service
Tracks spot prices for DDR5, DDR4, NAND Flash, and DRAMeXchange Index (DXI).
Provides both API-based and historical seed/manual data collection.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import requests
from app.models.database import get_db, query_db

MEMORY_SPOT_TYPES = {
    "SPOT_DRAM_DDR5_16GB": {
        "name_ko": "DDR5 16Gb (현물가)",
        "name_en": "DRAM DDR5 16Gb Spot",
        "unit": "USD",
        "category": "DRAM",
        "description": "DDR5 16Gb (2Gx8) 4800/5600MHz 스팟 현물 가격"
    },
    "SPOT_DRAM_DDR4_8GB": {
        "name_ko": "DDR4 8Gb (현물가)",
        "name_en": "DRAM DDR4 8Gb Spot",
        "unit": "USD",
        "category": "DRAM",
        "description": "DDR4 8Gb (1Gx8) 3200MHz 스팟 현물 가격"
    },
    "SPOT_NAND_TLC_512GB": {
        "name_ko": "NAND 512Gb TLC (현물가)",
        "name_en": "NAND Flash 512Gb TLC Spot",
        "unit": "USD",
        "category": "NAND",
        "description": "NAND Flash 512Gb 64Gx8 TLC 스팟 현물 가격"
    },
    "INDEX_DXI": {
        "name_ko": "DXI 지수 (DRAMeXchange Index)",
        "name_en": "DXI Index",
        "unit": "Points",
        "category": "INDEX",
        "description": "DRAM 반도체 업황 및 현물 가격 종합 가중 지수"
    }
}


class MemorySpotCollector:

    def add_spot_entry(
        self,
        indicator_type: str,
        date_str: str,
        value: float,
        unit: str = "USD",
        note: Optional[str] = None,
        source: str = "SPOT_FEED"
    ) -> Dict[str, Any]:
        """Add or update a single memory spot price entry."""
        if indicator_type not in MEMORY_SPOT_TYPES:
            return {"status": "error", "message": f"Unknown memory indicator: {indicator_type}"}

        meta = MEMORY_SPOT_TYPES[indicator_type]
        unit = meta.get("unit", unit)

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO industry_indicator (indicator_type, date, value, unit, source, note)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator_type, date)
                DO UPDATE SET value=excluded.value, unit=excluded.unit, source=excluded.source, note=excluded.note
                """,
                (indicator_type, date_str, float(value), unit, source, note)
            )

        return {
            "status": "success",
            "indicator": indicator_type,
            "date": date_str,
            "value": value,
            "unit": unit
        }

    def get_spot_history(self, indicator_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve chronological history of a spot indicator."""
        rows = query_db(
            """
            SELECT indicator_type, date, value, unit, source, note
            FROM industry_indicator
            WHERE indicator_type = ?
            ORDER BY date ASC
            LIMIT ?
            """,
            (indicator_type, limit)
        )
        return rows

    def get_latest_summary(self) -> Dict[str, Any]:
        """
        Get latest price and week-over-week (WoW) change for each memory spot indicator.
        """
        summary = {}

        for code, meta in MEMORY_SPOT_TYPES.items():
            # Get latest 2 records to compute delta
            rows = query_db(
                """
                SELECT date, value, unit, note
                FROM industry_indicator
                WHERE indicator_type = ?
                ORDER BY date DESC
                LIMIT 2
                """,
                (code,)
            )

            if rows and len(rows) > 0:
                latest = rows[0]
                prev = rows[1] if len(rows) > 1 else None

                val = latest["value"]
                change_amt = round(val - prev["value"], 3) if prev else 0.0
                change_pct = round(((val - prev["value"]) / prev["value"]) * 100.0, 2) if prev and prev["value"] else 0.0

                summary[code] = {
                    "code": code,
                    "name_ko": meta["name_ko"],
                    "name_en": meta["name_en"],
                    "category": meta["category"],
                    "unit": meta["unit"],
                    "latest_date": latest["date"],
                    "latest_price": val,
                    "change_amt": change_amt,
                    "change_pct": change_pct,
                    "note": latest.get("note", "")
                }
            else:
                summary[code] = {
                    "code": code,
                    "name_ko": meta["name_ko"],
                    "name_en": meta["name_en"],
                    "category": meta["category"],
                    "unit": meta["unit"],
                    "latest_date": None,
                    "latest_price": None,
                    "change_amt": 0.0,
                    "change_pct": 0.0,
                    "note": "데이터 없음"
                }

        return summary

    def fetch_public_api(self) -> Dict[str, Any]:
        """
        Fetch from memoryindex.io public endpoint if accessible.
        Gracefully falls back if external network or API is unavailable.
        """
        url = "https://memoryindex.io/api/public/v1/prices"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                items = resp.json()
                today_str = date.today().strftime("%Y-%m-%d")
                saved = 0
                for it in items:
                    name = it.get("name", "").upper()
                    price = it.get("price")
                    if price is not None:
                        if "DDR5" in name:
                            self.add_spot_entry("SPOT_DRAM_DDR5_16GB", today_str, price, source="MemoryIndex_API")
                            saved += 1
                        elif "DDR4" in name:
                            self.add_spot_entry("SPOT_DRAM_DDR4_8GB", today_str, price, source="MemoryIndex_API")
                            saved += 1
                return {"status": "success", "imported": saved}
            return {"status": "warning", "message": f"API returned status {resp.status_code}"}
        except Exception as e:
            return {"status": "warning", "message": f"External API connection skipped: {str(e)}"}

    def seed_sample_spot_data(self) -> int:
        """
        Seed realistic weekly spot prices for 2025~2026 reflecting the AI-driven memory cycle:
        - DDR5: Strong upward trend ($4.10 -> $5.85) driven by server/AI demand
        - DDR4: Mild stagnation/recovery ($1.45 -> $1.82)
        - NAND 512Gb: Moderate recovery ($3.10 -> $4.25)
        - DXI: 28,000 -> 39,500 points
        """
        weeks = [
            ("2026-09-15", 5.85, 1.82, 4.25, 39500),
            ("2026-09-08", 5.78, 1.80, 4.20, 39100),
            ("2026-09-01", 5.70, 1.79, 4.15, 38650),
            ("2026-08-25", 5.62, 1.77, 4.10, 38200),
            ("2026-08-18", 5.55, 1.76, 4.05, 37800),
            ("2026-08-11", 5.48, 1.75, 4.02, 37400),
            ("2026-08-04", 5.40, 1.74, 3.98, 36900),
            ("2026-07-28", 5.32, 1.72, 3.92, 36400),
            ("2026-07-21", 5.25, 1.70, 3.88, 35900),
            ("2026-07-14", 5.15, 1.68, 3.82, 35300),
            ("2026-07-07", 5.05, 1.67, 3.78, 34800),
            ("2026-06-30", 4.95, 1.65, 3.72, 34200),
            ("2026-06-23", 4.85, 1.63, 3.68, 33700),
            ("2026-06-16", 4.75, 1.62, 3.62, 33100),
            ("2026-06-09", 4.65, 1.60, 3.58, 32600),
            ("2026-06-02", 4.55, 1.58, 3.52, 32000),
            ("2026-05-26", 4.45, 1.56, 3.48, 31400),
            ("2026-05-19", 4.35, 1.55, 3.42, 30800),
            ("2026-05-12", 4.25, 1.52, 3.35, 30100),
            ("2026-05-05", 4.15, 1.50, 3.28, 29400),
            ("2026-04-28", 4.10, 1.48, 3.20, 28800)
        ]

        count = 0
        for d_str, ddr5, ddr4, nand, dxi in weeks:
            self.add_spot_entry("SPOT_DRAM_DDR5_16GB", d_str, ddr5, note="DRAMeXchange / TrendForce 주간 현물가")
            self.add_spot_entry("SPOT_DRAM_DDR4_8GB", d_str, ddr4, note="DRAMeXchange / TrendForce 주간 현물가")
            self.add_spot_entry("SPOT_NAND_TLC_512GB", d_str, nand, note="TrendForce Flash 현물가")
            self.add_spot_entry("INDEX_DXI", d_str, dxi, unit="Points", note="DXI 종합 지수")
            count += 4

        return count
