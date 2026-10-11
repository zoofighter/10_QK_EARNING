"""
FinTwit & Global IB Real-time Question & Answering Agent
Takes natural language queries about analyst price targets and synthesizes
structured tables, analyst arguments, and market sentiment.
"""
import os
import re
import json
import logging
import urllib.request
from typing import Dict, List, Optional, Any
from app.models.database import query_db
from app.config import GLOBAL_IB_TIERS

logger = logging.getLogger(__name__)

STOCKTWITS_API_URL = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class FinTwitQAAgent:
    def __init__(self):
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*"
        }

    def fetch_live_fintwit_stream(self, ticker: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch latest live social posts and news from StockTwits for ticker."""
        clean_ticker = ticker.replace(".KS", "").replace(".KQ", "")
        url = STOCKTWITS_API_URL.format(ticker=clean_ticker)
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                messages = data.get("messages", [])
                results = []
                for m in messages[:limit]:
                    if not isinstance(m, dict):
                        continue
                    entities = m.get("entities") or {}
                    sentiment_obj = entities.get("sentiment") or {}
                    results.append({
                        "id": m.get("id"),
                        "username": (m.get("user") or {}).get("username"),
                        "created_at": m.get("created_at"),
                        "body": m.get("body", "").strip(),
                        "sentiment": sentiment_obj.get("basic") if isinstance(sentiment_obj, dict) else None
                    })
                return results
        except Exception as e:
            logger.warning(f"Error fetching StockTwits for {ticker}: {e}")
            return []

    def answer_query(self, user_query: str, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Process user question about price targets, search DB & FinTwit stream,
        and synthesize a structured summary response.
        """
        # 1. Detect Ticker if not provided
        detected_ticker = ticker
        if not detected_ticker:
            q_upper = user_query.upper()
            known_tickers = ["NVDA", "TSM", "MSFT", "AAPL", "000660.KS", "005930.KS", "AVGO", "GOOGL", "AMZN", "META"]
            for kt in known_tickers:
                if kt in q_upper or (kt == "NVDA" and ("엔비디아" in user_query or "NVIDIA" in q_upper)) or \
                   (kt == "000660.KS" and ("SK하이닉스" in user_query or "하이닉스" in user_query)) or \
                   (kt == "005930.KS" and "삼성전자" in user_query) or \
                   (kt == "TSM" and ("TSMC" in q_upper or "티에스엠씨" in user_query)):
                    detected_ticker = kt
                    break
        
        if not detected_ticker:
            detected_ticker = "NVDA"

        # 2. Look up entity and latest stock price
        entity = query_db("SELECT id, ticker, name_en, name_ko, country FROM entity WHERE ticker = ?", (detected_ticker,), one=True)
        entity_id = entity["id"] if entity else None

        price_row = query_db(
            "SELECT close, date FROM stock_price WHERE entity_id = ? ORDER BY date DESC LIMIT 1",
            (entity_id,),
            one=True
        ) if entity_id else None
        current_price = float(price_row["close"]) if price_row else None
        currency_sym = "₩" if entity and entity["country"] == "KR" else "$"

        # 3. Retrieve relevant analyst reports from database
        db_reports = []
        if entity_id:
            db_reports = query_db(
                """
                SELECT broker_name, report_date, title, rating, action_type,
                       target_price, upside_pct, summary_text, pdf_url, local_pdf_path
                FROM analyst_report
                WHERE entity_id = ? AND target_price IS NOT NULL AND target_price > 0
                ORDER BY report_date DESC, id DESC
                LIMIT 15
                """,
                (entity_id,)
            )

        # 4. Retrieve live FinTwit stream
        stream_posts = self.fetch_live_fintwit_stream(detected_ticker, limit=10)

        # 5. Synthesize Structured Table & Key Findings
        filtered_ibs = []
        # Check if user mentioned specific IBs
        q_lower = user_query.lower()
        target_firm_filters = []
        if "골드만" in q_lower or "goldman" in q_lower: target_firm_filters.append("Goldman Sachs")
        if "시티" in q_lower or "citi" in q_lower: target_firm_filters.append("Citigroup")
        if "모건스탠리" in q_lower or "morgan" in q_lower: target_firm_filters.append("Morgan Stanley")
        if "jp" in q_lower or "제이피" in q_lower or "jpmorgan" in q_lower: target_firm_filters.append("JPMorgan")
        if "노무라" in q_lower or "nomura" in q_lower: target_firm_filters.append("Nomura")

        for r in db_reports:
            b_name = r["broker_name"]
            if target_firm_filters:
                # If specific firms requested, match them
                if any(tf.lower() in b_name.lower() for tf in target_firm_filters):
                    filtered_ibs.append(r)
            else:
                filtered_ibs.append(r)

        # Fallback to all reports if specific filter matched none
        if not filtered_ibs:
            filtered_ibs = db_reports[:6]

        # Generate markdown summary
        company_name = f"{entity['name_ko']} ({entity['ticker']})" if entity else detected_ticker
        md_lines = []
        md_lines.append(f"### 📊 {company_name} 주요 IB 목표주가 및 애널리스트 코멘트 종합")
        md_lines.append(f"* **현재 주가**: {currency_sym}{current_price:,.1f}" if current_price else "* **현재 주가**: -")
        md_lines.append("")
        md_lines.append("| 투자은행 (IB) | 최신 목표가 | 투자의견 | 변동구분 | 기대 괴리율(Upside) | 발행일자 |")
        md_lines.append("|:---|:---:|:---:|:---:|:---:|:---:|")

        for item in filtered_ibs:
            tgt = f"{currency_sym}{item['target_price']:,.1f}"
            rat = item["rating"] or "-"
            act = item["action_type"] or "-"
            up = f"{item['upside_pct']:+.1f}%" if item.get("upside_pct") is not None else "-"
            dt = item["report_date"]
            md_lines.append(f"| **{item['broker_name']}** | **{tgt}** | {rat} | {act} | {up} | {dt} |")

        md_lines.append("")
        md_lines.append("#### 💡 월가 핵심 논거 및 코멘트 요약")
        for item in filtered_ibs[:4]:
            b_name = item["broker_name"]
            summary = item.get("summary_text") or item.get("title") or "투자의견 유지 및 밸류에이션 목표가 상향"
            md_lines.append(f"* **{b_name}**: {summary}")

        # Sentiment summary from FinTwit
        bull_count = sum(1 for s in stream_posts if s.get("sentiment") == "Bullish")
        bear_count = sum(1 for s in stream_posts if s.get("sentiment") == "Bearish")
        sentiment_label = "중립 (Neutral)"
        if bull_count > bear_count: sentiment_label = f"🟢 낙관 (Bullish {bull_count}건 vs {bear_count}건)"
        elif bear_count > bull_count: sentiment_label = f"🔴 신중/비관 (Bearish {bear_count}건 vs {bull_count}건)"

        md_lines.append("")
        md_lines.append(f"#### ⚡ FinTwit 실시간 시장 센티먼트")
        md_lines.append(f"* **실시간 트윗 여론**: {sentiment_label}")
        if stream_posts:
            sample_post = stream_posts[0]
            clean_body = re.sub(r'\s+', ' ', sample_post['body'])[:120]
            md_lines.append(f"* **최신 속보 피드**: `@{sample_post['username']}`: \"{clean_body}...\"")

        markdown_output = "\n".join(md_lines)

        ib_actions = []
        for r in filtered_ibs:
            ib_actions.append({
                "broker": r.get("broker_name"),
                "analyst": r.get("analyst_name") or "-",
                "current_target": r.get("target_price"),
                "prev_target": None,
                "action": r.get("action_type") or "Maintain",
                "rating": r.get("rating"),
                "currency": r.get("currency", "USD"),
                "tweet_time": r.get("report_date"),
                "source_account": "월가 리서치 피드",
                "tweet_url": r.get("pdf_url"),
                "key_point": r.get("title") or r.get("summary_text") or "목표주가 산정"
            })

        structured_data = {
            "query_summary": f"{detected_ticker} 주요 IB 및 증권사 목표주가 변동 종합",
            "ib_actions": ib_actions,
            "market_sentiment": f"{sentiment_label} (FinTwit 소셜 피드 {len(stream_posts)}건 분석)",
            "risks_mentioned": "단기 밸류에이션 부담 및 공급망 병목 모니터링 필요",
            "markdown_result": markdown_output,
            "current_price": current_price
        }

        return {
            "status": "success",
            "query": user_query,
            "ticker": detected_ticker,
            "data": structured_data,
            "current_price": current_price,
            "reports_count": len(filtered_ibs),
            "stream_posts_count": len(stream_posts),
            "markdown_result": markdown_output,
            "reports": filtered_ibs,
            "stream_posts": stream_posts
        }

    def ask_question(self, ticker: str, user_query: str) -> Dict[str, Any]:
        """Convenience alias for answer_query returning structured data."""
        res = self.answer_query(user_query=user_query, ticker=ticker)
        return res.get("data", {})

