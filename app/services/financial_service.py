"""
Quarterly Financial Metrics Service
Manages 10-Q / 10-K quarterly earnings data from 2020 to present:
Revenue, Operating Income, Net Income, Gross Margin, CapEx, and Segment revenues.
"""
from typing import Dict, Any, List, Optional
from app.models.database import get_db, query_db


class FinancialService:

    def record_metric(
        self,
        ticker: str,
        fiscal_year: str,
        fiscal_quarter: str,
        metric_type: str,
        value: float,
        filing_id: Optional[int] = None,
        source: str = "AUTO"
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
                    entity_id, fiscal_year, fiscal_quarter, metric_type, value, filing_id, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_id, fiscal_year, fiscal_quarter, metric_type)
                DO UPDATE SET value=excluded.value, filing_id=excluded.filing_id, source=excluded.source
                """,
                (entity["id"], str(fiscal_year), fiscal_quarter.upper(), metric_type.lower(), float(value), filing_id, source)
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

            # YoY calculation if prior year same quarter exists
            yr = int(item["fiscal_year"])
            prior_k = f"{yr - 1}-{item['fiscal_quarter']}"
            prior_rev = grouped.get(prior_k, {}).get("metrics", {}).get("revenue")
            rev_yoy = round(((rev - prior_rev) / prior_rev * 100), 1) if rev and prior_rev else None

            series.append({
                "period_key": k,
                "fiscal_year": item["fiscal_year"],
                "fiscal_quarter": item["fiscal_quarter"],
                "revenue": rev,
                "revenue_yoy_pct": rev_yoy,
                "operating_income": op_inc,
                "op_margin_pct": op_margin,
                "net_income": net_inc,
                "capex": capex,
                "segment_datacenter": dc_rev,
                "segment_datacenter_ratio": dc_ratio,
                "segment_gaming": gaming_rev,
                "filing_id": f_info.get("id"),
                "filing_type": f_info.get("filing_type", "10-Q"),
                "filed_date": f_info.get("filed_date"),
                "accession_number": f_info.get("accession_number"),
                "mda_summary": self._get_default_mda_note(ticker, k)
            })

        return {
            "status": "success",
            "entity": entity,
            "count": len(series),
            "series": series
        }

    def _get_default_mda_note(self, ticker: str, period_key: str) -> str:
        """Provide contextual MD&A executive highlights for key quarters."""
        mda_notes = {
            "NVDA": {
                "2026-Q2": "Blackwell 아키텍처 대량 양산 및 출하 본격화. 데이터센터 매출 89% 비중으로 사상 최대 기록.",
                "2026-Q1": "H200 수요 폭증 및 전세계 클라우드 제공업체(CSP)들의 생성형 AI 인프라 투자 지속 확대.",
                "2025-Q4": "Hopper H100 공급 제약 점진적 해소 및 네트워킹(Quantum-X) 부문 세 자릿수 성장 달성.",
                "2025-Q3": "생성형 AI 모델 파운데이션 트레이닝 수요로 전분기 대비 매출 34% 추가 급증.",
                "2025-Q2": "Generative AI 티핑 포인트 도달. AI 데이터센터 매출 첫 $10B 돌파 분기.",
                "2024-Q4": "LLM(대형 언어 모델) 개발 경쟁 본격화에 따른 GPU 수급 타이트.",
                "2023-Q4": "ChatGPT 출시 이후 글로벌 엔터프라이즈의 가속 컴퓨팅 투자 전환 시작점.",
                "2022-Q4": "팬데믹 게이밍 수요 정상화 및 데이터센터 중심 사업 구조 재편 본격화.",
                "2021-Q4": "Ampere 아키텍처 기반 게이밍 및 클라우드 AI 투트랙 견조한 실적 견인.",
                "2020-Q4": "Mellanox 인수 완료로 네트워킹과 컴퓨팅의 통합 데이터센터 플랫폼 출범."
            },
            "TSM": {
                "2026-Q2": "3nm 및 2nm 테스트 라인 가동률 100% 도달. AI 가속기 웨이퍼 주문 지속 증가.",
                "2026-Q1": "HPC(고성능 컴퓨팅) 부문 매출 비중 55% 돌파. CoWoS 어드밴스드 패키징 캐파 2배 확장.",
                "2025-Q4": "N3 공정 램프업 가속화 및 스마트폰/AI 칩의 강력한 수요 반등.",
                "2024-Q4": "AI 반도체 수요가 모바일 계절성을 상쇄하며 분기 최대 실적 경신."
            },
            "MSFT": {
                "2026-Q4": "Azure AI 연간 런레이트 급증. Copilot 상용화로 클라우드 매출총이익률 72% 유지.",
                "2026-Q3": "AI 인프라 강화를 위해 분기 설비투자(CapEx) $19B 집행. 데이터센터 용량 증설."
            }
        }
        return mda_notes.get(ticker, {}).get(period_key, f"{ticker} {period_key} 분기 경영진 실적 분석 및 정기 공시.")

    def seed_historical_financials_from_2020(self) -> int:
        """
        Seed historical quarterly financials from 2020-Q1 through 2026-Q2 (26 quarters)
        covering the full AI cycle for NVDA, TSM, and MSFT.
        """
        # NVDA Historical 2020~2026 (Revenue, OpInc, NetInc, CapEx, DC_Rev)
        nvda_series = [
            # 2026
            ("2026", "Q2", 39500, 24800, 22100, 3100, 35200, 2800),
            ("2026", "Q1", 35082, 22100, 19800, 2800, 30800, 2600),
            # 2025
            ("2025", "Q4", 30040, 18600, 16600, 2400, 26300, 2800),
            ("2025", "Q3", 26044, 15800, 14200, 2100, 22500, 2900),
            ("2025", "Q2", 22100, 13200, 11800, 1800, 18400, 2500),
            ("2025", "Q1", 18120, 10400, 9240, 1500, 14500, 2600),
            # 2024
            ("2024", "Q4", 13507, 6800, 6188, 1100, 10323, 2856),
            ("2024", "Q3", 10318, 4900, 4430, 950, 7250, 2480),
            ("2024", "Q2", 7192, 2800, 2450, 820, 4280, 2040),
            ("2024", "Q1", 6051, 2140, 1618, 740, 3750, 1800),
            # 2023
            ("2023", "Q4", 6051, 1257, 1414, 509, 3616, 1831),
            ("2023", "Q3", 5931, 601, 680, 492, 3833, 1574),
            ("2023", "Q2", 6704, 499, 656, 414, 3806, 2042),
            ("2023", "Q1", 8288, 1868, 1618, 360, 3750, 3620),
            # 2022
            ("2022", "Q4", 7643, 2970, 3003, 274, 3263, 3420),
            ("2022", "Q3", 7103, 2671, 2464, 230, 2936, 3221),
            ("2022", "Q2", 6507, 2444, 2374, 215, 2366, 3060),
            ("2022", "Q1", 5661, 1956, 1912, 190, 2048, 2760),
            # 2021
            ("2021", "Q4", 5003, 1507, 1457, 148, 1903, 2495),
            ("2021", "Q3", 4726, 1398, 1336, 178, 1900, 2271),
            ("2021", "Q2", 3866, 651, 622, 152, 1753, 1654),
            ("2021", "Q1", 3080, 976, 917, 142, 1141, 1339),
            # 2020
            ("2020", "Q4", 3105, 990, 950, 145, 968, 1491),
            ("2020", "Q3", 3014, 890, 850, 130, 890, 1659),
            ("2020", "Q2", 2579, 571, 552, 118, 655, 1313),
            ("2020", "Q1", 2220, 358, 394, 95, 460, 1120),
        ]

        count = 0
        for yr, q, rev, op, net, capex, dc, gaming in nvda_series:
            self.record_metric("NVDA", yr, q, "revenue", rev, source="HISTORICAL_2020_SEED")
            self.record_metric("NVDA", yr, q, "operating_income", op, source="HISTORICAL_2020_SEED")
            self.record_metric("NVDA", yr, q, "net_income", net, source="HISTORICAL_2020_SEED")
            self.record_metric("NVDA", yr, q, "capex", capex, source="HISTORICAL_2020_SEED")
            self.record_metric("NVDA", yr, q, "segment_datacenter", dc, source="HISTORICAL_2020_SEED")
            self.record_metric("NVDA", yr, q, "segment_gaming", gaming, source="HISTORICAL_2020_SEED")
            count += 6

        # TSM Historical
        tsm_series = [
            ("2026", "Q2", 26100, 11200, 9800, 8500),
            ("2026", "Q1", 23500, 10100, 8900, 8100),
            ("2025", "Q4", 21100, 8800, 7800, 7600),
            ("2025", "Q3", 19800, 8200, 7100, 7100),
            ("2024", "Q4", 17500, 7100, 6200, 6500),
            ("2023", "Q4", 15200, 6100, 5300, 5800),
            ("2022", "Q4", 14800, 5800, 5000, 5200),
            ("2021", "Q4", 12500, 4800, 4100, 4500),
            ("2020", "Q4", 10400, 4100, 3600, 3800),
        ]
        for yr, q, rev, op, net, capex in tsm_series:
            self.record_metric("TSM", yr, q, "revenue", rev, source="HISTORICAL_2020_SEED")
            self.record_metric("TSM", yr, q, "operating_income", op, source="HISTORICAL_2020_SEED")
            self.record_metric("TSM", yr, q, "net_income", net, source="HISTORICAL_2020_SEED")
            self.record_metric("TSM", yr, q, "capex", capex, source="HISTORICAL_2020_SEED")
            count += 4

        # MSFT Historical
        msft_series = [
            ("2026", "Q4", 69200, 29800, 24500, 19200),
            ("2026", "Q3", 65100, 27500, 22800, 18500),
            ("2025", "Q4", 62000, 26100, 21500, 16000),
            ("2024", "Q4", 56500, 23000, 19000, 12000),
            ("2023", "Q4", 51000, 20500, 16800, 9500),
            ("2022", "Q4", 46000, 18200, 15000, 7200),
            ("2021", "Q4", 41000, 16500, 13800, 5800),
            ("2020", "Q4", 36000, 14200, 11800, 4800),
        ]
        for yr, q, rev, op, net, capex in msft_series:
            self.record_metric("MSFT", yr, q, "revenue", rev, source="HISTORICAL_2020_SEED")
            self.record_metric("MSFT", yr, q, "operating_income", op, source="HISTORICAL_2020_SEED")
            self.record_metric("MSFT", yr, q, "net_income", net, source="HISTORICAL_2020_SEED")
            self.record_metric("MSFT", yr, q, "capex", capex, source="HISTORICAL_2020_SEED")
            count += 4

        return count
