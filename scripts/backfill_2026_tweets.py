#!/usr/bin/env python3
"""
2026 Full-Year Twitter Backfill Script (Plan A)
Backfills authentic 2026-01-01 ~ 2026-08-31 semiconductor intelligence tweets
from core influencers into c_1006_subject_outline/data/timeline.db.
"""
import sys
import os
import re
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# Paths
B_PROJECT_DIR = Path(__file__).resolve().parent.parent
C_PROJECT_DIR = B_PROJECT_DIR.parent / "c_1006_subject_outline"
TIMELINE_DB_PATH = C_PROJECT_DIR / "data" / "timeline.db"
ACCOUNTS_DB_PATH = C_PROJECT_DIR / "data" / "accounts.db"

if str(C_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(C_PROJECT_DIR))

from twscrape import API, gather

KST = timezone(timedelta(hours=9))

# High-Priority Semiconductor & AI Value Chain Influencer Accounts
CORE_INFLUENCERS = [
    {"handle": "dnystedt", "name": "Dan Nystedt", "tier": "P0"},
    {"handle": "SemiAnalysis_", "name": "SemiAnalysis", "tier": "P0"},
    {"handle": "dylan522p", "name": "Dylan Patel", "tier": "P0"},
    {"handle": "jimkxa", "name": "Jim Keller", "tier": "P0"},
    {"handle": "chiakokhua", "name": "Chia Kok Hua", "tier": "P1"},
    {"handle": "pequityresearch", "name": "PEquity Research", "tier": "P0"},
    {"handle": "IanCutress", "name": "Dr. Ian Cutress", "tier": "P1"},
    {"handle": "techanalyst", "name": "Tech Analyst", "tier": "P1"},
    {"handle": "sama", "name": "Sam Altman", "tier": "P0"},
    {"handle": "karpathy", "name": "Andrej Karpathy", "tier": "P1"},
    {"handle": "gaborcselle", "name": "Gabor Cselle", "tier": "P1"},
]

def init_db(conn: sqlite3.Connection):
    """Ensure timeline_events table and index exist."""
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS timeline_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            author_handle TEXT,
            author_name TEXT,
            tier TEXT DEFAULT 'P1',
            content TEXT NOT NULL,
            url TEXT,
            scraped_title TEXT,
            scraped_snippet TEXT,
            metrics TEXT,
            published_at TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_timeline_url ON timeline_events(url) WHERE url IS NOT NULL")
    conn.commit()

async def backfill_influencer(
    api: API,
    conn: sqlite3.Connection,
    influencer: Dict[str, str],
    start_date: str = "2026-01-01",
    end_date: str = "2026-08-31",
    limit_per_user: int = 40,
    delay_sec: float = 2.5
) -> int:
    """Fetch past tweets for an influencer and insert into timeline.db."""
    handle = influencer["handle"].lstrip("@").strip()
    name = influencer["name"]
    tier = influencer.get("tier", "P1")

    query = f"from:{handle} since:{start_date} until:{end_date}"
    print(f"\n[Backfill] 🔍 Querying: '{query}' (Limit: {limit_per_user})...")

    inserted_count = 0
    try:
        tweets_gen = api.search(query, limit=limit_per_user)
        tweets = await gather(tweets_gen)
        print(f"[Backfill] 📥 Found {len(tweets)} tweets for @{handle} in window [{start_date} ~ {end_date}].")

        c = conn.cursor()
        for tw in tweets:
            tw_date = tw.date
            if tw_date:
                if tw_date.tzinfo is None:
                    tw_date = tw_date.replace(tzinfo=timezone.utc)
                local_dt = tw_date.astimezone(KST)
                published_at_str = local_dt.strftime("%Y-%m-%dT%H:%M:%S+09:00")
            else:
                published_at_str = datetime.now(KST).isoformat()

            raw_content = tw.rawContent.strip()
            tweet_url = tw.url

            # Skip retweets or empty replies without text
            if not raw_content:
                continue

            # Metrics
            metrics_dict = {
                "likes": tw.likeCount or 0,
                "retweets": tw.retweetCount or 0,
                "replies": tw.replyCount or 0,
                "views": tw.viewCount or 0,
            }
            import json
            metrics_json = json.dumps(metrics_dict)

            try:
                # Check duplicate by url
                c.execute("SELECT id FROM timeline_events WHERE url = ?", (tweet_url,))
                if c.fetchone():
                    continue

                c.execute("""
                    INSERT INTO timeline_events (
                        source, author_handle, author_name, tier,
                        content, url, metrics, published_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "twitter", handle, name, tier,
                    raw_content, tweet_url, metrics_json, published_at_str
                ))
                inserted_count += 1
            except Exception as e:
                # Ignore duplicates or constraint errors
                pass

        conn.commit()
        print(f"[Backfill] ✅ Inserted {inserted_count} new historical tweets for @{handle}.")

    except Exception as err:
        print(f"[Backfill] ⚠️ Error querying @{handle}: {err}")

    await asyncio.sleep(delay_sec)
    return inserted_count

async def run_backfill(start_date: str = "2026-01-01", end_date: str = "2026-08-31", limit_per_user: int = 40):
    if not TIMELINE_DB_PATH.exists():
        print(f"❌ Target timeline.db not found at: {TIMELINE_DB_PATH}")
        return

    if not ACCOUNTS_DB_PATH.exists():
        print(f"❌ Target accounts.db not found at: {ACCOUNTS_DB_PATH}")
        return

    print("=" * 70)
    print("🚀 2026 FULL-YEAR TWITTER BACKFILL ENGINE (Plan A)")
    print(f"   Target DB: {TIMELINE_DB_PATH}")
    print(f"   Window: {start_date} ~ {end_date}")
    print(f"   Accounts: {len(CORE_INFLUENCERS)} semiconductor influencers")
    print("=" * 70)

    api = API(str(ACCOUNTS_DB_PATH))
    conn = sqlite3.connect(str(TIMELINE_DB_PATH))
    init_db(conn)

    total_added = 0
    for idx, inf in enumerate(CORE_INFLUENCERS, 1):
        print(f"[{idx}/{len(CORE_INFLUENCERS)}] Processing @{inf['handle']} ({inf['name']})...")
        added = await backfill_influencer(
            api=api,
            conn=conn,
            influencer=inf,
            start_date=start_date,
            end_date=end_date,
            limit_per_user=limit_per_user,
            delay_sec=2.5
        )
        total_added += added

    conn.close()
    print("=" * 70)
    print(f"🎉 2026 Backfill Completed! Total New Historical Tweets Inserted: {total_added}")
    print("=" * 70)

if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else "2026-01-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2026-08-31"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 35
    asyncio.run(run_backfill(start_date=start, end_date=end, limit_per_user=limit))
