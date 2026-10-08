"""
Integration tests for Company-Centric Workspace & Memory Claude Macro Hub Endpoints
"""
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_company_full_profile(client):
    # Test NVIDIA full profile
    res = client.get("/api/companies/NVDA/full")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["entity"]["ticker"] == "NVDA"
    assert "stock" in data
    assert "calendar" in data
    assert "financials" in data
    assert "analyst" in data
    assert "value_chain" in data
    assert len(data["value_chain"]["suppliers"]) > 0
    assert len(data["value_chain"]["customers"]) > 0

def test_company_financials_series(client):
    res = client.get("/api/companies/NVDA/financials")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["quarters"]) > 0

def test_company_news(client):
    res = client.get("/api/companies/NVDA/news")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "news" in data

def test_macro_sankey(client):
    res = client.get("/api/macro/sankey")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["flows"]) > 0
    assert len(data["companies"]) > 0

def test_macro_hbm_balance(client):
    res = client.get("/api/macro/hbm-balance")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["timeline"]) > 0
    assert len(data["market_share"]) == 3

def test_macro_contracts(client):
    res = client.get("/api/macro/contracts")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["count"] == 15
    assert data["total_value_b"] > 800

def test_macro_capacity(client):
    res = client.get("/api/macro/capacity")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["fabs_count"] > 0
    assert data["datacenters_count"] > 0
