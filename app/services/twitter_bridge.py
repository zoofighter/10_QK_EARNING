"""
Twitter / 𝕏 Signal Bridge Service
Reads data from c_1006_subject_outline (SignalForge) SQLite database in read-only mode,
maps tweets to the 36 semiconductor value chain entities, and converts them to unpivoted matrix events.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default relative path to SignalForge timeline DB
DEFAULT_SIGNALFORGE_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "c_1006_subject_outline" / "data" / "timeline.db"

# 36 Entity Master Mapping Dictionary
ENTITY_CATALOG: list[dict[str, Any]] = [
    # L1 AI Models
    {
        "layer_id": "L1_AI_MODEL",
        "layer_name": "L1 AI 모델",
        "ticker": "OAI",
        "name_en": "OpenAI",
        "name_ko": "오픈AI",
        "country": "🇺🇸",
        "keywords": ["openai", "open ai", "chatgpt", "gpt-4", "gpt-5", "o1", "o3", "altman", "sam altman"],
    },
    {
        "layer_id": "L1_AI_MODEL",
        "layer_name": "L1 AI 모델",
        "ticker": "ANTHROPIC",
        "name_en": "Anthropic",
        "name_ko": "앤트로픽",
        "country": "🇺🇸",
        "keywords": ["anthropic", "claude", "amodei", "dario amodei", "claude 3", "claude 3.5"],
    },
    # L2 Hyperscalers
    {
        "layer_id": "L2_HYPERSCALER",
        "layer_name": "L2 하이퍼스케일러",
        "ticker": "GOOGL",
        "name_en": "Alphabet",
        "name_ko": "구글",
        "country": "🇺🇸",
        "keywords": ["google", "alphabet", "googl", "tpu", "gemini", "deepmind"],
    },
    {
        "layer_id": "L2_HYPERSCALER",
        "layer_name": "L2 하이퍼스케일러",
        "ticker": "AMZN",
        "name_en": "Amazon",
        "name_ko": "아마존",
        "country": "🇺🇸",
        "keywords": ["amazon", "aws", "amzn", "trainium", "inferentia", "andy jassy"],
    },
    {
        "layer_id": "L2_HYPERSCALER",
        "layer_name": "L2 하이퍼스케일러",
        "ticker": "MSFT",
        "name_en": "Microsoft",
        "name_ko": "마이크로소프트",
        "country": "🇺🇸",
        "keywords": ["microsoft", "msft", "azure", "satya nadella", "maia"],
    },
    {
        "layer_id": "L2_HYPERSCALER",
        "layer_name": "L2 하이퍼스케일러",
        "ticker": "META",
        "name_en": "Meta Platforms",
        "name_ko": "메타",
        "country": "🇺🇸",
        "keywords": ["meta", "facebook", "zuckerberg", "llama", "mtia"],
    },
    {
        "layer_id": "L2_HYPERSCALER",
        "layer_name": "L2 하이퍼스케일러",
        "ticker": "ORCL",
        "name_en": "Oracle",
        "name_ko": "오라클",
        "country": "🇺🇸",
        "keywords": ["oracle", "orcl", "oci", "larry ellison"],
    },
    {
        "layer_id": "L2_HYPERSCALER",
        "layer_name": "L2 하이퍼스케일러",
        "ticker": "CRWV",
        "name_en": "CoreWeave",
        "name_ko": "코어위브",
        "country": "🇺🇸",
        "keywords": ["coreweave", "crwv", "brannin mcbee", "mike intrator"],
    },
    {
        "layer_id": "L2_HYPERSCALER",
        "layer_name": "L2 하이퍼스케일러",
        "ticker": "NBIS",
        "name_en": "Nebius Group",
        "name_ko": "네비우스",
        "country": "🇳🇱",
        "keywords": ["nebius", "nbis", "arkady volozh"],
    },
    # L3 Compute & Accelerators
    {
        "layer_id": "L3_COMPUTE",
        "layer_name": "L3 컴퓨팅/가속기",
        "ticker": "NVDA",
        "name_en": "NVIDIA",
        "name_ko": "엔비디아",
        "country": "🇺🇸",
        "keywords": ["nvidia", "nvda", "jensen huang", "jensen", "blackwell", "b200", "gb200", "h100", "h200", "rubin", "r100"],
    },
    {
        "layer_id": "L3_COMPUTE",
        "layer_name": "L3 컴퓨팅/가속기",
        "ticker": "AMD",
        "name_en": "AMD",
        "name_ko": "AMD",
        "country": "🇺🇸",
        "keywords": ["amd", "lisa su", "mi300", "mi300x", "mi325", "mi350", "turin", "epyc"],
    },
    {
        "layer_id": "L3_COMPUTE",
        "layer_name": "L3 컴퓨팅/가속기",
        "ticker": "AVGO",
        "name_en": "Broadcom",
        "name_ko": "브로드컴",
        "country": "🇺🇸",
        "keywords": ["broadcom", "avgo", "hock tan", "tomahawk", "jericho", "custom asic"],
    },
    {
        "layer_id": "L3_COMPUTE",
        "layer_name": "L3 컴퓨팅/가속기",
        "ticker": "ARM",
        "name_en": "Arm Holdings",
        "name_ko": "Arm",
        "country": "🇬🇧",
        "keywords": ["arm holdings", "arm", "rene haas", "neoverse"],
    },
    {
        "layer_id": "L3_COMPUTE",
        "layer_name": "L3 컴퓨팅/가속기",
        "ticker": "INTC",
        "name_en": "Intel",
        "name_ko": "인텔",
        "country": "🇺🇸",
        "keywords": ["intel", "intc", "pat gelsinger", "18a", "gaudi", "panther lake", "lunar lake"],
    },
    # L4 Foundry & Equipment
    {
        "layer_id": "L4_FOUNDRY",
        "layer_name": "L4 파운드리/제조",
        "ticker": "TSM",
        "name_en": "TSMC",
        "name_ko": "TSMC",
        "country": "🇹🇼",
        "keywords": ["tsmc", "tsm", "taiwan semi", "c.c. wei", "cowos", "n2", "a16", "terafab"],
    },
    {
        "layer_id": "L4_FOUNDRY",
        "layer_name": "L4 파운드리/제조",
        "ticker": "ASML",
        "name_en": "ASML",
        "name_ko": "ASML",
        "country": "🇳🇱",
        "keywords": ["asml", "christophe fouquet", "high na", "euv", "duv"],
    },
    {
        "layer_id": "L4_FOUNDRY",
        "layer_name": "L4 파운드리/제조",
        "ticker": "AMAT",
        "name_en": "Applied Materials",
        "name_ko": "어플라이드 머티어리얼즈",
        "country": "🇺🇸",
        "keywords": ["applied materials", "amat", "gary dickerson"],
    },
    {
        "layer_id": "L4_FOUNDRY",
        "layer_name": "L4 파운드리/제조",
        "ticker": "LRCX",
        "name_en": "Lam Research",
        "name_ko": "램리서치",
        "country": "🇺🇸",
        "keywords": ["lam research", "lrcx", "tim archer"],
    },
    {
        "layer_id": "L4_FOUNDRY",
        "layer_name": "L4 파운드리/제조",
        "ticker": "KLAC",
        "name_en": "KLA",
        "name_ko": "KLA",
        "country": "🇺🇸",
        "keywords": ["kla", "klac", "rick wallace"],
    },
    {
        "layer_id": "L4_FOUNDRY",
        "layer_name": "L4 파운드리/제조",
        "ticker": "ASX",
        "name_en": "ASE Technology",
        "name_ko": "ASE",
        "country": "🇹🇼",
        "keywords": ["ase technology", "asx", "ase", "日月光", "osat"],
    },
    {
        "layer_id": "L4_FOUNDRY",
        "layer_name": "L4 파운드리/제조",
        "ticker": "AMKR",
        "name_en": "Amkor Technology",
        "name_ko": "앰코",
        "country": "🇺🇸",
        "keywords": ["amkor", "amkr", "giel rutten"],
    },
    # L5 Memory & Storage
    {
        "layer_id": "L5_MEMORY",
        "layer_name": "L5 메모리/스토리지",
        "ticker": "000660",
        "name_en": "SK hynix",
        "name_ko": "SK하이닉스",
        "country": "🇰🇷",
        "keywords": ["sk hynix", "hynix", "sk하이닉스", "hbm3e", "hbm4", "곽노정"],
    },
    {
        "layer_id": "L5_MEMORY",
        "layer_name": "L5 메모리/스토리지",
        "ticker": "005930",
        "name_en": "삼성전자",
        "name_ko": "삼성전자",
        "country": "🇰🇷",
        "keywords": ["samsung", "삼성전자", "samsung electronics", "전영현", "hbm", "taylor fab", "테일러"],
    },
    {
        "layer_id": "L5_MEMORY",
        "layer_name": "L5 메모리/스토리지",
        "ticker": "MU",
        "name_en": "Micron",
        "name_ko": "마이크론",
        "country": "🇺🇸",
        "keywords": ["micron", "mu", "sanjay mehrotra"],
    },
    {
        "layer_id": "L5_MEMORY",
        "layer_name": "L5 메모리/스토리지",
        "ticker": "WDC",
        "name_en": "Western Digital",
        "name_ko": "웨스턴디지털",
        "country": "🇺🇸",
        "keywords": ["western digital", "wdc", "david goeckeler"],
    },
    {
        "layer_id": "L5_MEMORY",
        "layer_name": "L5 메모리/스토리지",
        "ticker": "SNDK",
        "name_en": "SanDisk",
        "name_ko": "샌디스크",
        "country": "🇺🇸",
        "keywords": ["sandisk", "sndk"],
    },
    {
        "layer_id": "L5_MEMORY",
        "layer_name": "L5 메모리/스토리지",
        "ticker": "6600",
        "name_en": "Kioxia",
        "name_ko": "키옥시아",
        "country": "🇯🇵",
        "keywords": ["kioxia", "키옥시아", "6600.t"],
    },
    # L6 Optical & Networking
    {
        "layer_id": "L6_OPTICAL",
        "layer_name": "L6 광통신/네트워킹",
        "ticker": "MRVL",
        "name_en": "Marvell",
        "name_ko": "마벨",
        "country": "🇺🇸",
        "keywords": ["marvell", "mrvl", "matt murphy", "optical dsp"],
    },
    {
        "layer_id": "L6_OPTICAL",
        "layer_name": "L6 광통신/네트워킹",
        "ticker": "COHR",
        "name_en": "Coherent",
        "name_ko": "코히어런트",
        "country": "🇺🇸",
        "keywords": ["coherent", "cohr", "jim anderson", "transceiver"],
    },
    {
        "layer_id": "L6_OPTICAL",
        "layer_name": "L6 광통신/네트워킹",
        "ticker": "ANET",
        "name_en": "Arista Networks",
        "name_ko": "아리스타",
        "country": "🇺🇸",
        "keywords": ["arista", "anet", "jayshree ullal"],
    },
    # L7 Infra & Specialized
    {
        "layer_id": "L7_INFRA",
        "layer_name": "L7 인프라/특수",
        "ticker": "AAPL",
        "name_en": "Apple",
        "name_ko": "애플",
        "country": "🇺🇸",
        "keywords": ["apple", "aapl", "tim cook", "apple intelligence", "acdc"],
    },
    {
        "layer_id": "L7_INFRA",
        "layer_name": "L7 인프라/특수",
        "ticker": "SPACEX",
        "name_en": "SpaceX / xAI",
        "name_ko": "스페이스X/xAI",
        "country": "🇺🇸",
        "keywords": ["spacex", "xai", "grok", "colossus", "elon", "elon musk"],
    },
    {
        "layer_id": "L7_INFRA",
        "layer_name": "L7 인프라/특수",
        "ticker": "9984",
        "name_en": "SoftBank",
        "name_ko": "소프트뱅크",
        "country": "🇯🇵",
        "keywords": ["softbank", "손정의", "masayoshi son", "project izanagi"],
    },
    # L8 Power & Energy
    {
        "layer_id": "L8_POWER",
        "layer_name": "L8 전력/에너지",
        "ticker": "VRT",
        "name_en": "Vertiv",
        "name_ko": "버티브",
        "country": "🇺🇸",
        "keywords": ["vertiv", "vrt", "giordano albertazzi", "liquid cooling"],
    },
    {
        "layer_id": "L8_POWER",
        "layer_name": "L8 전력/에너지",
        "ticker": "ETN",
        "name_en": "Eaton",
        "name_ko": "이튼",
        "country": "🇮🇪",
        "keywords": ["eaton", "etn", "craig arnold"],
    },
    {
        "layer_id": "L8_POWER",
        "layer_name": "L8 전력/에너지",
        "ticker": "GEV",
        "name_en": "GE Vernova",
        "name_ko": "GE 버노바",
        "country": "🇺🇸",
        "keywords": ["ge vernova", "gev", "scott strazik"],
    },
    {
        "layer_id": "L8_POWER",
        "layer_name": "L8 전력/에너지",
        "ticker": "SBGSF",
        "name_en": "Schneider Electric",
        "name_ko": "슈나이더 일렉트릭",
        "country": "🇫🇷",
        "keywords": ["schneider electric", "schneider", "sbgsf"],
    },
]


@dataclass
class UnpivotedEvent:
    layer: str
    entity: str
    date: str
    content: str
    event_type_confidence: str
    raw_tweet_id: Optional[int] = None
    author: Optional[str] = None
    url: Optional[str] = None


class TwitterBridge:
    """Bridge for reading Twitter events from SignalForge timeline.db and mapping to 36 entities."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_SIGNALFORGE_DB_PATH

    def get_connection(self) -> sqlite3.Connection:
        """Connect to SignalForge timeline.db in read-only mode."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"SignalForge database not found at {self.db_path}")

        uri_path = f"file:{self.db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri_path, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_raw_tweets(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Fetch raw tweets from timeline_events."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, source, author_handle, author_name, tier, content, url,
                       scraped_title, scraped_snippet, metrics, published_at, created_at
                FROM timeline_events
                WHERE source = 'twitter'
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def match_entities(self, text: str) -> list[dict[str, Any]]:
        """Match entities from text based on keywords."""
        text_lower = text.lower()
        matched = []
        for ent in ENTITY_CATALOG:
            for kw in ent["keywords"]:
                # Check keyword boundary or word match
                pattern = rf"\b{re.escape(kw)}\b" if len(kw) <= 4 else re.escape(kw)
                if re.search(pattern, text_lower):
                    matched.append(ent)
                    break
        return matched

    def determine_confidence_and_type(self, tweet: dict[str, Any]) -> tuple[str, str]:
        """
        Determine confidence (C1~C4) and event type badge.
        Returns: (event_type_label, confidence_badge)
        """
        author_tier = tweet.get("tier", "P1")
        author_name = tweet.get("author_name", "")
        content = tweet.get("content", "").lower()
        url = tweet.get("url", "")
        scraped_title = tweet.get("scraped_title") or ""

        # Check official links or SEC / IR
        if any(term in url.lower() for term in ["sec.gov", "investor.", "ir.", "press-release"]):
            return "🚩 공식공시", "C4"

        # Check major news links in scraped_title or content
        if any(term in (scraped_title.lower() + content) for term in ["semianalysis", "bloomberg", "reuters", "wsj"]):
            return "📜 언론보도", "C3"

        # If reported by P0 tier key analyst
        if author_tier == "P0" or any(p in author_name.lower() for p in ["dylan patel", "dan nystedt"]):
            if any(term in content for term in ["exclusive", "contract", "delay", "leak"]):
                return "⚠️ 공급망속보", "C2"
            return "💬 분석가전망", "C2"

        # General rumor / radar
        if any(term in content for term in ["rumor", "leak", "unconfirmed", "heard", "delay", "cancel"]):
            return "⚠️ 루머", "C1"

        return "💬 트위터", "C1"

    def parse_published_date(self, published_at: str) -> str:
        """Parse published_at ISO string to YYYY-MM-DD."""
        if not published_at:
            return datetime.now().strftime("%Y-%m-%d")

        # Try multiple date formats
        cleaned = published_at.replace("T", " ").split("+")[0].split(".")[0]
        try:
            dt = datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            try:
                dt = datetime.strptime(cleaned[:10], "%Y-%m-%d")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return published_at[:10]

    def convert_to_unpivoted_events(self, limit: int = 1000) -> list[UnpivotedEvent]:
        """Convert matched tweets to UnpivotedEvent records."""
        tweets = self.fetch_raw_tweets(limit=limit)
        events: list[UnpivotedEvent] = []

        for tweet in tweets:
            content = tweet.get("content", "")
            matched_entities = self.match_entities(content)
            if not matched_entities:
                continue

            event_type, confidence = self.determine_confidence_and_type(tweet)
            event_date = self.parse_published_date(tweet.get("published_at", ""))
            author_str = f"{tweet.get('author_name', 'Unknown')}({tweet.get('author_handle', '')})"

            # Clean content for markdown matrix: replace newlines and escape pipe characters
            clean_content = " ".join(content.strip().splitlines()).replace("|", "\\|")

            formatted_content = f"[𝕏 Radar] {author_str}: {clean_content}"
            type_confidence_str = f"{event_type} `[{confidence}]`"

            for ent in matched_entities:
                events.append(
                    UnpivotedEvent(
                        layer=f"**{ent['layer_name']}**",
                        entity=f"**{ent['name_en']}** ({ent['ticker']} {ent['country']})",
                        date=event_date,
                        content=formatted_content,
                        event_type_confidence=type_confidence_str,
                        raw_tweet_id=tweet.get("id"),
                        author=author_str,
                        url=tweet.get("url"),
                    )
                )

        return events
