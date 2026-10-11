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


class LedgerService:
    @classmethod
    def load_ledger(cls, force_reload: bool = False) -> list[dict[str, Any]]:
        global _CACHED_LEDGER
        if _CACHED_LEDGER and not force_reload:
            return _CACHED_LEDGER

        if not LEDGER_FILE.exists():
            return []

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
                    is_twitter = "[𝕏 Radar]" in parts[3]

                    rows.append({
                        "id": len(rows) + 1,
                        "layer": layer_raw,
                        "entity": entity_raw,
                        "name": name,
                        "ticker": ticker,
                        "country": country,
                        "date": parts[2],
                        "content": parts[3],
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
        limit: int = 1000,
        offset: int = 0,
    ) -> dict[str, Any]:
        all_events = cls.load_ledger()
        filtered = all_events

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
