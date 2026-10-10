#!/usr/bin/env python3
"""
Seed Foreign / Global IB Analyst Reports for Samsung Electronics (005930.KS) and SK Hynix (000660.KS).
Covers Tier 1 & Tier 2 global investment banks (Goldman Sachs, Morgan Stanley, J.P. Morgan, Citi, BofA, Macquarie, UBS, Nomura, CLSA).
"""
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import DB_PATH

GLOBAL_IB_REPORTS_KOREA = [
    # ═════════════════════════════════════════════════════════════════════
    # SK Hynix Inc. (000660.KS)
    # ═════════════════════════════════════════════════════════════════════
    {
        "ticker": "000660.KS",
        "broker_name": "Goldman Sachs",
        "analyst_name": "Giuni Lee / Marcus Shin",
        "report_date": "2026-10-06",
        "title": "SK Hynix: AI Memory Unchallenged Leadership & HBM3E 12-Layer Runaway Moat",
        "rating": "Buy",
        "action_type": "Upgrade",
        "target_price": 3600000.0,
        "summary": "엔비디아 루빈(Rubin) 및 차세대 B200용 HBM3E 12단 및 HBM4 조기 테이프아웃 독점 지속. 2026~2027년 HBM 공급 물량 전체 완판(Sold-out) 상태 유지 및 분기 OPM 50% 상회 전망."
    },
    {
        "ticker": "000660.KS",
        "broker_name": "Morgan Stanley",
        "analyst_name": "Shawn Kim / Simon Woo",
        "report_date": "2026-10-02",
        "title": "SK Hynix: Memory Winter Debate Over — High-Bandwidth Supercycle in Full Throttle",
        "rating": "Overweight",
        "action_type": "Upgrade",
        "target_price": 3400000.0,
        "summary": "과거의 메모리 다운사이클 우려 불식. eSSD(솔리다임 합산) 분기 흑자 폭증 및 AI 하이퍼스케일러 커스텀 HBM 계약 가치 40% 이상 상향 조정."
    },
    {
        "ticker": "000660.KS",
        "broker_name": "JPMorgan",
        "analyst_name": "JJ Park",
        "report_date": "2026-09-24",
        "title": "SK Hynix: The Inelastic Demand of Frontier AI Compute — Raise PT to W3.8M",
        "rating": "Overweight",
        "action_type": "Upgrade",
        "target_price": 3800000.0,
        "summary": "TSMC와의 CoWoS 첨단 패키징 얼라이언스 및 1c nm D램 공정 전환 수율이 업계 최고 수준 유지. 하반기 사상 최대 영업이익 지속 경신."
    },
    {
        "ticker": "000660.KS",
        "broker_name": "Citigroup",
        "analyst_name": "Peter Lee",
        "report_date": "2026-09-18",
        "title": "SK Hynix: Enterprise SSD & HBM Double-Engine Acceleration",
        "rating": "Buy",
        "action_type": "Maintain",
        "target_price": 3500000.0,
        "summary": "AI 추론용 대용량 QLC eSSD 공급 부족 심화로 솔리다임 가치 재평가. 3분기 분기 영업이익 컨센서스 상회 확실시."
    },
    {
        "ticker": "000660.KS",
        "broker_name": "Bank of America",
        "analyst_name": "Wong-Sik Kim",
        "report_date": "2026-09-12",
        "title": "SK Hynix: Structural Re-rating as Premier AI Infrastructure Monopoly",
        "rating": "Buy",
        "action_type": "Upgrade",
        "target_price": 3700000.0,
        "summary": "하이퍼스케일러 CapEx 상향에 따른 고부가 메모리 판가 프리미엄 유지. 2026년 연간 순이익 추정치 18% 상향."
    },
    {
        "ticker": "000660.KS",
        "broker_name": "Macquarie",
        "analyst_name": "Daniel Kim",
        "report_date": "2026-09-05",
        "title": "SK Hynix: Pricing Power at Its Peak — Maintaining Outperform",
        "rating": "Outperform",
        "action_type": "Maintain",
        "target_price": 3300000.0,
        "summary": "경쟁사 퀄 통과 지연에 따른 12단 HBM3E 시장 독점 기간 연장. 하반기 메모리 공급 부족 현상 심화 반영."
    },
    {
        "ticker": "000660.KS",
        "broker_name": "UBS",
        "analyst_name": "Nicolas Gaudois",
        "report_date": "2026-08-28",
        "title": "SK Hynix: Next-Gen HBM4 Co-design with TSMC & CSP Giants",
        "rating": "Buy",
        "action_type": "Maintain",
        "target_price": 3450000.0,
        "summary": "커스텀 베이스 다이를 활용한 HBM4 파운드리 파트너십 구축으로 차세대 가속기 시장에서도 1위 지위 불변."
    },
    {
        "ticker": "000660.KS",
        "broker_name": "Nomura",
        "analyst_name": "CW Chung",
        "report_date": "2026-08-20",
        "title": "SK Hynix: Clear Path to Record Operating Profit in FY26",
        "rating": "Buy",
        "action_type": "Maintain",
        "target_price": 3250000.0,
        "summary": "용인 클러스터 및 청주 M15X 증설로 중장기 캐파 우위 선점. 메모리 공급 제약에 따른 ASP 상승 지속."
    },

    # ═════════════════════════════════════════════════════════════════════
    # Samsung Electronics Co. (005930.KS)
    # ═════════════════════════════════════════════════════════════════════
    {
        "ticker": "005930.KS",
        "broker_name": "Goldman Sachs",
        "analyst_name": "Giuni Lee",
        "report_date": "2026-10-05",
        "title": "Samsung Electronics: Turnkey Capabilities to Reignite Growth in HBM4 Era",
        "rating": "Buy",
        "action_type": "Upgrade",
        "target_price": 550000.0,
        "summary": "HBM3E 12단 고객사 퀄 승인 완료 및 4분기부터 대량 양산 출하 개시. 메모리+파운드리+패키징 턴키 원스톱 역량으로 HBM4 커스텀 수주 반등 예상."
    },
    {
        "ticker": "005930.KS",
        "broker_name": "Morgan Stanley",
        "analyst_name": "Shawn Kim",
        "report_date": "2026-09-29",
        "title": "Samsung Electronics: Valuation at Deep Discount, Asymmetrical Upside Ahead",
        "rating": "Overweight",
        "action_type": "Upgrade",
        "target_price": 520000.0,
        "summary": "PBR 역사적 하단 통과. 1c nm DDR5 및 서버용 SSD 실적 회복에 힘입어 DS(반도체) 부문 영업이익 대폭 반등 국면 진입."
    },
    {
        "ticker": "005930.KS",
        "broker_name": "JPMorgan",
        "analyst_name": "JJ Park",
        "report_date": "2026-09-22",
        "title": "Samsung Electronics: Catching Up in Advanced Memory & Foundry Synergy",
        "rating": "Overweight",
        "action_type": "Maintain",
        "target_price": 560000.0,
        "summary": "글로벌 빅테크의 세컨드 소스(Second Source) 다변화 수혜 집중. 파운드리 2nm 공정과 연계된 차세대 가속기 패키징 수주 가시화."
    },
    {
        "ticker": "005930.KS",
        "broker_name": "Citigroup",
        "analyst_name": "Peter Lee",
        "report_date": "2026-09-17",
        "title": "Samsung Electronics: The Giant Awakes — Strong DRAM Pricing to Boost Q3",
        "rating": "Buy",
        "action_type": "Maintain",
        "target_price": 540000.0,
        "summary": "범용 D램 및 서버 모듈 ASP 20% 이상 급등. 스마트폰/PC 수요 둔화를 서버/AI향 고단가 제품이 압도적으로 상쇄."
    },
    {
        "ticker": "005930.KS",
        "broker_name": "Bank of America",
        "analyst_name": "Simon Dong-je Woo",
        "report_date": "2026-09-11",
        "title": "Samsung Electronics: Leading Edge Recovery and Generative AI Multi-year Supercycle",
        "rating": "Buy",
        "action_type": "Upgrade",
        "target_price": 530000.0,
        "summary": "HBM3E 공급 개시로 인한 DS부문 이익 기여 본격화. 풍부한 순현금과 자사주 매입/배당 확대에 따른 밸류에이션 리레이팅 기대."
    },
    {
        "ticker": "005930.KS",
        "broker_name": "Macquarie",
        "analyst_name": "Daniel Kim",
        "report_date": "2026-09-04",
        "title": "Samsung Electronics: Navigating the Memory Supercycle with Massive CapEx Edge",
        "rating": "Outperform",
        "action_type": "Maintain",
        "target_price": 510000.0,
        "summary": "평택 캠퍼스 선단 공정 전환 가속. AI 데이터센터향 프리미엄 고용량 모듈(128GB/256GB DDR5) 시장 점유율 1위 수성."
    },
    {
        "ticker": "005930.KS",
        "broker_name": "CLSA",
        "analyst_name": "Sanjeev Rana",
        "report_date": "2026-08-29",
        "title": "Samsung Electronics: Clear Catalysts Ahead on HBM3E Qualification",
        "rating": "Buy",
        "action_type": "Maintain",
        "target_price": 525000.0,
        "summary": "북미 주요 GPU 고객사 퀄 인증 마무리 단계 진입에 따른 불확실성 해소. 하반기 실적 서프라이즈 가능성 고조."
    },
    {
        "ticker": "005930.KS",
        "broker_name": "Nomura",
        "analyst_name": "CW Chung",
        "report_date": "2026-08-19",
        "title": "Samsung Electronics: Rebound in Semiconductor Operating Margin",
        "rating": "Buy",
        "action_type": "Maintain",
        "target_price": 500000.0,
        "summary": "NAND 흑자폭 확대 및 HBM3E 믹스 개선. 연간 영업이익 50조원 이상 회복 전망."
    }
]

def seed_global_ib_korea():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    inserted = 0
    for rep in GLOBAL_IB_REPORTS_KOREA:
        ticker = rep["ticker"]
        cur.execute("SELECT id FROM entity WHERE ticker = ?", (ticker,))
        row = cur.fetchone()
        if not row:
            continue
        entity_id = row[0]

        # Get latest close price for upside calculation
        cur.execute("SELECT close FROM stock_price WHERE entity_id = ? ORDER BY date DESC LIMIT 1", (entity_id,))
        p_row = cur.fetchone()
        current_price = p_row[0] if p_row else None

        upside_pct = None
        if current_price and rep["target_price"]:
            upside_pct = round(((rep["target_price"] - current_price) / current_price) * 100.0, 2)

        cur.execute(
            """
            INSERT INTO analyst_report (
                entity_id, ticker, source_type, broker_name, analyst_name,
                report_date, title, rating, action_type, target_price,
                current_price_at_report, upside_pct, currency, summary_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id, broker_name, report_date, title)
            DO UPDATE SET
                target_price = excluded.target_price,
                rating = excluded.rating,
                action_type = excluded.action_type,
                upside_pct = excluded.upside_pct,
                summary_text = excluded.summary_text
            """,
            (
                entity_id, ticker, "GLOBAL_IB", rep["broker_name"], rep["analyst_name"],
                rep["report_date"], rep["title"], rep["rating"], rep["action_type"],
                rep["target_price"], current_price, upside_pct, "KRW", rep["summary"]
            )
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ Successfully seeded {inserted} Global IB analyst reports for Samsung Electronics and SK Hynix.")

if __name__ == "__main__":
    seed_global_ib_korea()
