"""
Tests for Intelligence Priorities 1 through 4:
1. FinTwit Q&A Agent & UI Endpoints
2. AI Report Studio IB Targets Context Injection
3. PDF Text Extraction & FTS5 Full-Text Search
4. Pre-Market Automated Scheduler
"""
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.services.fintwit_qa_agent import FinTwitQAAgent
from app.services.report_agent import ReportAgent
from app.services.pdf_indexer import PdfReportIndexer
from app.services.report_scheduler import ReportScheduler


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ─── 1순위 테스트: FinTwit Q&A ───

def test_priority1_fintwit_qa_agent():
    agent = FinTwitQAAgent()
    res = agent.ask_question(
        ticker="NVDA",
        user_query="골드만삭스와 시티의 최신 엔비디아 목표주가와 논거를 정리해줘"
    )
    assert "query_summary" in res
    assert "ib_actions" in res
    assert "market_sentiment" in res
    assert isinstance(res["ib_actions"], list)


def test_priority1_fintwit_api(client):
    resp = client.post(
        "/api/fintwit/ask",
        json={"ticker": "NVDA", "query": "골드만삭스 목표가"}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "data" in data


# ─── 2순위 테스트: ReportAgent IB 목표가 결합 ───

def test_priority2_report_agent_ib_targets():
    agent = ReportAgent()
    # Test tool definition presence
    tool_defs = agent.get_tool_definitions()
    tool_names = [t["name"] for t in tool_defs]
    assert "get_analyst_targets_and_reports" in tool_names

    # Test tool execution
    data = agent.execute_tool("get_analyst_targets_and_reports", {"ticker": "000660.KS"})
    assert data["ticker"] == "000660.KS"
    assert "consensus" in data
    assert "recent_reports" in data


# ─── 3순위 테스트: PDF FTS5 본문 전문 검색 ───

def test_priority3_pdf_fts5_search(client):
    # Search for known indexed keyword
    results = PdfReportIndexer.search_reports("자사주", ticker="000660.KS")
    assert isinstance(results, list)
    if results:
        first = results[0]
        assert "snippet" in first
        assert "fts-hl" in first["snippet"]
        assert first["ticker"] == "000660.KS"

    # API Endpoint check
    resp = client.get("/api/reports/search?q=자사주")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"


# ─── 4순위 테스트: 장전 자동 수집 스케줄러 ───

def test_priority4_scheduler_lifecycle(client):
    sch = ReportScheduler.get_instance()
    status = sch.get_status()
    assert "is_running" in status
    assert "next_kr_morning_run" in status
    assert "next_us_evening_run" in status

    # API status check
    resp = client.get("/api/scheduler/status")
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["status"] == "success"
    assert "current_time_kst" in json_data["data"]
