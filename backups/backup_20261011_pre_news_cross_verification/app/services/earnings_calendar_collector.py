"""
Earnings Calendar Collector Service.
Synchronizes real-time earnings announcement dates (Earnings Date)
and conference call times from Yahoo Finance (yfinance) for all value chain entities.
"""
import logging
from datetime import date, datetime
from typing import Dict, Any, List, Optional
import yfinance as yf

from app.models.database import get_db, query_db

logger = logging.getLogger(__name__)


class EarningsCalendarCollector:
    """Collects and syncs real-world earnings dates into earning_calendar table."""

    def sync_calendar_for_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Sync earnings calendar date for a single ticker."""
        entity = query_db(
            "SELECT id, ticker, name_en, name_ko, fiscal_year_end FROM entity WHERE ticker = ?",
            (ticker,),
            one=True
        )
        if not entity:
            return None

        try:
            cal = yf.Ticker(ticker).calendar
            ed = cal.get("Earnings Date") if cal else None
            if not ed or len(ed) == 0:
                return None

            exp_date_obj = ed[0]
            exp_date_str = str(exp_date_obj)

            # Conference call time heuristic (ET)
            if ticker in ("TSM", "ASML", "000660.KS", "005930.KS"):
                call_time = "09:00"
            elif ticker in ("ORCL", "NVDA", "META", "MSFT", "AMZN", "AAPL", "AMD", "INTC", "GOOGL"):
                call_time = "17:00"
            else:
                call_time = "16:30"

            today = date.today()
            diff = (exp_date_obj - today).days
            status = "CONFIRMED" if 0 <= diff <= 30 else ("COMPLETED" if diff < 0 else "UPCOMING")

            # Determine fiscal quarter respecting fiscal_year_end
            m = exp_date_obj.month
            y = exp_date_obj.year
            fy_end = entity["fiscal_year_end"] or "12"

            if m in (10, 11):
                fq = "Q3"
                fy = str(y)
                if fy_end == "06":  # MSFT, LRCX, KLAC, WDC
                    fy = str(y + 1)
                    fq = "Q1"
                elif fy_end == "09":  # AAPL
                    fq = "Q4"
            elif m in (12, 1):
                fq = "Q4" if fy_end == "12" else "Q2"
                fy = str(y + 1) if fy_end in ("05", "06") else str(y)
            elif m in (8, 9):
                fq = "Q1" if fy_end in ("05", "06") else "Q3"
                fy = str(y + 1) if fy_end in ("05", "06") else str(y)
            elif m in (2, 3):
                fq = "Q4" if fy_end == "01" else ("Q3" if fy_end == "05" else "Q1")
                fy = str(y)
            else:
                fq = "Q2"
                fy = str(y)

            with get_db() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO earning_calendar (
                        entity_id, fiscal_year, fiscal_quarter, expected_date, call_time_et, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(entity_id, fiscal_year, fiscal_quarter)
                    DO UPDATE SET expected_date = excluded.expected_date,
                                  call_time_et = excluded.call_time_et,
                                  status = excluded.status
                    """,
                    (entity["id"], fy, fq, exp_date_str, call_time, status)
                )

            return {
                "ticker": ticker,
                "expected_date": exp_date_str,
                "fiscal_period": f"{fy}-{fq}",
                "call_time_et": call_time,
                "status": status,
                "days_left": diff
            }
        except Exception as e:
            logger.warning(f"[CalendarCollector] Failed to fetch {ticker}: {e}")
            return None

    def sync_calendar_all_entities(self) -> Dict[str, Any]:
        """Synchronize earnings dates for all 34 entities in the database."""
        entities = query_db("SELECT id, ticker, name_en, name_ko FROM entity ORDER BY id")
        synced: List[Dict[str, Any]] = []
        skipped: List[str] = []

        for e in entities:
            res = self.sync_calendar_for_ticker(e["ticker"])
            if res:
                synced.append(res)
            else:
                skipped.append(e["ticker"])

        return {
            "status": "success",
            "total_entities": len(entities),
            "synced_count": len(synced),
            "synced": synced,
            "skipped": skipped
        }
