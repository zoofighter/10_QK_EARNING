"""
Tests for Naver Report Collector & Global IB Target Price System
"""
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pytest
import json
from unittest.mock import patch, MagicMock
from app import create_app
from app.services.naver_report_collector import NaverReportCollector
from app.services.ib_target_collector import IBTargetCollector
from app.models.database import get_db, execute_db, query_db

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_ib_target_collector_normalization():
    """Test broker name normalization and action mapping."""
    collector = IBTargetCollector()
    
    assert collector._normalize_broker_name("Goldman Sachs & Co.") == "Goldman Sachs"
    assert collector._normalize_broker_name("Citigroup Global Markets") == "Citigroup"
    assert collector._normalize_broker_name("JPMorgan Chase") == "JPMorgan"
    assert collector._normalize_broker_name("Morgan Stanley Research") == "Morgan Stanley"
    assert collector._normalize_broker_name("BofA Securities") == "Bank of America"
    assert collector._normalize_broker_name("Nomura Securities") == "Nomura"
    assert collector._normalize_broker_name("Unknown Boutique") == "Unknown Boutique"

    # Tier verification
    assert IBTargetCollector.get_broker_tier("Goldman Sachs") == "TIER_1"
    assert IBTargetCollector.get_broker_tier("Citigroup") == "TIER_1"
    assert IBTargetCollector.get_broker_tier("Nomura") == "TIER_2"
    assert IBTargetCollector.get_broker_tier("Barclays") == "TIER_2"
    assert IBTargetCollector.get_broker_tier("Mizuho") == "TIER_3"
    assert IBTargetCollector.get_broker_tier("Needham") == "TIER_3"
    assert IBTargetCollector.get_broker_tier("Unknown Broker") == "TIER_OTHER"

    assert collector._map_action_type("up") == "Upgrade"
    assert collector._map_action_type("raises") == "Upgrade"
    assert collector._map_action_type("down") == "Downgrade"
    assert collector._map_action_type("cuts") == "Downgrade"
    assert collector._map_action_type("main") == "Maintain"
    assert collector._map_action_type("init") == "Initiate"

def test_naver_report_collector_parsing(tmp_path):
    """Test Naver report collection logic with mocked HTTP responses."""
    collector = NaverReportCollector(delay_sec=0.0)

    mock_list_resp = [
        {
            "researchCategory": "종목분석",
            "itemCode": "000660",
            "itemName": "SK하이닉스",
            "researchId": 99901,
            "title": "HBM 선두 지위 공고화",
            "brokerName": "미래에셋증권",
            "writeDate": "2026-09-21"
        }
    ]

    mock_detail_resp = {
        "researchContent": {
            "itemCode": "000660",
            "itemName": "SK하이닉스",
            "researchId": 99901,
            "title": "HBM 선두 지위 공고화",
            "brokerName": "미래에셋증권",
            "writeDate": "2026-09-21",
            "attachUrl": "https://fake.pstatic.net/fake.pdf",
            "opinion": "매수",
            "goalPrice": "280000",
            "prevGoalPrice": "250000",
            "priceAtWriteDate": "190000",
            "content": "<p>HBM3E 공급 가속화로 사상 최대 실적 지속 전망</p>"
        },
        "researchSummaries": []
    }

    with patch.object(collector, "_http_get_json") as mock_get_json:
        def side_effect(url):
            if "pageSize=50" in url:
                return mock_list_resp
            elif "99901" in url:
                return mock_detail_resp
            return None
        mock_get_json.side_effect = side_effect

        with patch.object(collector, "_download_pdf", return_value=True):
            res = collector.collect_reports_for_ticker("000660.KS", download_pdf=False, max_scan_pages=1)
            
            assert res["ticker"] == "000660.KS"
            assert res["total_processed"] == 1
            reports = res["reports"]
            assert len(reports) == 1
            r = reports[0]
            assert r["broker_name"] == "미래에셋증권"
            assert r["target_price"] == 280000.0
            assert r["action_type"] == "Upgrade"
            assert r["rating"] == "매수"

def test_api_analyst_reports_and_bands(client):
    """Test API endpoint /api/reports/analysts and /api/reports/target-bands."""
    # Ensure NVDA entity exists
    entity = query_db("SELECT id FROM entity WHERE ticker = 'NVDA'", one=True)
    if not entity:
        pytest.skip("NVDA entity not in test database")

    # Insert a mock analyst report
    execute_db(
        """
        INSERT INTO analyst_report (
            entity_id, ticker, source_type, broker_name, report_date,
            title, rating, action_type, target_price, current_price_at_report,
            upside_pct, currency
        ) VALUES (?, 'NVDA', 'GLOBAL_IB', 'Goldman Sachs', '2026-09-20',
                  'Goldman Sachs Upgrade to Buy', 'Buy', 'Upgrade', 185.0, 120.0,
                  54.17, 'USD')
        ON CONFLICT(entity_id, broker_name, report_date, title) DO UPDATE SET
            target_price = excluded.target_price
        """,
        (entity["id"],)
    )

    # Call /api/reports/analysts
    resp = client.get("/api/reports/analysts?ticker=NVDA")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ticker"] == "NVDA"
    assert data["total_reports"] >= 1
    assert any(r["broker_name"] == "Goldman Sachs" for r in data["reports"])

    # Call /api/reports/target-bands
    resp_bands = client.get("/api/reports/target-bands?ticker=NVDA&days=30")
    assert resp_bands.status_code == 200
    bands_data = resp_bands.get_json()
    assert bands_data["ticker"] == "NVDA"
    assert "target_means" in bands_data
