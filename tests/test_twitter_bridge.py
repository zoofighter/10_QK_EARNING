"""
Unit and integration tests for TwitterBridge service.
"""
import pytest
from app.services.twitter_bridge import TwitterBridge, ENTITY_CATALOG


def test_entity_catalog_integrity():
    assert len(ENTITY_CATALOG) >= 35
    tickers = [e["ticker"] for e in ENTITY_CATALOG]
    assert "NVDA" in tickers
    assert "TSM" in tickers
    assert "005930" in tickers
    assert "OAI" in tickers


def test_entity_matching():
    bridge = TwitterBridge()
    text = "Elon Musk met with TSMC regarding custom chip manufacturing for Tesla and xAI."
    matched = bridge.match_entities(text)
    matched_tickers = [m["ticker"] for m in matched]
    assert "TSM" in matched_tickers
    assert "SPACEX" in matched_tickers


def test_confidence_determination():
    bridge = TwitterBridge()
    # Official SEC link -> C4
    tweet_sec = {
        "tier": "P0",
        "url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000001/nvda-8k.htm",
        "content": "NVIDIA files 8-K",
    }
    badge, conf = bridge.determine_confidence_and_type(tweet_sec)
    assert conf == "C4"

    # SemiAnalysis link / mention -> C3
    tweet_semi = {
        "tier": "P0",
        "url": "https://x.com/SemiAnalysis_/status/123",
        "scraped_title": "SemiAnalysis Rubin Architecture Deep Dive",
        "content": "Exclusive analysis on Rubin",
    }
    badge, conf = bridge.determine_confidence_and_type(tweet_semi)
    assert conf == "C3"

    # Rumor mention -> C1
    tweet_rumor = {
        "tier": "P2",
        "url": "https://x.com/random/status/123",
        "content": "Unconfirmed rumor about Blackwell packaging delay",
    }
    badge, conf = bridge.determine_confidence_and_type(tweet_rumor)
    assert conf == "C1"


def test_signalforge_db_connection_and_conversion():
    bridge = TwitterBridge()
    if not bridge.db_path.exists():
        pytest.skip("SignalForge database not present in local test environment")

    events = bridge.convert_to_unpivoted_events(limit=50)
    assert len(events) > 0
    first_ev = events[0]
    assert first_ev.layer.startswith("**L")
    assert "[𝕏 Radar]" in first_ev.content
    assert any(c in first_ev.event_type_confidence for c in ["C1", "C2", "C3", "C4"])
