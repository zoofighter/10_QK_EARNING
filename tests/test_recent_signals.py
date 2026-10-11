"""
Tests for Recent Monthly Intelligent Signal Filtering in Company Snapshot.
"""
import pytest
from app import create_app
from app.services.ledger_service import LedgerService


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_recent_monthly_signals_service():
    """Verify LedgerService.get_recent_monthly_signals returns scored signals within window."""
    res = LedgerService.get_recent_monthly_signals(ticker="TSM", days=30, min_score=60, limit=6)
    assert res["status"] == "success"
    assert res["ticker"] == "TSM"
    assert "window" in res
    assert res["window"]["days_applied"] in (30, 60)
    assert len(res["signals"]) > 0

    top = res["signals"][0]
    assert "importance_score" in top
    assert top["importance_score"] >= 60
    assert "badge_type" in top
    assert "badge_label" in top
    assert "days_ago_label" in top


def test_recent_monthly_signals_api(client):
    """Verify GET /api/companies/<ticker>/signals/recent-monthly API response."""
    resp = client.get("/api/companies/ANTHROPIC/signals/recent-monthly?days=30&min_score=60&limit=5")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "window" in data
    assert "signals" in data
    assert len(data["signals"]) <= 5


def test_nonexistent_ticker(client):
    """Verify empty signals for a non-existent company ticker."""
    resp = client.get("/api/companies/UNKNOWN_TICKER_XYZ/signals/recent-monthly")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert len(data["signals"]) == 0
