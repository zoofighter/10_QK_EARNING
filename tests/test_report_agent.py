import pytest
from unittest.mock import patch
from app.services.report_agent import (
    ReportAgent,
    REPORT_TEMPLATES,
)

def test_check_engine_status():
    status = ReportAgent.check_engine_status()
    assert "gemini" in status
    assert "ollama" in status
    assert isinstance(status["gemini"]["available"], bool)
    assert isinstance(status["ollama"]["available"], bool)

def test_report_templates():
    assert "cross_chain" in REPORT_TEMPLATES
    assert "beat_miss" in REPORT_TEMPLATES
    assert "executive_brief" in REPORT_TEMPLATES
    for key, tmpl in REPORT_TEMPLATES.items():
        assert "title" in tmpl
        assert "chapters" in tmpl
        assert len(tmpl["chapters"]) >= 3

def test_tool_get_quarterly_financials():
    res = ReportAgent.tool_get_quarterly_financials("NVDA", limit=2)
    assert res["ticker"] == "NVDA"
    assert "series" in res
    assert isinstance(res["series"], list)

def test_tool_search_transcripts():
    res = ReportAgent.tool_search_transcripts("NVDA", query="H100")
    assert res["ticker"] == "NVDA"
    assert "transcripts_found" in res
    assert "results" in res
    assert isinstance(res["results"], list)

def test_tool_get_consensus_surprise():
    res = ReportAgent.tool_get_consensus_surprise("NVDA")
    assert res["ticker"] == "NVDA"
    assert "records" in res
    assert isinstance(res["records"], list)

def test_tool_get_lead_indicators():
    res = ReportAgent.tool_get_lead_indicators()
    assert "memory_spot_latest" in res
    assert "kr_semiconductor_export_latest" in res
    assert isinstance(res["memory_spot_latest"], list)
    assert isinstance(res["kr_semiconductor_export_latest"], list)

def test_generate_report_gemini_mock():
    agent = ReportAgent(engine="gemini")
    
    mock_markdown = "# NVDA vs HBM Peer Report\n\n## 1. Executive Summary\nStrong growth."
    mock_tools = [{"tool": "get_quarterly_financials", "arguments": {"ticker": "NVDA"}}]

    with patch.object(agent, "_run_gemini_agent", return_value=(mock_markdown, mock_tools)):
        result = agent.generate_report(
            target_ticker="NVDA",
            peer_tickers=["000660.KS"],
            chapters=["1. Executive Summary"],
            user_notes="Check HBM3E supply",
            tone_style="analyst"
        )
        assert result["status"] == "success"
        assert result["report_markdown"].startswith("# NVDA vs HBM Peer Report")
        assert len(result["tools_used"]) == 1
        assert result["engine"] == "gemini"
