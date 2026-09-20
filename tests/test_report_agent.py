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
    assert "opencode" in status
    assert isinstance(status["gemini"]["available"], bool)
    assert isinstance(status["ollama"]["available"], bool)
    assert isinstance(status["opencode"]["available"], bool)
    assert "gemini-3.8-flash" in status["gemini"]["models"]

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
    # Check operating income is included
    if res["series"]:
        assert "operating_income_usd_m" in res["series"][0]

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
    assert "gpu_rental_latest" in res
    assert isinstance(res["memory_spot_latest"], list)
    assert isinstance(res["kr_semiconductor_export_latest"], list)
    assert isinstance(res["gpu_rental_latest"], list)

def test_generate_report_gemini_38_mock():
    agent = ReportAgent(engine="gemini", model_name="gemini-3.8-flash")
    assert agent.model_name == "gemini-3.8-flash"
    
    mock_markdown = "# NVDA Gemini 3.8 Report\n\n## 1. Executive Summary\nUltra fast synthesis."
    mock_tools = [{"tool": "get_quarterly_financials", "arguments": {"ticker": "NVDA"}}]

    with patch.object(agent, "_run_gemini_agent", return_value=(mock_markdown, mock_tools)):
        result = agent.generate_report(
            target_ticker="NVDA",
            peer_tickers=["000660.KS"],
            chapters=["1. Executive Summary"],
            user_notes="Check Blackwell demand",
            tone_style="analyst"
        )
        assert result["status"] == "success"
        assert result["model"] == "gemini-3.8-flash"
        assert result["engine"] == "gemini"

def test_generate_report_opencode_mock():
    agent = ReportAgent(engine="opencode", model_name="opencode/muse-spark-1.3-contributor-free")
    assert agent.model_name == "opencode/muse-spark-1.3-contributor-free"
    
    mock_markdown = "# Muse Spark Report\n\n## 1. Executive Summary\nOpenCode generated report."
    mock_tools = [
        {"tool": "get_quarterly_financials", "arguments": {"ticker": "NVDA"}},
        {"tool": "get_gpu_rental_prices", "arguments": {"gpu_model": "H100"}}
    ]

    with patch.object(agent, "_run_opencode_agent", return_value=(mock_markdown, mock_tools)):
        result = agent.generate_report(
            target_ticker="NVDA",
            peer_tickers=["000660.KS"],
            chapters=["1. Executive Summary"],
            user_notes="Muse Spark prompt test",
            tone_style="analyst"
        )
        assert result["status"] == "success"
        assert result["engine"] == "opencode"
        assert result["model"] == "opencode/muse-spark-1.3-contributor-free"
        assert len(result["tools_used"]) == 2
