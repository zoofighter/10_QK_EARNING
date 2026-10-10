"""
Tests for NewsCollector service and /api/companies/<ticker>/news endpoint.
"""
import pytest
from app import create_app
from app.services.news_collector import NewsCollector
from app.models.database import get_db


@pytest.fixture
def test_client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_news_collector_methods():
    collector = NewsCollector()
    assert collector is not None
    # Test cleaning text
    clean = collector._clean_text("<b>Title with tags</b> &amp; special")
    assert "<b>" not in clean
    assert "&" in clean


def test_api_company_news_avgo(test_client):
    """Verify previously empty company (AVGO) returns news."""
    resp = test_client.get("/api/companies/AVGO/news?limit=10")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["ticker"] == "AVGO"
    assert data["count"] > 0
    assert len(data["news"]) > 0


def test_api_company_news_crwv(test_client):
    """Verify CRWV returns news."""
    resp = test_client.get("/api/companies/CRWV/news?limit=10")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["ticker"] == "CRWV"
    assert data["count"] > 0
