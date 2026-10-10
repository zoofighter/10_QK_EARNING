#!/usr/bin/env python3
"""
Seed and update news for all 34 AI semiconductor value chain entities.
Populates Google News RSS and Yahoo Finance RSS news into data/qk_earning.db.
"""
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app.services.news_collector import NewsCollector
from app.models.database import query_db


def main():
    print("=" * 70)
    print("🚀 Starting News Seed for All 34 AI Semiconductor Value Chain Entities")
    print("=" * 70)

    app = create_app()
    with app.app_context():
        collector = NewsCollector()
        print("\nChecking entity news coverage and collecting missing news...")
        res = collector.collect_all_entities(min_threshold=20)

        print("\n" + "=" * 70)
        print(f"📊 News Collection Summary:")
        print(f"   Total Entities Checked: {res.get('total_entities')}")
        print(f"   Total Newly Inserted Articles: {res.get('total_newly_inserted')}")
        print("=" * 70)

        print("\nDetails per Entity:")
        for d in res.get("details", []):
            ticker = d["ticker"].ljust(10)
            name = d["name_ko"].ljust(15)
            if d["status"] == "COLLECTED":
                print(f"  ✅ [COLLECTED] {ticker} {name}: +{d.get('newly_inserted')} articles (was {d.get('previous_count')})")
            else:
                print(f"  ℹ️ [SUFFICIENT]{ticker} {name}: {d.get('current_count')} articles present")

        # Total news in DB
        total_in_db = query_db("SELECT COUNT(*) as cnt FROM news", one=True)["cnt"]
        print("\n" + "=" * 70)
        print(f"🎉 Complete! Total news articles now in DB: {total_in_db:,} articles")
        print("=" * 70)


if __name__ == "__main__":
    main()
