"""
Global Investment Bank (IB) Target Price & Consensus Collector
Tracks target prices, ratings, and revisions from Goldman Sachs, Citi, J.P. Morgan, Morgan Stanley, etc.
"""
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import yfinance as yf
from app.config import GLOBAL_IB_TIERS, GLOBAL_IB_ALIASES
from app.models.database import query_db, execute_db

logger = logging.getLogger(__name__)

class IBTargetCollector:
    def __init__(self):
        pass

    def _normalize_broker_name(self, raw_firm: str) -> str:
        """Map raw firm name to standard normalized broker name."""
        if not raw_firm:
            return "Wall Street Analyst"
        clean = raw_firm.strip()
        for norm_name, aliases in GLOBAL_IB_ALIASES.items():
            for alias in aliases:
                if alias.lower() in clean.lower():
                    return norm_name
        return clean

    @staticmethod
    def get_broker_tier(broker_name: str) -> str:
        """Return TIER_1, TIER_2, TIER_3, or TIER_OTHER for a given broker name."""
        if not broker_name:
            return "TIER_OTHER"
        b_clean = broker_name.strip()
        for tier_key, brokers in GLOBAL_IB_TIERS.items():
            for b in brokers:
                if b.lower() == b_clean.lower():
                    return tier_key
        return "TIER_OTHER"

    def _map_action_type(self, raw_action: str) -> str:
        """Normalize action string to Maintain, Upgrade, Downgrade, Initiate."""
        if not raw_action:
            return "Maintain"
        act = str(raw_action).lower().strip()
        if "up" in act or "raise" in act:
            return "Upgrade"
        elif "down" in act or "cut" in act or "lower" in act:
            return "Downgrade"
        elif "init" in act:
            return "Initiate"
        elif "reit" in act or "main" in act:
            return "Maintain"
        return "Maintain"

    def collect_ib_targets_for_ticker(self, ticker: str, limit_actions: int = 50) -> Dict[str, Any]:
        """
        Collect analyst target prices, consensus mean/high/low, and IB revisions for a ticker.
        Saves individual actions to `analyst_report` and consensus snapshot to `target_price_history`.
        """
        entity = query_db("SELECT id, ticker, name_en, name_ko, country FROM entity WHERE ticker = ?", (ticker,), one=True)
        entity_id = entity["id"] if entity else None

        if not entity_id:
            logger.warning(f"Entity for ticker {ticker} not found in database")

        logger.info(f"Collecting IB targets and consensus for {ticker} via yfinance")
        yt = yf.Ticker(ticker)

        # 1. Consensus stats from info
        info = {}
        try:
            info = yt.info or {}
        except Exception as e:
            logger.warning(f"Failed to fetch info for {ticker}: {e}")

        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        target_median = info.get("targetMedianPrice")
        num_analysts = info.get("numberOfAnalystOpinions")
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")

        # Fallback for current price if not in info
        if not current_price and entity_id:
            latest_price_row = query_db(
                "SELECT close FROM stock_price WHERE entity_id = ? ORDER BY date DESC LIMIT 1",
                (entity_id,),
                one=True
            )
            if latest_price_row:
                current_price = float(latest_price_row["close"])

        # 2. Extract recent upgrades and downgrades
        actions_saved = 0
        key_ib_snapshots = {}
        parsed_actions = []

        try:
            ud = yt.upgrades_downgrades
            if ud is not None and not ud.empty:
                # Upgrades/downgrades has GradeDate as index
                ud_reset = ud.reset_index()
                
                # Sort by date descending
                date_col = "GradeDate" if "GradeDate" in ud_reset.columns else ud_reset.columns[0]
                ud_reset = ud_reset.sort_values(by=date_col, ascending=False).head(limit_actions)

                for _, row in ud_reset.iterrows():
                    raw_firm = str(row.get("Firm", "")).strip()
                    if not raw_firm or raw_firm.lower() == "nan":
                        continue

                    broker_name = self._normalize_broker_name(raw_firm)
                    
                    # Date formatting
                    grade_date_val = row.get(date_col)
                    if isinstance(grade_date_val, (datetime, date)):
                        report_date = grade_date_val.strftime("%Y-%m-%d")
                    else:
                        report_date = str(grade_date_val)[:10]

                    rating = str(row.get("ToGrade", "")).strip()
                    if rating.lower() == "nan":
                        rating = "Buy"

                    raw_action = str(row.get("Action", "")).strip()
                    action_type = self._map_action_type(raw_action)

                    # Target price parsing
                    cpt = row.get("currentPriceTarget")
                    target_price = None
                    if cpt is not None and str(cpt).lower() != "nan":
                        try:
                            val = float(cpt)
                            if val > 0:
                                target_price = val
                        except (ValueError, TypeError):
                            pass

                    # Upside %
                    upside_pct = None
                    if target_price and current_price and current_price > 0:
                        upside_pct = round(((target_price - current_price) / current_price) * 100.0, 2)

                    # Title description
                    title = f"{broker_name} {action_type} to {rating}"
                    if target_price:
                        title += f" (PT: ${target_price:.1f})"

                    # Save to latest key IB snapshot
                    if broker_name not in key_ib_snapshots and target_price:
                        key_ib_snapshots[broker_name] = {
                            "target_price": target_price,
                            "rating": rating,
                            "action": action_type,
                            "date": report_date
                        }

                    # Save to DB analyst_report
                    if entity_id:
                        try:
                            execute_db(
                                """
                                INSERT INTO analyst_report (
                                    entity_id, ticker, source_type, broker_name, analyst_name,
                                    report_date, title, rating, action_type, target_price,
                                    current_price_at_report, upside_pct, currency, summary_text
                                ) VALUES (?, ?, 'GLOBAL_IB', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'USD', ?)
                                ON CONFLICT(entity_id, broker_name, report_date, title) DO UPDATE SET
                                    target_price = COALESCE(excluded.target_price, analyst_report.target_price),
                                    rating = excluded.rating,
                                    upside_pct = COALESCE(excluded.upside_pct, analyst_report.upside_pct)
                                """,
                                (
                                    entity_id, ticker, broker_name, None,
                                    report_date, title, rating, action_type, target_price,
                                    current_price, upside_pct, f"Wall Street research action by {broker_name}"
                                )
                            )
                            actions_saved += 1
                        except Exception as e:
                            logger.warning(f"Error saving IB action {title}: {e}")

                    parsed_actions.append({
                        "broker_name": broker_name,
                        "report_date": report_date,
                        "title": title,
                        "rating": rating,
                        "action_type": action_type,
                        "target_price": target_price,
                        "upside_pct": upside_pct
                    })
        except Exception as e:
            logger.warning(f"Failed to parse upgrades/downgrades for {ticker}: {e}")

        # 3. Save daily consensus history to `target_price_history`
        today_str = date.today().strftime("%Y-%m-%d")
        if entity_id and (target_mean or current_price):
            try:
                execute_db(
                    """
                    INSERT INTO target_price_history (
                        entity_id, date, close_price, target_mean, target_high,
                        target_low, num_analysts, key_ib_targets_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(entity_id, date) DO UPDATE SET
                        close_price = excluded.close_price,
                        target_mean = excluded.target_mean,
                        target_high = excluded.target_high,
                        target_low = excluded.target_low,
                        num_analysts = excluded.num_analysts,
                        key_ib_targets_json = excluded.key_ib_targets_json
                    """,
                    (
                        entity_id, today_str, current_price or 0.0,
                        target_mean, target_high, target_low, num_analysts,
                        json.dumps(key_ib_snapshots, ensure_ascii=False)
                    )
                )
                logger.info(f"Saved consensus snapshot for {ticker} on {today_str}")
            except Exception as e:
                logger.warning(f"Failed to save target_price_history for {ticker}: {e}")

        return {
            "ticker": ticker,
            "entity_id": entity_id,
            "current_price": current_price,
            "consensus": {
                "mean": target_mean,
                "high": target_high,
                "low": target_low,
                "median": target_median,
                "num_analysts": num_analysts,
                "upside_mean_pct": round(((target_mean - current_price) / current_price) * 100.0, 2) if target_mean and current_price else None
            },
            "key_ib_snapshots": key_ib_snapshots,
            "actions_saved": actions_saved,
            "actions": parsed_actions
        }
