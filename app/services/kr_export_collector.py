"""
Korea Customs Service (관세청) Semiconductor Export Collector
Collects 10-day interval (순별) and monthly semiconductor export statistics.

Data sources:
1. 공공데이터포털 (data.go.kr) Open API — HS Code 8542 (전자집적회로/반도체)
2. 수동 입력 fallback — 관세청 보도자료 기반 (순별 잠정치)

Publication schedule:
- 매월 1일: 전월 21일~말일 하순 잠정치
- 매월 11일: 당월 1일~10일 상순 잠정치
- 매월 21일: 당월 11일~20일 중순 잠정치
"""
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from typing import Any, Optional

from app.config import CUSTOMS_API_KEY, CUSTOMS_API_URL
from app.models.database import get_db, query_db

logger = logging.getLogger(__name__)

SEMI_HS_CODE = "8542"  # 전자집적회로 (반도체)

INDICATOR_TYPES = {
    "KR_SEMI_EXPORT_AMT": {
        "name_ko": "한국 반도체 수출액 (순별 잠정치)",
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
    "KR_SEMI_EXPORT_MONTHLY_AMT": {
        "name_ko": "관세청 반도체 수출액 (월별 확정치)",
        "name_en": "Korea Semi Export (Monthly)",
        "unit": "M_USD",
        "description": "관세청 Open API 공식 월별 반도체(HS8542) 수출금액"
    },
    "KR_SEMI_EXPORT_MONTHLY_YOY": {
        "name_ko": "관세청 반도체 수출 YoY 증감률 (월별)",
        "name_en": "Korea Semi Export YoY (Monthly)",
        "unit": "pct",
        "description": "관세청 API 월별 반도체 수출 전년동월대비 증감률"
    },
    "KR_SEMI_MEMORY_EXPORT_AMT": {
        "name_ko": "관세청 메모리 반도체 수출액 (HS 854232)",
        "name_en": "Korea Memory Semi Export (Monthly)",
        "unit": "M_USD",
        "description": "관세청 메모리 반도체(DRAM/NAND 등) 월별 수출금액"
    },
    "KR_SEMI_SYSTEM_EXPORT_AMT": {
        "name_ko": "관세청 시스템 반도체 수출액 (HS 854231)",
        "name_en": "Korea System Semi Export (Monthly)",
        "unit": "M_USD",
        "description": "관세청 시스템/프로세서 반도체 월별 수출금액"
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

    def seed_sample_export_data(self) -> int:
        """Seed representative 10-day semiconductor export stats (2025~2026)."""
        samples = [
            # 2026년
            {"year": 2026, "month": 9, "period": "하순", "semi": 5260, "yoy": 38.8, "total": 120944},
            {"year": 2026, "month": 9, "period": "중순", "semi": 4250, "yoy": 44.1, "total": 71409},
            {"year": 2026, "month": 9, "period": "상순", "semi": 4120, "yoy": 42.5, "total": 34973},
            {"year": 2026, "month": 8, "period": "하순", "semi": 4580, "yoy": 38.2, "total": 98282},
            {"year": 2026, "month": 8, "period": "중순", "semi": 3890, "yoy": 36.1, "total": 17200},
            {"year": 2026, "month": 8, "period": "상순", "semi": 3750, "yoy": 41.0, "total": 16900},
            {"year": 2026, "month": 7, "period": "하순", "semi": 4320, "yoy": 49.8, "total": 19100},
            {"year": 2026, "month": 7, "period": "중순", "semi": 3620, "yoy": 45.3, "total": 16400},
            {"year": 2026, "month": 7, "period": "상순", "semi": 3410, "yoy": 48.2, "total": 15800},
            {"year": 2026, "month": 6, "period": "하순", "semi": 4890, "yoy": 52.1, "total": 21000},
            {"year": 2026, "month": 6, "period": "중순", "semi": 3710, "yoy": 50.4, "total": 16800},
            {"year": 2026, "month": 6, "period": "상순", "semi": 3520, "yoy": 53.0, "total": 16200},
            {"year": 2026, "month": 5, "period": "하순", "semi": 4200, "yoy": 46.5, "total": 18900},
            {"year": 2026, "month": 5, "period": "중순", "semi": 3380, "yoy": 44.2, "total": 15300},
        ]

        count = 0
        for s in samples:
            self.add_10day_report(
                year=s["year"],
                month=s["month"],
                period=s["period"],
                semi_export_amt=s["semi"],
                semi_yoy_pct=s["yoy"],
                total_export_amt=s["total"],
                note=f"{s['year']}년 {s['month']}월 {s['period']} 관세청 잠정치 (HS 8542)"
            )
            count += 1
        return count

    def fetch_customs_api(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        hs_code: str = SEMI_HS_CODE
    ) -> dict[str, Any]:
        """
        Fetch official semiconductor export statistics from Korea Customs Service (관세청)
        Open API (http://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList).

        Aggregates:
        - Monthly Total Semi Export (HS 8542)
        - Monthly Memory Semi Export (HS 854232)
        - Monthly System Semi Export (HS 854231)
        - Automatically computes YoY % change against the same month of the prior year.
        """
        if not CUSTOMS_API_KEY:
            return {"status": "error", "message": "CUSTOMS_API_KEY가 설정되지 않았습니다."}

        cur_year = date.today().year
        if end_year is None:
            end_year = cur_year
        if start_year is None:
            start_year = end_year - 1

        all_monthly_totals: dict[str, int] = defaultdict(int)
        all_monthly_memory: dict[str, int] = defaultdict(int)
        all_monthly_system: dict[str, int] = defaultdict(int)
        fetched_years: list[int] = []

        for y in range(start_year, end_year + 1):
            params = {
                "serviceKey": CUSTOMS_API_KEY,
                "strtYymm": f"{y}01",
                "endYymm": f"{y}12",
                "hsSgn": hs_code,
            }
            req_url = f"{CUSTOMS_API_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0 (compatible; QKEarning/1.0)"})
            root = None
            for attempt in range(2):
                try:
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        xml_data = resp.read()
                    root = ET.fromstring(xml_data)
                    break
                except Exception as e:
                    logger.warning(f"Attempt {attempt+1} failed for year {y}: {e}")
                    import time
                    time.sleep(1.0)

            if root is None:
                logger.error(f"Failed to fetch customs API for year {y} after retries")
                continue

            result_code = root.find(".//resultCode")
            if result_code is None or result_code.text != "00":
                msg = root.find(".//resultMsg")
                msg_text = msg.text if msg is not None else "Unknown error"
                logger.warning(f"Customs API returned non-zero code for year {y}: {msg_text}")
                continue

            items = root.findall(".//item")
            year_count = 0
            for it in items:
                ym = it.find("year").text if it.find("year") is not None else ""
                if not ym or ym == "총계":
                    continue
                exp_usd = int(it.find("expDlr").text or 0)
                hscd = it.find("hsCd").text if it.find("hsCd") is not None else ""
                all_monthly_totals[ym] += exp_usd
                if hscd.startswith("854232"):
                    all_monthly_memory[ym] += exp_usd
                elif hscd.startswith("854231"):
                    all_monthly_system[ym] += exp_usd
                year_count += 1

            if year_count > 0:
                fetched_years.append(y)

        if not all_monthly_totals:
            return {"status": "error", "message": "관세청 API로부터 데이터를 수신하지 못했습니다."}

        synced_entries = []
        for ym in sorted(all_monthly_totals.keys()):
            tot_amt = round(all_monthly_totals[ym] / 1e6, 2)
            mem_amt = round(all_monthly_memory[ym] / 1e6, 2)
            sys_amt = round(all_monthly_system[ym] / 1e6, 2)

            # YoY 계산 (전년 동월 대비)
            parts = ym.split(".")
            y_int, m_str = int(parts[0]), parts[1]
            prev_ym = f"{y_int - 1}.{m_str}"
            prev_tot = all_monthly_totals.get(prev_ym, 0)
            yoy_pct = None
            if prev_tot > 0:
                yoy_pct = round(((all_monthly_totals[ym] - prev_tot) / prev_tot) * 100, 2)

            date_str = f"{y_int:04d}-{m_str}-01"
            note = f"관세청 Open API 공식 집계 (HS {hs_code})"

            # DB 저장
            self.add_manual_entry("KR_SEMI_EXPORT_MONTHLY_AMT", date_str, tot_amt, note, source="CUSTOMS_API")
            if yoy_pct is not None:
                self.add_manual_entry("KR_SEMI_EXPORT_MONTHLY_YOY", date_str, yoy_pct, f"관세청 공식 YoY (전년동월 {prev_tot/1e6:.1f}M USD 대비)", source="CUSTOMS_API")
            if mem_amt > 0:
                self.add_manual_entry("KR_SEMI_MEMORY_EXPORT_AMT", date_str, mem_amt, f"메모리반도체(HS854232) 비중: {round(mem_amt/tot_amt*100, 1)}%", source="CUSTOMS_API")
            if sys_amt > 0:
                self.add_manual_entry("KR_SEMI_SYSTEM_EXPORT_AMT", date_str, sys_amt, f"시스템반도체(HS854231) 비중: {round(sys_amt/tot_amt*100, 1)}%", source="CUSTOMS_API")

            synced_entries.append({
                "period": ym,
                "date": date_str,
                "total_amt_m_usd": tot_amt,
                "yoy_pct": yoy_pct,
                "memory_m_usd": mem_amt,
                "system_m_usd": sys_amt
            })

        latest_entry = synced_entries[-1] if synced_entries else None
        return {
            "status": "success",
            "message": f"관세청 API 데이터 동기화 완료: {len(synced_entries)}개 월별 실적 반영 (연도: {fetched_years})",
            "synced_count": len(synced_entries),
            "years": fetched_years,
            "latest": latest_entry,
            "data": synced_entries
        }

    def fetch_10day_customs_api(
        self,
        strt_yymm: Optional[str] = None,
        end_yymm: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Fetch 10-day provisional trade statistics from Korea Customs Service API:
        http://apis.data.go.kr/1220000/cntyMmUtPrviExpAcrs/getCntyMmUtPrviExpAcrs
        """
        if not CUSTOMS_API_KEY:
            return {"status": "error", "message": "CUSTOMS_API_KEY가 설정되지 않았습니다."}

        today = date.today()
        if not end_yymm:
            end_yymm = f"{today.year:04d}{today.month:02d}"
        if not strt_yymm:
            m = today.month - 2
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            strt_yymm = f"{y:04d}{m:02d}"

        url = "http://apis.data.go.kr/1220000/cntyMmUtPrviExpAcrs/getCntyMmUtPrviExpAcrs"
        params = {
            "serviceKey": CUSTOMS_API_KEY,
            "strtYymm": strt_yymm,
            "endYymm": end_yymm,
        }
        req_url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0 (compatible; QKEarning/1.0)"})

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            if "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" in err_body:
                return {
                    "status": "not_registered",
                    "message": "공공데이터포털에서 '관세청_수출 주요국가별 10일 단위 잠정치 통계' 오픈API 활용신청이 필요합니다.",
                    "apply_url": "https://www.data.go.kr/data/15157941/openapi.do"
                }
            return {"status": "error", "message": f"API 호출 오류 (HTTP {e.code}): {e.reason}"}
        except Exception as e:
            return {"status": "error", "message": f"네트워크 오류: {str(e)}"}

        items = root.findall(".//item")
        if not items:
            return {"status": "empty", "message": f"{strt_yymm}~{end_yymm} 기간에 반환된 10일 잠정치 데이터가 없습니다."}

        synced = []
        for it in items:
            y_str = (it.find("priodYear").text or "").strip()
            m_str = (it.find("priodMon").text or "").strip()
            d_str = (it.find("priodDt").text or "").strip()
            
            tot_raw = (it.find("itemUsdAmt00").text or "0").strip().replace(",", "")
            tot_usd_k = float(tot_raw)
            tot_m_usd = round(tot_usd_k / 1000.0, 1)

            us_raw = (it.find("itemUsdAmt02").text or "0").strip().replace(",", "")
            us_m_usd = round(float(us_raw) / 1000.0, 1)

            cn_raw = (it.find("itemUsdAmt01").text or "0").strip().replace(",", "")
            cn_m_usd = round(float(cn_raw) / 1000.0, 1)

            m_int = int(m_str[-2:]) if len(m_str) >= 2 else int(m_str)
            if "10" in d_str:
                day = "01"
                period_name = "상순(1~10일)"
            elif "20" in d_str:
                day = "11"
                period_name = "중순(1~20일 누적)"
            else:
                day = "21"
                period_name = f"하순({d_str} 누적)"

            date_str = f"{int(y_str):04d}-{m_int:02d}-{day}"
            note = f"관세청 10일 잠정치 API ({y_str}년 {m_int}월 {period_name}) | 미국 ${us_m_usd:,.1f}M, 중국 ${cn_m_usd:,.1f}M"
            
            self.add_manual_entry("KR_TOTAL_EXPORT_AMT", date_str, tot_m_usd, note, source="CUSTOMS_10DAY_API")
            synced.append({
                "date": date_str,
                "period": f"{y_str}.{m_int:02d} {period_name}",
                "total_m_usd": tot_m_usd,
                "us_m_usd": us_m_usd,
                "cn_m_usd": cn_m_usd
            })

        latest_entry = synced[-1] if synced else None
        return {
            "status": "success",
            "message": f"관세청 10일 단위 잠정치 API 동기화 완료: 총 {len(synced)}개 기간 반영 (최신: {latest_entry['period'] if latest_entry else '-'})",
            "count": len(synced),
            "latest": latest_entry,
            "data": synced
        }

