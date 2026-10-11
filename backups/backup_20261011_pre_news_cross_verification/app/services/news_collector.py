"""
News Collector Service for AI Semiconductor Value Chain Entities.
Collects and indexes real-time & historical news from:
1. Google News RSS (Korean & Global coverage)
2. Yahoo Finance RSS (Wall Street equity headlines)
Stores structured news into the SQLite 'news' table with deduplication and relevance scoring.
"""
import re
import html
import time
import email.utils
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.models.database import get_db, query_db, execute_db


class NewsCollector:
    """Collector and indexer for company-specific news via RSS feeds."""

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    REQUEST_TIMEOUT = 8

    # Customized clean query search map for non-standard tickers
    SEARCH_QUERY_MAP = {
        "000660.KS": "SK하이닉스 Hynix",
        "005930.KS": "삼성전자 Samsung Electronics",
        "6600.T": "키옥시아 Kioxia",
        "9984.T": "소프트뱅크 SoftBank Group",
        "OAI": "오픈AI OpenAI ChatGPT Sam Altman",
        "ANTHROPIC": "앤트로픽 Anthropic Claude Dario Amodei",
        "SPACEX": "스페이스X xAI SpaceX",
        "CRWV": "코어위브 CoreWeave",
        "NBIS": "네비우스 Nebius",
        "AVGO": "브로드컴 Broadcom",
        "VRT": "버티브 Vertiv",
        "ANET": "아리스타 Arista Networks",
        "ETN": "이튼 Eaton",
        "GEV": "GE버노바 GE Vernova",
        "SBGSF": "슈나이더 Schneider Electric",
        "COHR": "코히어런트 Coherent",
        "MRVL": "마벨 Marvell Technology",
        "LRCX": "램리서치 Lam Research",
        "AMAT": "어플라이드 머티어리얼즈 Applied Materials",
        "KLAC": "KLA 코퍼레이션 KLA",
        "AMKR": "앰코 Amkor Technology",
        "ASX": "ASE 테크놀로지 ASE",
        "TSM": "TSMC 대만반도체",
        "ASML": "ASML 에이에스엠엘",
        "ARM": "Arm 홀딩스 Arm",
        "INTC": "인텔 Intel",
        "WDC": "웨스턴디지털 Western Digital",
        "SNDK": "샌디스크 SanDisk",
        "MU": "마이크론 Micron",
    }

    def __init__(self):
        pass

    def _clean_text(self, text: Optional[str]) -> str:
        """Strip HTML tags and unescape HTML entities."""
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", "", text)
        clean = html.unescape(clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def _parse_pub_date(self, pub_str: Optional[str]) -> str:
        """Convert RFC 2822 / arbitrary pubDate string to YYYY-MM-DD HH:MM:SS."""
        if not pub_str:
            return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        try:
            dt = email.utils.parsedate_to_datetime(pub_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    def _fetch_rss(self, url: str) -> List[Dict[str, Any]]:
        """Fetch and parse RSS items from a URL."""
        req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
        items = []
        try:
            with urllib.request.urlopen(req, timeout=self.REQUEST_TIMEOUT) as resp:
                xml_data = resp.read()
                root = ET.fromstring(xml_data)
                for it in root.findall(".//item"):
                    title = it.findtext("title")
                    link = it.findtext("link")
                    pub = it.findtext("pubDate")
                    desc = it.findtext("description")
                    src = it.findtext("source")

                    if not link or not title:
                        continue

                    items.append({
                        "title": self._clean_text(title),
                        "link": link.strip(),
                        "published": self._parse_pub_date(pub),
                        "snippet": self._clean_text(desc)[:300],
                        "source": self._clean_text(src) or "News"
                    })
        except Exception as e:
            # Gracefully catch network / xml errors
            pass
        return items

    def fetch_google_news(self, query: str, lang: str = "ko", country: str = "KR") -> List[Dict[str, Any]]:
        """Fetch Google News RSS for a given search query."""
        encoded_q = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_q}&hl={lang}&gl={country}&ceid={country}:{lang}"
        items = self._fetch_rss(url)
        for it in items:
            if not it.get("source") or it["source"] == "News":
                # Often Google News title ends with ' - SourceName'
                if " - " in it["title"]:
                    parts = it["title"].rsplit(" - ", 1)
                    it["source"] = parts[1].strip()
        return items

    def fetch_yahoo_finance(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch Yahoo Finance RSS for a US-compatible ticker."""
        clean_ticker = ticker.split(".")[0].upper()
        # Only relevant for US-style stock tickers
        if not clean_ticker.isalpha():
            return []
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={clean_ticker}&region=US&lang=en-US"
        items = self._fetch_rss(url)
        for it in items:
            it["source"] = "Yahoo Finance"
        return items

    def collect_for_entity(
        self,
        ticker: str,
        name_ko: str,
        name_en: str,
        limit_target: int = 40
    ) -> Dict[str, Any]:
        """Collect, deduplicate, and store news for a single company."""
        collected_articles = []
        seen_links = set()

        search_q = self.SEARCH_QUERY_MAP.get(ticker, f"{name_ko} {name_en} {ticker}")

        # 1. Google News Korean search
        ko_items = self.fetch_google_news(search_q, lang="ko", country="KR")
        for it in ko_items:
            if it["link"] not in seen_links:
                seen_links.add(it["link"])
                it["query"] = search_q
                it["score"] = 85
                collected_articles.append(it)

        # 2. Yahoo Finance RSS (if US ticker)
        yf_items = self.fetch_yahoo_finance(ticker)
        for it in yf_items:
            if it["link"] not in seen_links:
                seen_links.add(it["link"])
                it["query"] = ticker
                it["score"] = 90
                collected_articles.append(it)

        # 3. Google News Global (EN) search if collected items are still fewer than 15
        if len(collected_articles) < 15:
            en_q = f"{name_en} {ticker.split('.')[0]} semiconductor"
            en_items = self.fetch_google_news(en_q, lang="en-US", country="US")
            for it in en_items:
                if it["link"] not in seen_links:
                    seen_links.add(it["link"])
                    it["query"] = en_q
                    it["score"] = 75
                    collected_articles.append(it)

        # Sort newest first
        collected_articles.sort(key=lambda x: x["published"], reverse=True)
        target_articles = collected_articles[:limit_target]

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        inserted_count = 0

        # Insert into database with deduplication
        with get_db() as conn:
            cur = conn.cursor()
            for art in target_articles:
                try:
                    cur.execute("""
                        INSERT OR IGNORE INTO news (
                            url, title, snippet, source, company, ticker, query, score, published, collected_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        art["link"],
                        art["title"],
                        art["snippet"],
                        art["source"],
                        name_ko or name_en,
                        ticker,
                        art.get("query", search_q),
                        art.get("score", 80),
                        art["published"],
                        now_str
                    ))
                    if cur.rowcount > 0:
                        inserted_count += 1
                except Exception:
                    pass

        return {
            "status": "success",
            "ticker": ticker,
            "fetched_count": len(target_articles),
            "inserted_count": inserted_count
        }

    def collect_all_entities(self, min_threshold: int = 15) -> Dict[str, Any]:
        """
        Check all 34 entities in DB, collect news for any entity with news count < min_threshold.
        """
        entities = query_db("SELECT id, ticker, name_en, name_ko FROM entity ORDER BY id ASC")
        if not entities:
            return {"status": "error", "message": "No entities found in database"}

        results = []
        total_inserted = 0

        for ent in entities:
            ticker = ent["ticker"]
            name_ko = ent["name_ko"]
            name_en = ent["name_en"]

            # Check existing news count for this ticker (and its base ticker)
            base_ticker = ticker.split(".")[0]
            existing_cnt = query_db(
                """
                SELECT COUNT(*) as cnt FROM news
                WHERE UPPER(ticker) = UPPER(?) OR UPPER(ticker) = UPPER(?) OR company LIKE ?
                """,
                (ticker, base_ticker, f"%{name_ko}%"),
                one=True
            )["cnt"]

            if existing_cnt < min_threshold:
                res = self.collect_for_entity(ticker, name_ko, name_en, limit_target=40)
                inserted = res.get("inserted_count", 0)
                total_inserted += inserted
                results.append({
                    "ticker": ticker,
                    "name_ko": name_ko,
                    "previous_count": existing_cnt,
                    "newly_inserted": inserted,
                    "status": "COLLECTED"
                })
                time.sleep(0.15)  # Be polite to RSS endpoints
            else:
                results.append({
                    "ticker": ticker,
                    "name_ko": name_ko,
                    "current_count": existing_cnt,
                    "status": "SKIPPED_SUFFICIENT"
                })

        return {
            "status": "success",
            "total_entities": len(entities),
            "total_newly_inserted": total_inserted,
            "details": results
        }
