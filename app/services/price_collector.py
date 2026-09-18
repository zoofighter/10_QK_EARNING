"""
Stock Price Collector Service
Collects daily OHLCV stock price history using yfinance.
"""
import yfinance as yf
from app.models.database import get_db, query_db

class PriceCollector:
    def collect_for_entity(self, ticker: str, period="1y"):
        """Fetch historical price data for a ticker and save to DB."""
        entity = query_db("SELECT id, ticker, exchange FROM entity WHERE ticker = ?", (ticker,), one=True)
        if not entity:
            return {"error": f"Entity not found for {ticker}", "count": 0}

        # Handle unlisted companies
        if ticker in ["SPACEX"]:
            return {"ticker": ticker, "status": "SKIPPED", "reason": "Unlisted private company", "count": 0}

        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            if df.empty:
                return {"ticker": ticker, "status": "EMPTY", "count": 0}

            rows_to_insert = []
            for date_idx, row in df.iterrows():
                date_str = date_idx.strftime("%Y-%m-%d")
                rows_to_insert.append((
                    entity["id"],
                    date_str,
                    float(row.get("Open", 0.0)),
                    float(row.get("High", 0.0)),
                    float(row.get("Low", 0.0)),
                    float(row.get("Close", 0.0)),
                    float(row.get("Close", 0.0)), # adj_close approximation if not explicit
                    int(row.get("Volume", 0))
                ))

            with get_db() as conn:
                cur = conn.cursor()
                cur.executemany(
                    """
                    INSERT OR REPLACE INTO stock_price (
                        entity_id, date, open, high, low, close, adj_close, volume
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows_to_insert
                )

            return {
                "ticker": ticker,
                "status": "SUCCESS",
                "count": len(rows_to_insert),
                "latest_date": rows_to_insert[-1][1] if rows_to_insert else None,
                "latest_close": rows_to_insert[-1][5] if rows_to_insert else None
            }
        except Exception as e:
            print(f"[PriceCollector] Error for {ticker}: {e}")
            return {"ticker": ticker, "status": "ERROR", "error": str(e), "count": 0}

    def collect_all_entities(self, period="6mo"):
        """Collect prices for all trackable entities."""
        entities = query_db("SELECT ticker FROM entity WHERE ticker != 'SPACEX'")
        results = []
        for ent in entities:
            res = self.collect_for_entity(ent["ticker"], period=period)
            results.append(res)
        return results
