"""
Quarterly Financial Metrics Service
Manages 10-Q / 10-K quarterly earnings data from 2020 to present:
Revenue, Operating Income, Net Income, Gross Margin, CapEx, and Segment revenues.
"""
from typing import Dict, Any, List, Optional
from app.models.database import get_db, query_db


class FinancialService:

    @staticmethod
    def get_ticker_fx_info(ticker: str) -> Dict[str, Any]:
        """Return original reporting currency and FX conversion rate to USD."""
        if ticker in ("005930.KS", "000660.KS"):
            return {"currency": "KRW", "fx_rate": 1350.0, "symbol": "₩", "label": "₩1,350/$ (KRW)"}
        elif ticker in ("6600.T", "9984.T"):
            return {"currency": "JPY", "fx_rate": 155.0, "symbol": "¥", "label": "¥155/$ (JPY)"}
        elif ticker in ("ASML", "SBGSF"):
            return {"currency": "EUR", "fx_rate": 0.92, "symbol": "€", "label": "€0.92/$ (EUR)"}
        elif ticker in ("TSM", "ASX"):
            return {"currency": "TWD", "fx_rate": 32.0, "symbol": "NT$", "label": "NT$32/$ (TWD)"}
        else:
            return {"currency": "USD", "fx_rate": 1.0, "symbol": "$", "label": "USD (기준)"}

    def record_metric(
        self,
        ticker: str,
        fiscal_year: str,
        fiscal_quarter: str,
        metric_type: str,
        value: float,
        filing_id: Optional[int] = None,
        source: str = "AUTO",
        fx_rate: float = 1.0,
        original_currency: str = "USD"
    ) -> Dict[str, Any]:
        """Insert or update a single financial metric."""
        entity = query_db("SELECT id FROM entity WHERE ticker = ?", (ticker,), one=True)
        if not entity:
            return {"status": "error", "message": f"Entity not found: {ticker}"}

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO financial_metric (
                    entity_id, fiscal_year, fiscal_quarter, metric_type, value, filing_id, source, fx_rate, original_currency
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_id, fiscal_year, fiscal_quarter, metric_type)
                DO UPDATE SET value=excluded.value, filing_id=excluded.filing_id, source=excluded.source, fx_rate=excluded.fx_rate, original_currency=excluded.original_currency
                """,
                (entity["id"], str(fiscal_year), fiscal_quarter.upper(), metric_type.lower(), float(value), filing_id, source, fx_rate, original_currency)
            )

        return {"status": "success", "ticker": ticker, "metric": metric_type, "value": value}

    def get_quarterly_financials(self, ticker: str, start_year: int = 2020) -> Dict[str, Any]:
        """
        Retrieve complete quarterly financial series from start_year (e.g. 2020) to present,
        joined with corresponding 10-Q/10-K filing documents and MD&A notes.
        """
        entity = query_db(
            """
            SELECT e.*, l.name_ko as layer_name_ko, l.name_en as layer_name_en
            FROM entity e
            JOIN layer l ON e.layer_code = l.code
            WHERE e.ticker = ?
            """,
            (ticker,),
            one=True
        )
        if not entity:
            return {"status": "error", "message": f"Entity {ticker} not found"}

        # Fetch all metrics
        metrics = query_db(
            """
            SELECT fiscal_year, fiscal_quarter, metric_type, value, filing_id
            FROM financial_metric
            WHERE entity_id = ? AND cast(fiscal_year as integer) >= ?
            ORDER BY fiscal_year DESC, fiscal_quarter DESC
            """,
            (entity["id"], start_year)
        )

        # Fetch filings for matching
        filings = query_db(
            """
            SELECT id, filing_type, fiscal_year, fiscal_quarter, filed_date, accession_number, source_url
            FROM filing
            WHERE entity_id = ? AND filing_type IN ('10-Q', '10-K')
            """,
            (entity["id"],)
        )

        filing_map = {}
        for f in filings:
            key = f"{f['fiscal_year']}-{f['fiscal_quarter']}"
            filing_map[key] = f
            if f.get("fiscal_quarter") == "FY":
                filing_map[f"{f['fiscal_year']}-Q4"] = f

        # Group metrics by quarter
        grouped = {}
        for m in metrics:
            q_key = f"{m['fiscal_year']}-{m['fiscal_quarter']}"
            if q_key not in grouped:
                grouped[q_key] = {
                    "fiscal_year": m["fiscal_year"],
                    "fiscal_quarter": m["fiscal_quarter"],
                    "period_key": q_key,
                    "metrics": {}
                }
            grouped[q_key]["metrics"][m["metric_type"]] = m["value"]

        # Sort quarters chronologically
        sorted_keys = sorted(grouped.keys(), reverse=True)
        series = []
        fx_info = self.get_ticker_fx_info(ticker)

        for k in sorted_keys:
            item = grouped[k]
            met = item["metrics"]
            rev = met.get("revenue")
            op_inc = met.get("operating_income")
            net_inc = met.get("net_income")
            capex = met.get("capex")
            dc_rev = met.get("segment_datacenter")
            gaming_rev = met.get("segment_gaming")

            op_margin = round((op_inc / rev * 100), 1) if rev and op_inc else None
            dc_ratio = round((dc_rev / rev * 100), 1) if rev and dc_rev else None

            # Corresponding filing
            f_info = filing_map.get(k, {})

            # Earnings release date (실적발표일)
            fy_end = entity.get("fiscal_year_end") if entity else "12"
            rel_date = (
                f_info.get("filed_date")
                or self._get_default_release_date(ticker, item["fiscal_year"], item["fiscal_quarter"], fy_end)
            )

            # YoY calculation if prior year same quarter exists
            yr = int(item["fiscal_year"])
            prior_k = f"{yr - 1}-{item['fiscal_quarter']}"
            prior_rev = grouped.get(prior_k, {}).get("metrics", {}).get("revenue")
            rev_yoy = round(((rev - prior_rev) / prior_rev * 100), 1) if rev and prior_rev else None

            default_ftype = "10-K" if item["fiscal_quarter"] == "Q4" else "10-Q"
            if ticker in ("TSM", "ASML", "ARM", "ASX") and item["fiscal_quarter"] == "Q4":
                default_ftype = "20-F"

            # Original currency display string (e.g. KRW 조원, JPY 조엔, EUR)
            orig_rev_str = None
            if fx_info["currency"] == "KRW" and rev:
                rev_krw_tril = (rev * fx_info["fx_rate"]) / 1_000_000
                orig_rev_str = f"약 {rev_krw_tril:.1f}조원"
            elif fx_info["currency"] == "JPY" and rev:
                rev_jpy_tril = (rev * fx_info["fx_rate"]) / 1_000_000
                orig_rev_str = f"약 {rev_jpy_tril:.1f}조엔"
            elif fx_info["currency"] == "EUR" and rev:
                rev_eur_b = (rev * fx_info["fx_rate"]) / 1_000
                orig_rev_str = f"€{rev_eur_b:.1f}B"
            elif fx_info["currency"] == "TWD" and rev:
                rev_twd_b = (rev * fx_info["fx_rate"]) / 1_000
                orig_rev_str = f"NT${rev_twd_b:.0f}B"

            series.append({
                "period": k,
                "period_key": k,
                "fiscal_year": item["fiscal_year"],
                "fiscal_quarter": item["fiscal_quarter"],
                "revenue": rev,
                "revenue_yoy_pct": rev_yoy,
                "operating_income": op_inc,
                "op_margin_pct": op_margin,
                "net_income": net_inc,
                "capex": capex,
                "revenue_datacenter": dc_rev,
                "revenue_datacenter_pct": dc_ratio,
                "segment_datacenter": dc_rev,
                "segment_datacenter_ratio": dc_ratio,
                "segment_gaming": gaming_rev,
                "filing_id": f_info.get("id"),
                "filing_type": f_info.get("filing_type", default_ftype),
                "report_date": rel_date,
                "filed_date": rel_date,
                "accession_number": f_info.get("accession_number"),
                "mda_summary": self._get_default_mda_note(ticker, k),
                "fx_rate": fx_info["fx_rate"],
                "fx_rate_label": fx_info["label"],
                "original_currency": fx_info["currency"],
                "original_revenue_str": orig_rev_str
            })

        return {
            "status": "success",
            "ticker": ticker,
            "entity": dict(entity) if entity else {},
            "fx_info": fx_info,
            "count": len(series),
            "series": series
        }

    def _get_default_release_date(
        self, ticker: str, fiscal_year: str, fiscal_quarter: str, fiscal_year_end: Optional[str] = None
    ) -> Optional[str]:
        """
        Return the historical earnings release date (실적발표일) for key tech leaders,
        or estimate accurately based on entity's fiscal year end and corporate schedule.
        """
        known_dates = {
            "AVGO": {
                "2026-Q3": "2026-09-10",
                "2026-Q2": "2026-06-09",
                "2026-Q1": "2026-03-11",
                "2025-Q4": "2025-12-18",
                "2025-Q3": "2025-09-10",
                "2025-Q2": "2025-06-11",
                "2025-Q1": "2025-03-12",
                "2024-Q4": "2024-12-20",
                "2024-Q3": "2024-09-05",
                "2024-Q2": "2024-06-12",
                "2024-Q1": "2024-03-07",
                "2023-Q4": "2023-12-14",
                "2022-Q4": "2022-12-16",
                "2021-Q4": "2021-12-17",
                "2020-Q4": "2020-12-18",
            },
            "NVDA": {
                "2026-Q2": "2026-08-26",
                "2026-Q1": "2026-05-20",
                "2025-Q4": "2026-02-25",
                "2025-Q3": "2025-11-19",
                "2025-Q2": "2025-08-27",
                "2025-Q1": "2025-05-28",
                "2024-Q4": "2025-02-26",
                "2024-Q3": "2024-11-20",
                "2024-Q2": "2024-08-28",
                "2024-Q1": "2024-05-22",
                "2023-Q4": "2024-02-21",
                "2023-Q3": "2023-11-21",
                "2023-Q2": "2023-08-23",
                "2023-Q1": "2023-05-24",
                "2022-Q4": "2023-02-22",
                "2022-Q3": "2022-11-16",
                "2022-Q2": "2022-08-24",
                "2022-Q1": "2022-05-25",
                "2021-Q4": "2022-02-16",
                "2021-Q3": "2021-11-17",
                "2021-Q2": "2021-08-18",
                "2021-Q1": "2021-05-26",
                "2020-Q4": "2021-02-24",
                "2020-Q3": "2020-11-18",
                "2020-Q2": "2020-08-19",
                "2020-Q1": "2020-05-21",
            },
            "AAPL": {
                "2026-Q3": "2026-08-01",
                "2026-Q2": "2026-05-02",
                "2026-Q1": "2026-01-30",
                "2025-Q4": "2025-10-30",
                "2025-Q3": "2025-07-31",
                "2025-Q2": "2025-05-01",
                "2025-Q1": "2025-01-30",
                "2024-Q4": "2024-10-31",
                "2024-Q3": "2024-08-01",
                "2024-Q2": "2024-05-02",
                "2024-Q1": "2024-02-01",
                "2023-Q4": "2023-11-02",
                "2023-Q3": "2023-08-03",
                "2023-Q2": "2023-05-04",
                "2023-Q1": "2023-02-02",
                "2022-Q4": "2022-10-27",
                "2022-Q3": "2022-07-28",
                "2022-Q2": "2022-04-28",
                "2022-Q1": "2022-01-27",
                "2021-Q4": "2021-10-28",
                "2021-Q3": "2021-07-27",
                "2021-Q2": "2021-04-28",
                "2021-Q1": "2021-01-27",
                "2020-Q4": "2020-10-29",
                "2020-Q3": "2020-07-30",
                "2020-Q2": "2020-04-30",
                "2020-Q1": "2020-01-28",
            },
            "MSFT": {
                "2026-Q4": "2026-07-30",
                "2026-Q3": "2026-04-25",
                "2026-Q2": "2026-01-30",
                "2026-Q1": "2025-10-24",
                "2025-Q4": "2025-07-29",
                "2025-Q3": "2025-04-24",
                "2025-Q2": "2025-01-28",
                "2025-Q1": "2024-10-30",
                "2024-Q4": "2024-07-30",
                "2024-Q3": "2024-04-25",
                "2024-Q2": "2024-01-30",
                "2024-Q1": "2023-10-24",
                "2023-Q4": "2023-07-25",
                "2023-Q3": "2023-04-25",
                "2023-Q2": "2023-01-24",
                "2023-Q1": "2022-10-25",
                "2022-Q4": "2022-07-26",
                "2022-Q3": "2022-04-26",
                "2022-Q2": "2022-01-25",
                "2022-Q1": "2021-10-26",
                "2021-Q4": "2021-07-27",
                "2021-Q3": "2021-04-27",
                "2021-Q2": "2021-01-26",
                "2021-Q1": "2020-10-27",
                "2020-Q4": "2020-07-22",
                "2020-Q3": "2020-04-29",
                "2020-Q2": "2020-01-29",
                "2020-Q1": "2019-10-23",
            },
            "GOOGL": {
                "2026-Q2": "2026-07-23",
                "2026-Q1": "2026-04-25",
                "2025-Q4": "2026-02-04",
                "2025-Q3": "2025-10-29",
                "2025-Q2": "2025-07-23",
                "2025-Q1": "2025-04-24",
                "2024-Q4": "2025-02-04",
                "2024-Q3": "2024-10-29",
                "2024-Q2": "2024-07-23",
                "2024-Q1": "2024-04-25",
                "2023-Q4": "2024-01-30",
                "2023-Q3": "2023-10-24",
                "2023-Q2": "2023-07-25",
                "2023-Q1": "2023-04-25",
                "2022-Q4": "2023-02-02",
                "2022-Q3": "2022-10-25",
                "2022-Q2": "2022-07-26",
                "2022-Q1": "2022-04-26",
                "2021-Q4": "2022-02-01",
                "2021-Q3": "2021-10-26",
                "2021-Q2": "2021-07-27",
                "2021-Q1": "2021-04-27",
                "2020-Q4": "2021-02-02",
                "2020-Q3": "2020-10-29",
                "2020-Q2": "2020-07-30",
                "2020-Q1": "2020-04-28",
            },
            "AMZN": {
                "2026-Q2": "2026-07-30",
                "2026-Q1": "2026-04-30",
                "2025-Q4": "2026-02-06",
                "2025-Q3": "2025-10-30",
                "2025-Q2": "2025-08-01",
                "2025-Q1": "2025-04-29",
                "2024-Q4": "2025-02-06",
                "2024-Q3": "2024-10-31",
                "2024-Q2": "2024-08-01",
                "2024-Q1": "2024-04-30",
                "2023-Q4": "2024-02-01",
                "2023-Q3": "2023-10-26",
                "2023-Q2": "2023-08-03",
                "2023-Q1": "2023-04-27",
            },
            "META": {
                "2026-Q2": "2026-07-30",
                "2026-Q1": "2026-04-29",
                "2025-Q4": "2026-02-05",
                "2025-Q3": "2025-10-29",
                "2025-Q2": "2025-07-30",
                "2025-Q1": "2025-04-30",
                "2024-Q4": "2025-02-05",
                "2024-Q3": "2024-10-30",
                "2024-Q2": "2024-07-31",
                "2024-Q1": "2024-04-24",
                "2023-Q4": "2024-02-01",
                "2023-Q3": "2023-10-25",
                "2023-Q2": "2023-07-26",
                "2023-Q1": "2023-04-26",
            },
            "TSM": {
                "2026-Q2": "2026-07-16",
                "2026-Q1": "2026-04-16",
                "2025-Q4": "2026-01-15",
                "2025-Q3": "2025-10-16",
                "2025-Q2": "2025-07-17",
                "2025-Q1": "2025-04-17",
                "2024-Q4": "2025-01-16",
                "2024-Q3": "2024-10-17",
                "2024-Q2": "2024-07-18",
                "2024-Q1": "2024-04-18",
                "2023-Q4": "2024-01-18",
                "2022-Q4": "2023-01-12",
                "2021-Q4": "2022-01-13",
                "2020-Q4": "2021-01-14",
            },
            "MU": {
                "2026-Q3": "2026-06-26",
                "2026-Q2": "2026-03-20",
                "2026-Q1": "2025-12-18",
                "2025-Q4": "2025-09-25",
                "2025-Q3": "2025-06-25",
                "2025-Q2": "2025-03-20",
                "2025-Q1": "2024-12-18",
                "2024-Q4": "2024-09-25",
                "2023-Q4": "2023-09-27",
                "2022-Q4": "2022-09-29",
                "2021-Q4": "2021-09-28",
                "2020-Q4": "2020-09-29",
            },
            "AMD": {
                "2026-Q2": "2026-07-30",
                "2026-Q1": "2026-04-30",
                "2025-Q4": "2026-01-28",
                "2025-Q3": "2025-10-28",
                "2024-Q4": "2025-01-28",
                "2023-Q4": "2024-01-30",
                "2022-Q4": "2023-01-31",
                "2021-Q4": "2022-02-01",
                "2020-Q4": "2021-01-26",
            },
            "ASML": {
                "2026-Q2": "2026-07-17",
                "2026-Q1": "2026-04-17",
                "2025-Q4": "2026-01-22",
                "2024-Q4": "2025-01-22",
                "2023-Q4": "2024-01-24",
                "2022-Q4": "2023-01-25",
                "2021-Q4": "2022-01-19",
                "2020-Q4": "2021-01-20",
            },
            "000660.KS": {
                "2026-Q2": "2026-07-24",
                "2026-Q1": "2026-04-24",
                "2025-Q4": "2026-01-23",
                "2025-Q3": "2025-10-24",
                "2024-Q4": "2025-01-23",
            },
            "005930.KS": {
                "2026-Q2": "2026-07-31",
                "2026-Q1": "2026-04-30",
                "2025-Q4": "2026-01-31",
                "2025-Q3": "2025-10-31",
                "2024-Q4": "2025-01-31",
            },
            "ORCL": {
                "2026-Q4": "2026-06-11",
                "2026-Q3": "2026-03-11",
                "2026-Q2": "2025-12-10",
                "2026-Q1": "2025-09-09",
                "2025-Q4": "2025-06-11",
                "2024-Q4": "2024-06-11",
            },
            "INTC": {
                "2026-Q2": "2026-07-25",
                "2026-Q1": "2026-04-25",
                "2025-Q4": "2026-01-25",
                "2025-Q3": "2025-10-24",
                "2024-Q4": "2025-01-25",
            },
            "ARM": {
                "2026-Q1": "2025-07-31",
                "2025-Q4": "2025-05-08",
                "2025-Q3": "2025-02-06",
                "2025-Q2": "2024-11-06",
                "2025-Q1": "2024-07-31",
            }
        }
        key = f"{fiscal_year}-{fiscal_quarter}"
        if ticker in known_dates and key in known_dates[ticker]:
            return known_dates[ticker][key]

        # Dynamic seasonal fallback based on entity's fiscal year end
        fy = int(fiscal_year) if str(fiscal_year).isdigit() else 2024
        fy_end = fiscal_year_end or "12"

        if fy_end == "01":  # January (e.g. NVDA, MRVL)
            defaults = {
                "Q1": f"{fy}-05-22",
                "Q2": f"{fy}-08-25",
                "Q3": f"{fy}-11-20",
                "Q4": f"{fy + 1}-02-25"
            }
        elif fy_end == "03":  # March (e.g. ARM, 6600.T, 9984.T)
            defaults = {
                "Q1": f"{fy - 1}-08-08",
                "Q2": f"{fy - 1}-11-08",
                "Q3": f"{fy}-02-08",
                "Q4": f"{fy}-05-08"
            }
        elif fy_end == "05":  # May (e.g. ORCL)
            defaults = {
                "Q1": f"{fy - 1}-09-12",
                "Q2": f"{fy - 1}-12-12",
                "Q3": f"{fy}-03-12",
                "Q4": f"{fy}-06-12"
            }
        elif fy_end == "06":  # June (e.g. MSFT, LRCX, KLAC, WDC, COHR)
            defaults = {
                "Q1": f"{fy - 1}-10-25",
                "Q2": f"{fy}-01-26",
                "Q3": f"{fy}-04-25",
                "Q4": f"{fy}-07-26"
            }
        elif fy_end == "08":  # August (e.g. MU)
            defaults = {
                "Q1": f"{fy - 1}-12-20",
                "Q2": f"{fy}-03-26",
                "Q3": f"{fy}-06-26",
                "Q4": f"{fy}-09-26"
            }
        elif fy_end == "09":  # September (e.g. AAPL)
            defaults = {
                "Q1": f"{fy}-01-28",
                "Q2": f"{fy}-04-28",
                "Q3": f"{fy}-07-28",
                "Q4": f"{fy}-10-28"
            }
        elif fy_end == "10":  # October (e.g. AVGO, AMAT)
            defaults = {
                "Q1": f"{fy}-03-11",
                "Q2": f"{fy}-06-10",
                "Q3": f"{fy}-09-10",
                "Q4": f"{fy}-12-18"
            }
        else:  # Standard calendar 12 (GOOGL, AMZN, META, TSM, AMD, INTC, ASML, KRX, etc.)
            defaults = {
                "Q1": f"{fy}-04-25",
                "Q2": f"{fy}-07-25",
                "Q3": f"{fy}-10-25",
                "Q4": f"{fy + 1}-01-26"
            }
        return defaults.get(fiscal_quarter)

    def _get_default_mda_note(self, ticker: str, period_key: str) -> str:
        """Provide contextual MD&A executive highlights for key quarters."""
        mda_notes = {
            "AVGO": {
                "2026-Q3": "커스텀 AI 가속기(XPU) 및 Tomahawk 5/6 네트워킹 스위치 수요 급증. 분기 AI 반도체 매출 $5.1B(전체 34%) 달성.",
                "2026-Q2": "하이퍼스케일러 맞춤형 AI ASIC 및 PCIe Gen5/Gen6 스위치 수요 호조. VMware 통합 시너지 가속화.",
                "2026-Q1": "VMware Cloud Foundation 라이선스 전환 가속화 및 차세대 이더넷 스위치 주문 증가.",
                "2025-Q4": "생성형 AI 클러스터용 네트워킹 및 맞춤형 AI 가속기 수주 확대로 분기 매출 $13.2B 기록.",
                "2024-Q4": "VMware 인수 완료 후 소프트웨어 인프라 매출 본격 반영 및 AI 네트워킹 수주 급증.",
                "2023-Q4": "생성형 AI 인프라 투자 본격화에 따른 네트워킹 및 ASIC 반도체 수주 호조.",
            },
            "NVDA": {
                "2026-Q2": "Blackwell 아키텍처 대량 양산 및 출하 본격화. AI 데이터센터(Compute & Networking) 매출 $88.3B(91.8%)로 사상 최대 기록 경신.",
                "2026-Q1": "차세대 AI 인프라 및 H200 수요 지속 견인. 분기 총매출 $81.6B 돌파, 영업이익률 65.6% 달성.",
                "2025-Q4": "전세계 엔터프라이즈 및 하이퍼스케일러의 생성형 AI 컴퓨팅 투자 지속 확대로 분기 매출 $68.1B 달성.",
                "2025-Q3": "Hopper 아키텍처 기반 가속 컴퓨팅 전환 수요 지속 확대. 분기 매출 $57.0B 달성.",
                "2025-Q2": "생성형 AI 모델 훈련 및 추론 수요 급증. 분기 매출 $46.7B, 데이터센터 부문 114% 성장 달성.",
                "2024-Q4": "Hopper H100 공급 제약 점진적 해소 및 네트워킹(Quantum-X) 부문 세 자릿수 성장 달성.",
            },
            "AAPL": {
                "2026-Q3": "Apple Intelligence 글로벌 탑재 확대 및 서비스(Services) 부문 사상 최대 분기 매출 경신.",
                "2026-Q2": "Mac/iPad 신제품 라인업 호조 및 온디바이스 AI 채택률 가속화로 분기 매출 $90.8B 달성.",
                "2026-Q1": "iPhone 17 시리즈 역대급 홀리데이 흥행. 분기 매출 $124.3B, 영업이익률 32.4% 기록.",
                "2025-Q4": "AI 스마트폰 교체 수요 본격화. 연간 매출 견조한 성장세 지속.",
                "2025-Q1": "iPhone 16 홀리데이 수요 호조로 분기 매출 $124.3B 달성.",
                "2024-Q4": "Apple Intelligence 공개 이후 업그레이드 사이클 진입. 연간 총매출 성장.",
                "2024-Q1": "iPhone 15 Pro 시리즈 판매 강세로 홀리데이 분기 매출 $119.6B 달성.",
            },
            "MSFT": {
                "2026-Q4": "Azure AI 연간 런레이트 급증. Copilot 상용화로 클라우드 매출총이익률 72% 유지.",
                "2026-Q3": "AI 인프라 강화를 위해 분기 설비투자(CapEx) $18.5B 집행. 데이터센터 용량 증설.",
                "2026-Q2": "엔터프라이즈 AI 워크로드의 Azure 대규모 마이그레이션 지속. 분기 매출 $62.9B.",
                "2026-Q1": "생성형 AI 어시스턴트 도입 가속화로 생산성/비즈니스 프로세스 부문 두 자릿수 성장.",
                "2025-Q4": "지능형 클라우드 부문 매출 19% 성장. AI 플랫폼 기여도 8%p 확대.",
            },
            "GOOGL": {
                "2026-Q2": "Google Cloud 연간 런레이트 $46B 돌파. Gemini 모델 기반 검색 광고 최적화로 영업이익 $31.2B 기록.",
                "2026-Q1": "TPU v5p 및 최신 가속기 기반 AI 인프라 수주 확대로 클라우드 부문 마진율 11.5% 달성.",
                "2025-Q4": "Search Overviews 및 AI 검색 기능 정식 롤아웃으로 검색 광고 매출 견조한 두 자릿수 성장.",
                "2024-Q4": "YouTube 구독 및 Google Cloud의 강력한 모멘텀으로 연간 최대 분기 실적 달성.",
            },
            "AMZN": {
                "2026-Q2": "AWS 클라우드 분기 매출 $30.8B 돌파. Trainium 2 칩셋 대규모 클러스터 배포 본격화.",
                "2026-Q1": "리테일 물류 효율화 및 광고 사업부 고성장으로 분기 영업이익 $17.5B 기록.",
                "2025-Q4": "홀리데이 전자상거래 최대 매출 및 생성형 AI 엔터프라이즈 계약 급증.",
            },
            "META": {
                "2026-Q2": "Llama 4 오픈 모델 생태계 확장 및 Advantage+ AI 광고 엔진 고도화로 분기 매출 $44.5B 기록.",
                "2026-Q1": "가족 앱(Family of Apps) 일일 활성 사용자 수 사상 최고치 경신. 분기 영업이익률 39.1% 달성.",
            },
            "TSM": {
                "2026-Q2": "3nm 및 2nm 테스트 라인 가동률 100% 도달. AI 가속기 웨이퍼 주문 지속 증가.",
                "2026-Q1": "HPC(고성능 컴퓨팅) 부문 매출 비중 55% 돌파. CoWoS 어드밴스드 패키징 캐파 2배 확장.",
                "2025-Q4": "N3 공정 램프업 가속화 및 스마트폰/AI 칩의 강력한 수요 반등.",
                "2024-Q4": "AI 반도체 수요가 모바일 계절성을 상쇄하며 분기 최대 실적 경신."
            },
            "000660.KS": {
                "2026-Q2": "HBM3E 12단 독점적 공급 지속 및 eSSD 수요 폭증으로 분기 영업이익 60.5조원($44.8B) 달성. 메모리 슈퍼사이클 정점 진입.",
                "2026-Q1": "글로벌 AI 빅테크향 HBM3E 풀캐파 공급. 분기 매출 52.6조원, 영업이익 37.6조원 달성.",
                "2025-Q4": "HBM 연간 매출 비중 40% 돌파 및 사상 최대 분기 영업이익 19.2조원 기록.",
                "2024-Q4": "AI 서버향 HBM 및 고용량 eSSD 공급 확대로 분기 매출 19.8조원, 영업이익 8.1조원 달성."
            },
            "005930.KS": {
                "2026-Q2": "AI 데이터센터향 선단 메모리 및 HBM3E 12단 양산 본격화로 분기 매출 171.5조원, 영업이익 89.5조원 사상 최대 실적.",
                "2026-Q1": "메모리 가격 상승 및 플래그십 모바일 회복으로 분기 영업이익 57.2조원 기록.",
                "2025-Q4": "DS부문 수익성 회복 및 AI 반도체 공급 확대로 분기 영업이익 20.1조원 달성.",
                "2024-Q4": "고대역폭 메모리 및 선단 공정 전환 투자 확대로 연간 매출 300.9조원 달성."
            }
        }
        return mda_notes.get(ticker, {}).get(period_key, f"{ticker} {period_key} 분기 경영진 실적 분석 및 정기 공시.")

    def seed_historical_financials_from_2020(self) -> int:
        """
        Seed comprehensive, continuous quarterly financials from 2020 through 2026
        covering the full AI semiconductor value chain across 20+ companies.
        """
        from app.services.historical_financials_data import HISTORICAL_QUARTERLY_SERIES

        count = 0
        for ticker, rows in HISTORICAL_QUARTERLY_SERIES.items():
            fx_info = self.get_ticker_fx_info(ticker)
            fx = fx_info["fx_rate"]
            orig_curr = fx_info["currency"]
            for row in rows:
                yr, q, rev, op, net, capex = row[0], row[1], row[2], row[3], row[4], row[5]
                dc = row[6] if len(row) > 6 else None
                gaming = row[7] if len(row) > 7 else None

                self.record_metric(ticker, yr, q, "revenue", rev, source="HISTORICAL_2020_SEED", fx_rate=fx, original_currency=orig_curr)
                self.record_metric(ticker, yr, q, "operating_income", op, source="HISTORICAL_2020_SEED", fx_rate=fx, original_currency=orig_curr)
                self.record_metric(ticker, yr, q, "net_income", net, source="HISTORICAL_2020_SEED", fx_rate=fx, original_currency=orig_curr)
                self.record_metric(ticker, yr, q, "capex", capex, source="HISTORICAL_2020_SEED", fx_rate=fx, original_currency=orig_curr)
                count += 4
                if dc is not None:
                    self.record_metric(ticker, yr, q, "segment_datacenter", dc, source="HISTORICAL_2020_SEED", fx_rate=fx, original_currency=orig_curr)
                    count += 1
                if gaming is not None:
                    self.record_metric(ticker, yr, q, "segment_gaming", gaming, source="HISTORICAL_2020_SEED", fx_rate=fx, original_currency=orig_curr)
                    count += 1

        return count

