"""
Korea Customs Service (관세청) Semiconductor Export Collector
Collects 10-day interval (순별) semiconductor export statistics.

Data sources:
1. 공공데이터포털 (data.go.kr) Open API — HS Code 8542 (전자집적회로/반도체)
2. 수동 입력 fallback — 관세청 보도자료 기반

Publication schedule:
- 매월 1일: 전월 21일~말일 하순 잠정치
- 매월 11일: 당월 1일~10일 상순 잠정치
- 매월 21일: 당월 11일~20일 중순 잠정치
"""
from datetime import date
from app.models.database import get_db, query_db

# 관세청 Open API 기본 설정
# 실제 사용 시 공공데이터포털에서 인증키 발급 필요
CUSTOMS_API_URL = "https://apis.data.go.kr/1220000/nationtradeList/getNationtradeList"
SEMI_HS_CODE = "8542"  # 전자집적회로 (반도체)

INDICATOR_TYPES = {
    "KR_SEMI_EXPORT_AMT": {
        "name_ko": "한국 반도체 수출액 (순별)",
        "name_en": "Korea Semiconductor Export (10-day)",
        "unit": "M_USD",
        "description": "관세청 순별(10일 단위) 반도체(HS8542) 수출금액 잠정치"
    },
    "KR_SEMI_EXPORT_YOY": {
        "name_ko": "한국 반도체 수출 YoY 증감률 (순별)",
        "name_en": "Korea Semi Export YoY Growth (10-day)",
        "unit": "pct",
        "description": "관세청 순별(10일 단위) 반도체 수출 전년동기대비 증감률"
    },
    "KR_TOTAL_EXPORT_AMT": {
        "name_ko": "한국 전체 수출액 (순별)",
        "name_en": "Korea Total Export (10-day)",
        "unit": "M_USD",
        "description": "관세청 순별(10일 단위) 전체 수출금액 잠정치"
    },
}


class KoreaExportCollector:

    def add_manual_entry(self, indicator_type, date_str, value, note=None, source="CUSTOMS_KR"):
        """
        Manually add a 10-day export data point.

        Args:
            indicator_type: KR_SEMI_EXPORT_AMT, KR_SEMI_EXPORT_YOY, or KR_TOTAL_EXPORT_AMT
            date_str: Release/period date in YYYY-MM-DD (use the period start date, e.g., 2026-09-01 for 상순)
            value: Export amount in M_USD or YoY % change
            note: Optional note (e.g., "9월 상순(1~10일) 잠정치")
            source: Data source label
        """
        if indicator_type not in INDICATOR_TYPES:
            return {"error": f"Unknown indicator type: {indicator_type}. Valid: {list(INDICATOR_TYPES.keys())}"}

        meta = INDICATOR_TYPES[indicator_type]

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO industry_indicator (indicator_type, date, value, unit, source, note)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator_type, date)
                DO UPDATE SET value=excluded.value, source=excluded.source, note=excluded.note
                """,
                (indicator_type, date_str, value, meta["unit"], source, note)
            )

        return {
            "status": "success",
            "indicator": indicator_type,
            "date": date_str,
            "value": value,
            "note": note
        }

    def add_10day_report(self, year, month, period, semi_export_amt, semi_yoy_pct=None, total_export_amt=None, note=None):
        """
        Convenience method: add a full 10-day export report in one call.

        Args:
            year: 연도 (int, e.g. 2026)
            month: 월 (int, 1~12)
            period: 순 구분 — '상순'(1~10일), '중순'(11~20일), '하순'(21~말일)
            semi_export_amt: 반도체 수출액 (백만 USD)
            semi_yoy_pct: 반도체 수출 YoY 증감률 (%, optional)
            total_export_amt: 전체 수출액 (백만 USD, optional)
            note: 추가 메모 (optional)
        """
        period_map = {
            "상순": (1, "1~10일"),
            "중순": (11, "11~20일"),
            "하순": (21, "21~말일"),
        }

        if period not in period_map:
            return {"error": f"Invalid period: {period}. Use '상순', '중순', or '하순'"}

        day, day_range = period_map[period]
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        auto_note = note or f"{year}년 {month}월 {period}({day_range}) 잠정치"

        results = []

        # 1. 반도체 수출액
        r = self.add_manual_entry("KR_SEMI_EXPORT_AMT", date_str, semi_export_amt, auto_note)
        results.append(r)

        # 2. 반도체 YoY
        if semi_yoy_pct is not None:
            r = self.add_manual_entry("KR_SEMI_EXPORT_YOY", date_str, semi_yoy_pct, auto_note)
            results.append(r)

        # 3. 전체 수출액
        if total_export_amt is not None:
            r = self.add_manual_entry("KR_TOTAL_EXPORT_AMT", date_str, total_export_amt, auto_note)
            results.append(r)

        return {"status": "success", "period": f"{year}-{month:02d} {period}", "entries": results}

    def get_export_history(self, indicator_type="KR_SEMI_EXPORT_AMT", limit=36):
        """Retrieve historical 10-day export data points."""
        rows = query_db(
            """
            SELECT indicator_type, date, value, unit, source, note
            FROM industry_indicator
            WHERE indicator_type = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (indicator_type, limit)
        )
        return list(reversed(rows))

    def get_all_kr_indicators(self, limit=50):
        """Retrieve all Korea export indicator types, most recent first."""
        rows = query_db(
            """
            SELECT indicator_type, date, value, unit, source, note
            FROM industry_indicator
            WHERE indicator_type LIKE 'KR_%'
            ORDER BY date DESC, indicator_type ASC
            LIMIT ?
            """,
            (limit,)
        )
        return rows
