"""
Ledger Service for 2026 Full-Year Unpivoted Event Matrix.
Parses and caches the 8-column ledger data for high-performance API queries.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Any, Optional

LEDGER_FILE = Path(__file__).resolve().parent.parent.parent / "docs" / "2026-10-11_36entities_2026_full_year_layer_matrix.md"

_CACHED_LEDGER: list[dict[str, Any]] = []
_LAST_MTIME: float = 0.0


class LedgerService:
    @classmethod
    def load_ledger(cls, force_reload: bool = False) -> list[dict[str, Any]]:
        global _CACHED_LEDGER, _LAST_MTIME

        if not LEDGER_FILE.exists():
            return []

        current_mtime = LEDGER_FILE.stat().st_mtime
        if _CACHED_LEDGER and not force_reload and (current_mtime == _LAST_MTIME):
            return _CACHED_LEDGER

        _LAST_MTIME = current_mtime

        lines = LEDGER_FILE.read_text(encoding="utf-8").splitlines()
        rows: list[dict[str, Any]] = []
        in_table = False

        for line in lines:
            line_clean = line.strip()
            if line_clean.startswith("| 레이어") or line_clean.startswith("| Layer"):
                in_table = True
                continue
            if in_table and line_clean.startswith("| :---"):
                continue
            if in_table and line_clean.startswith("|"):
                parts = [p.strip() for p in line_clean.split("|")[1:-1]]
                if len(parts) >= 8:
                    layer_raw = parts[0].replace("**", "")
                    entity_raw = parts[1].replace("**", "")

                    # Extract ticker and clean entity name
                    # e.g. "OpenAI (OAI 🇺🇸)" -> name="OpenAI", ticker="OAI", country="🇺🇸"
                    ticker_match = re.search(r"\(([\w\.\-]+)\s*([^\)]*)\)", entity_raw)
                    ticker = ticker_match.group(1) if ticker_match else ""
                    country = ticker_match.group(2).strip() if ticker_match else ""
                    name = re.sub(r"\(.*?\)", "", entity_raw).strip()

                    conf_raw = parts[7].replace("`", "").replace("[", "").replace("]", "").strip()
                    raw_content = parts[3]
                    is_twitter = "[𝕏 Radar]" in raw_content or "[𝕏" in raw_content

                    clean_content = raw_content
                    handle = ""

                    # Clean up: remove [𝕏 Radar] and display name, keep only '@handle: text'
                    if is_twitter:
                        # Match: [𝕏 Radar] PEquity Research(@pequityresearch): body
                        # or: [𝕏 Radar] Dan Nystedt(dnystedt): body
                        tw_match = re.search(r"\[𝕏\s*Radar\]\s*.*?\(@?([a-zA-Z0-9_]+)\)\s*:\s*(.*)", raw_content)
                        if tw_match:
                            h_raw = tw_match.group(1).strip()
                            handle = f"@{h_raw.lstrip('@')}"
                            tweet_body = tw_match.group(2).strip()
                            clean_content = f"{handle}: {tweet_body}"
                        else:
                            # Fallback if pattern slightly varies
                            clean_content = re.sub(r"^\[𝕏\s*Radar\]\s*", "", raw_content)
                            handle_match = re.search(r"\(@?([a-zA-Z0-9_]+)\)", clean_content)
                            if handle_match:
                                h_raw = handle_match.group(1)
                                handle = f"@{h_raw.lstrip('@')}"
                                clean_content = re.sub(r"^.*?\(@?[a-zA-Z0-9_]+\)\s*:\s*", f"{handle}: ", clean_content)

                    rows.append({
                        "id": len(rows) + 1,
                        "layer": layer_raw,
                        "entity": entity_raw,
                        "name": name,
                        "ticker": ticker,
                        "country": country,
                        "date": parts[2],
                        "content": clean_content,
                        "raw_content": raw_content,
                        "handle": handle,
                        "target": parts[4],
                        "metrics": parts[5],
                        "event_type": parts[6],
                        "confidence": conf_raw,
                        "is_twitter": is_twitter,
                    })
            elif in_table and not line_clean.startswith("|") and line_clean != "":
                # Table ended
                pass

        _CACHED_LEDGER = rows
        return _CACHED_LEDGER

    @classmethod
    def get_filtered_events(
        cls,
        ticker: Optional[str] = None,
        layer: Optional[str] = None,
        month: Optional[str] = None,
        confidence: Optional[str] = None,
        query: Optional[str] = None,
        order: str = "desc",
        limit: int = 1000,
        offset: int = 0,
    ) -> dict[str, Any]:
        all_events = cls.load_ledger()
        filtered = list(all_events)

        if ticker:
            ticker_upper = ticker.strip().upper()
            filtered = [
                e for e in filtered
                if ticker_upper in e["ticker"].upper() or ticker_upper in e["name"].upper()
            ]

        if layer and layer != "ALL":
            filtered = [e for e in filtered if layer.lower() in e["layer"].lower()]

        if month and month != "ALL":
            filtered = [e for e in filtered if e["date"].startswith(month)]

        if confidence and confidence != "ALL":
            conf_list = [c.strip().upper() for c in confidence.split(",")]
            filtered = [e for e in filtered if e["confidence"].upper() in conf_list]

        if query:
            q_lower = query.strip().lower()
            filtered = [
                e for e in filtered
                if q_lower in e["content"].lower()
                or q_lower in e["target"].lower()
                or q_lower in e["metrics"].lower()
                or q_lower in e["entity"].lower()
            ]

        # Sort by date: default descending (최신순: 2026-10 -> 2026-01)
        is_desc = (order.lower() != "asc")
        filtered.sort(key=lambda e: (e["date"], e["id"]), reverse=is_desc)

        total_count = len(filtered)
        paginated = filtered[offset : offset + limit]

        # Overall Stats
        h1_count = sum(1 for e in all_events if any(e["date"].startswith(f"2026-0{m}") for m in range(1, 7)))
        h2_count = sum(1 for e in all_events if not any(e["date"].startswith(f"2026-0{m}") for m in range(1, 7)))
        twitter_count = sum(1 for e in all_events if e["is_twitter"])
        fact_count = len(all_events) - twitter_count
        struct_count = sum(1 for e in all_events if e["target"] != "-" or e["metrics"] != "-")

        return {
            "status": "success",
            "total": total_count,
            "events": paginated,
            "stats": {
                "total_events": len(all_events),
                "h1_events": h1_count,
                "h2_events": h2_count,
                "fact_events": fact_count,
                "twitter_events": twitter_count,
                "structured_rate": round((struct_count / len(all_events) * 100), 1) if all_events else 0.0,
            },
        }

    @classmethod
    def export_csv(cls, events: list[dict[str, Any]]) -> str:
        """Export list of events to CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "레이어", "회사이름", "티커", "발생일자", "핵심이벤트", "식별대상", "정량조건", "이벤트유형", "신뢰도", "트위터여부"
        ])
        for e in events:
            writer.writerow([
                e["layer"], e["name"], e["ticker"], e["date"], e["content"],
                e["target"], e["metrics"], e["event_type"], e["confidence"],
                "Y" if e["is_twitter"] else "N"
            ])
        return output.getvalue()

    @classmethod
    def get_recent_monthly_signals(
        cls,
        ticker: str,
        days: int = 30,
        min_score: int = 60,
        limit: int = 6,
        include_fallback: bool = True
    ) -> dict[str, Any]:
        """
        Intelligent filtering for Company Snapshot Timeline:
        Filters top-impact signals from the past 30 days based on importance scoring.
        Applies adaptive fallback window (60 days) if fewer than 3 high-impact signals exist.
        """
        from datetime import datetime, date, timedelta

        all_events = cls.load_ledger()
        ticker_upper = ticker.strip().upper()

        company_events = [
            e for e in all_events
            if ticker_upper in e["ticker"].upper() or ticker_upper in e["name"].upper()
        ]

        if not company_events:
            return {
                "status": "success",
                "ticker": ticker,
                "window": {
                    "days_applied": days,
                    "is_fallback_expanded": False,
                    "total_raw_count": 0,
                    "filtered_count": 0
                },
                "signals": []
            }

        # Determine reference date: use max date found in ledger or current system date
        valid_dates = []
        for e in company_events:
            d_str = e.get("date", "").strip()
            # Handle YYYY-MM-DD
            if re.match(r"^\d{4}-\d{2}-\d{2}$", d_str):
                try:
                    valid_dates.append(datetime.strptime(d_str, "%Y-%m-%d").date())
                except Exception:
                    pass
            elif re.match(r"^\d{4}-\d{2}$", d_str):
                try:
                    valid_dates.append(datetime.strptime(f"{d_str}-15", "%Y-%m-%d").date())
                except Exception:
                    pass

        now_date = datetime.now().date()
        ref_date = max(valid_dates) if valid_dates else now_date
        # If max date is older than system date, use max date as baseline (e.g. 2026-10-11)
        if ref_date < now_date:
            baseline_date = now_date
        else:
            baseline_date = ref_date

        start_date_30 = baseline_date - timedelta(days=days)
        start_date_60 = baseline_date - timedelta(days=days * 2)

        def parse_event_date(d_str: str) -> Optional[date]:
            d_str = d_str.strip()
            if re.match(r"^\d{4}-\d{2}-\d{2}$", d_str):
                try:
                    return datetime.strptime(d_str, "%Y-%m-%d").date()
                except Exception:
                    return None
            elif re.match(r"^\d{4}-\d{2}$", d_str):
                try:
                    return datetime.strptime(f"{d_str}-15", "%Y-%m-%d").date()
                except Exception:
                    return None
            return None

        # Score all company events
        scored_events = []
        for e in company_events:
            ev_date = parse_event_date(e.get("date", ""))
            if not ev_date:
                continue

            days_ago = max(0, (baseline_date - ev_date).days)
            score_data = cls._calculate_importance_score(e, days_ago)

            scored_item = dict(e)
            scored_item["parsed_date"] = ev_date
            scored_item["days_ago"] = days_ago
            scored_item["days_ago_label"] = cls._get_days_ago_label(days_ago)
            scored_item["importance_score"] = score_data["score"]
            scored_item["badge_type"] = score_data["badge_type"]
            scored_item["badge_label"] = score_data["badge_label"]
            scored_item["score_breakdown"] = score_data["breakdown"]
            scored_events.append(scored_item)

        # Collect signals up to target_count = limit (default 10)
        target_count = limit
        selected_events: list[dict[str, Any]] = []
        selected_ids: set[int] = set()
        is_fallback = False

        # Tier 1: Within 30 days & Score >= 60 (High impact)
        t1 = [
            ev for ev in scored_events
            if ev["parsed_date"] >= start_date_30 and ev["importance_score"] >= 60
        ]
        t1.sort(key=lambda x: (x["importance_score"], x["parsed_date"], x["id"]), reverse=True)
        for ev in t1:
            if len(selected_events) < target_count and ev["id"] not in selected_ids:
                selected_events.append(ev)
                selected_ids.add(ev["id"])

        # Tier 2: Within 30 days & Score 40~59 (Moderate impact)
        if len(selected_events) < target_count:
            t2 = [
                ev for ev in scored_events
                if ev["id"] not in selected_ids and ev["parsed_date"] >= start_date_30 and ev["importance_score"] >= 40
            ]
            t2.sort(key=lambda x: (x["importance_score"], x["parsed_date"], x["id"]), reverse=True)
            for ev in t2:
                if len(selected_events) < target_count and ev["id"] not in selected_ids:
                    selected_events.append(ev)
                    selected_ids.add(ev["id"])

        # Tier 3: Within 30 days & Score 20~39 (Minor impact but recent)
        if len(selected_events) < target_count:
            t3 = [
                ev for ev in scored_events
                if ev["id"] not in selected_ids and ev["parsed_date"] >= start_date_30 and ev["importance_score"] >= 20
            ]
            t3.sort(key=lambda x: (x["importance_score"], x["parsed_date"], x["id"]), reverse=True)
            for ev in t3:
                if len(selected_events) < target_count and ev["id"] not in selected_ids:
                    selected_events.append(ev)
                    selected_ids.add(ev["id"])

        # Tier 4: Expand to 60 days (Fallback) & Score >= 40
        if len(selected_events) < target_count and include_fallback:
            is_fallback = True
            t4 = [
                ev for ev in scored_events
                if ev["id"] not in selected_ids and ev["parsed_date"] >= start_date_60 and ev["importance_score"] >= 40
            ]
            t4.sort(key=lambda x: (x["importance_score"], x["parsed_date"], x["id"]), reverse=True)
            for ev in t4:
                if len(selected_events) < target_count and ev["id"] not in selected_ids:
                    selected_events.append(ev)
                    selected_ids.add(ev["id"])

        # Tier 5: Expand to 60 days & Score >= 20
        if len(selected_events) < target_count and include_fallback:
            is_fallback = True
            t5 = [
                ev for ev in scored_events
                if ev["id"] not in selected_ids and ev["parsed_date"] >= start_date_60 and ev["importance_score"] >= 20
            ]
            t5.sort(key=lambda x: (x["importance_score"], x["parsed_date"], x["id"]), reverse=True)
            for ev in t5:
                if len(selected_events) < target_count and ev["id"] not in selected_ids:
                    selected_events.append(ev)
                    selected_ids.add(ev["id"])

        # Tier 6: Final backfill from entire 2026 events of this company to reach 10 items
        if len(selected_events) < target_count:
            is_fallback = True
            t6 = [
                ev for ev in scored_events
                if ev["id"] not in selected_ids
            ]
            t6.sort(key=lambda x: (x["importance_score"], x["parsed_date"], x["id"]), reverse=True)
            for ev in t6:
                if len(selected_events) < target_count and ev["id"] not in selected_ids:
                    selected_events.append(ev)
                    selected_ids.add(ev["id"])

        # Clean non-serializable fields
        for s in selected_events:
            if "parsed_date" in s:
                del s["parsed_date"]

        applied_start = (start_date_60 if is_fallback else start_date_30).strftime("%Y-%m-%d")
        applied_end = baseline_date.strftime("%Y-%m-%d")

        return {
            "status": "success",
            "ticker": ticker,
            "window": {
                "days_applied": (days * 2) if is_fallback else days,
                "start_date": applied_start,
                "end_date": applied_end,
                "is_fallback_expanded": is_fallback,
                "total_company_events": len(company_events),
                "filtered_count": len(selected_events)
            },
            "signals": selected_events
        }

    @classmethod
    def _calculate_importance_score(cls, ev: dict[str, Any], days_ago: int) -> dict[str, Any]:
        """
        Importance Score Formula:
        Score = S_conf (max 35) + S_type (max 30) + S_scale (max 25) + S_recency (max 10) - Penalties
        """
        content = (ev.get("content") or "").strip()
        metrics = (ev.get("metrics") or "").strip()
        event_type = (ev.get("event_type") or "").strip()
        confidence = (ev.get("confidence") or "").strip().upper()
        target = (ev.get("target") or "").strip()
        combined_text = f"{content} {metrics} {event_type} {target}".lower()

        # 1. S_conf (max 35)
        s_conf = 0
        if "C4" in confidence:
            s_conf = 35
        elif "C3" in confidence:
            s_conf = 25
        elif "C2" in confidence:
            s_conf = 10
        else:
            s_conf = 0

        # 2. S_type (max 30)
        s_type = 10
        deal_keywords = ["공급계약", "물품계약", "컴퓨트계약", "수주", "계약 체결", "독점 공급", "선계약", "수주계약"]
        capital_keywords = ["자본유치", "자본공급", "지분투자", "전략적 투자", "시리즈", "펀딩", "출자", "인수", "유치"]
        infra_keywords = ["팹캐파", "데이터센터", "전력ppa", "원전", "수전", "변전소", "cowos", "증설", "클러스터", "메가팹"]
        milestone_keywords = ["마일스톤", "퀄", "qual", "양산", "테이프아웃", "정식 출시", "출시", "도입", "벤치마크 1위"]

        if any(k in combined_text for k in deal_keywords):
            s_type = 30
        elif any(k in combined_text for k in capital_keywords):
            s_type = 30
        elif any(k in combined_text for k in infra_keywords):
            s_type = 25
        elif any(k in combined_text for k in milestone_keywords):
            s_type = 20
        elif "실적" in combined_text or "공시" in combined_text:
            s_type = 20
        elif "공급망속보" in combined_text or "속보" in combined_text:
            s_type = 15

        # 3. S_scale (max 25)
        s_scale = 0
        # Mega scale: $10B+, 500MW+, 100k GPU+, 조원
        mega_patterns = [
            r"\$\s*([1-9]\d{1,3}|\d{2,})\.?\d*\s*[bB]",  # $10B ~ $999B
            r"[1-9]\d*\s*조원",
            r"([5-9]\d{2}|\d{4,})\s*mw",                 # 500MW ~
            r"\d+\s*gw",                                 # GW
            r"(1\d{2}|\d{3,})\s*k\s*(gpu|chip)",        # 100k GPUs ~
        ]
        major_patterns = [
            r"\$\s*[1-9]\.?\d*\s*[bB]",                  # $1B ~ $9.9B
            r"(1\d{2}|[2-4]\d{2})\s*mw",                 # 100MW ~ 499MW
            r"\d+\s*k\s*(gpu|wspm)",
        ]
        minor_patterns = [
            r"\$\s*\d+\.?\d*\s*[mM]",                    # $M
            r"\d+\s*mw",
            r"\d+\s*억",
        ]

        if any(re.search(pat, combined_text) for pat in mega_patterns):
            s_scale = 25
        elif any(re.search(pat, combined_text) for pat in major_patterns):
            s_scale = 15
        elif any(re.search(pat, combined_text) for pat in minor_patterns):
            s_scale = 10

        # 4. S_recency (max 10)
        s_recency = 0
        if days_ago <= 7:
            s_recency = 10
        elif days_ago <= 14:
            s_recency = 5
        elif days_ago <= 30:
            s_recency = 0
        else:
            s_recency = -5

        # 5. Penalties for pure social chatter / low-information noise
        penalties = 0
        noise_phrases = [
            "weekly claude limit", "my weekly limit", "haven't touched claude",
            "to the moon", "chart analysis", "personal opinion", "resigned from",
            "bury my talent", "translated by", "sound on please", "rt @"
        ]
        if any(p in combined_text for p in noise_phrases):
            penalties += 25

        # If twitter event but no target and no metric
        if ev.get("is_twitter") and target in ("-", "") and metrics in ("-", ""):
            penalties += 15

        raw_score = s_conf + s_type + s_scale + s_recency - penalties
        final_score = min(100, max(0, raw_score))

        # Assign Badge
        if final_score >= 85 or ("C4" in confidence and s_scale >= 15):
            badge_type = "MEGA_DEAL"
            badge_label = "🔥 MEGA DEAL"
        elif final_score >= 70 or any(k in combined_text for k in ["양산", "테이프아웃", "2nm", "독점"]):
            badge_type = "INFLECTION"
            badge_label = "⚡ 핵심 변곡점"
        elif "C4" in confidence:
            badge_type = "OFFICIAL"
            badge_label = "📑 공식 공시"
        elif ev.get("is_twitter") and final_score >= 50:
            badge_type = "X_RADAR"
            badge_label = "𝕏 단독 레이더"
        elif final_score >= 50:
            badge_type = "KEY_SIGNAL"
            badge_label = "📌 주요 시그널"
        elif final_score >= 35:
            badge_type = "TREND"
            badge_label = "💡 업계 동향"
        else:
            badge_type = "RADAR"
            badge_label = "💬 소셜 레이더"

        return {
            "score": final_score,
            "badge_type": badge_type,
            "badge_label": badge_label,
            "breakdown": {
                "conf": s_conf,
                "type": s_type,
                "scale": s_scale,
                "recency": s_recency,
                "penalties": penalties
            }
        }

    @classmethod
    def _get_days_ago_label(cls, days_ago: int) -> str:
        if days_ago == 0:
            return "오늘"
        elif days_ago == 1:
            return "어제"
        elif days_ago < 7:
            return f"{days_ago}일 전"
        elif days_ago < 30:
            weeks = days_ago // 7
            return f"{weeks}주 전"
        else:
            months = days_ago // 30
            return f"{months}달 전"

