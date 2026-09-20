import pytest
from app import create_app
from app.services.gpu_price_collector import GpuPriceCollector, GPU_MODELS, PROVIDER_QUOTATIONS
from app.services.report_agent import ReportAgent

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_gpu_price_collector_seeding_and_summary():
    collector = GpuPriceCollector()
    seeded = collector.seed_gpu_rental_history()
    assert seeded > 0

    summary = collector.get_latest_summary()
    assert summary["status"] == "success"
    assert "H100" in summary["kpis"]
    assert "H200" in summary["kpis"]
    assert "B200" in summary["kpis"]
    assert "A100" in summary["kpis"]

    h100_kpi = summary["kpis"]["H100"]
    assert h100_kpi["current_price"] > 0
    assert h100_kpi["unit"] == "USD/hr"
    assert len(summary["providers"]) >= 5

def test_gpu_price_history():
    collector = GpuPriceCollector()
    history_res = collector.get_price_history("H100", limit=30)
    assert history_res["status"] == "success"
    assert history_res["model_key"] == "H100"
    assert len(history_res["history"]) > 0

    # Ensure price points have date, value, unit
    p0 = history_res["history"][0]
    assert "date" in p0
    assert "value" in p0
    assert p0["unit"] == "USD/hr"

def test_api_gpu_endpoints(client):
    # Test seed endpoint
    seed_res = client.post("/api/gpu/seed")
    assert seed_res.status_code == 200
    seed_data = seed_res.get_json()
    assert seed_data["status"] == "success"
    assert seed_data["seeded_count"] > 0

    # Test latest prices endpoint
    prices_res = client.get("/api/gpu/prices")
    assert prices_res.status_code == 200
    prices_data = prices_res.get_json()
    assert prices_data["status"] == "success"
    assert "H100" in prices_data["kpis"]

    # Test history endpoint
    hist_res = client.get("/api/gpu/history?model=H100&limit=10")
    assert hist_res.status_code == 200
    hist_data = hist_res.get_json()
    assert hist_data["status"] == "success"
    assert hist_data["model_key"] == "H100"
    assert len(hist_data["history"]) > 0

def test_report_agent_gpu_tool():
    agent = ReportAgent(engine="gemini")
    
    # Check tool is listed in schema
    tools = agent.get_tool_definitions()
    tool_names = [t["name"] for t in tools]
    assert "get_gpu_rental_prices" in tool_names

    # Test static method directly
    tool_res = ReportAgent.tool_get_gpu_rental_prices("H100")
    assert tool_res["requested_model"] == "H100"
    assert "current_benchmark" in tool_res
    assert "recent_trend" in tool_res
    assert "providers_quotations" in tool_res

    # Test execute_tool dispatch
    disp_res = agent.execute_tool("get_gpu_rental_prices", {"gpu_model": "H200"})
    assert disp_res["requested_model"] == "H200"
    assert "current_benchmark" in disp_res
