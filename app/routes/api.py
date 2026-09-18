"""
REST API Routes for QK_EARNING Application
"""
from datetime import datetime, date
from flask import Blueprint, jsonify, request
from app.models.database import query_db, execute_db
from app.services.edgar_collector import EdgarCollector
from app.services.price_collector import PriceCollector
from app.services.kr_export_collector import KoreaExportCollector, INDICATOR_TYPES as KR_INDICATOR_TYPES

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/stats", methods=["GET"])
def get_stats():
    """System overview summary statistics."""
    company_count = query_db("SELECT COUNT(*) as cnt FROM entity", one=True)["cnt"]
    filing_count = query_db("SELECT COUNT(*) as cnt FROM filing", one=True)["cnt"]
    layer_count = query_db("SELECT COUNT(*) as cnt FROM layer", one=True)["cnt"]
    price_count = query_db("SELECT COUNT(DISTINCT entity_id) as cnt FROM stock_price", one=True)["cnt"]

    # Upcoming earnings countdown
    today_str = date.today().strftime("%Y-%m-%d")
    upcoming = query_db(
        """
        SELECT ec.id, ec.fiscal_year, ec.fiscal_quarter, ec.expected_date, ec.call_time_et,
               e.ticker, e.name_en, e.name_ko, e.layer_code
        FROM earning_calendar ec
        JOIN entity e ON ec.entity_id = e.id
        WHERE ec.expected_date >= ?
        ORDER BY ec.expected_date ASC
        LIMIT 5
        """,
        (today_str,)
    )

    for item in upcoming:
        try:
            exp_d = datetime.strptime(item["expected_date"], "%Y-%m-%d").date()
            diff = (exp_d - date.today()).days
            item["d_day"] = f"D-{diff}" if diff > 0 else ("D-Day" if diff == 0 else f"D+{abs(diff)}")
        except Exception:
            item["d_day"] = "-"

    # Layer distribution
    layers = query_db(
        """
        SELECT l.code, l.name_ko, l.name_en, COUNT(e.id) as entity_count
        FROM layer l
        LEFT JOIN entity e ON l.code = e.layer_code
        GROUP BY l.code
        ORDER BY l.sort_order ASC
        """
    )

    return jsonify({
        "status": "success",
        "data": {
            "company_count": company_count,
            "filing_count": filing_count,
            "layer_count": layer_count,
            "price_tracked_count": price_count,
            "upcoming_earnings": upcoming,
            "layers": layers
        }
    })

@api_bp.route("/layers", methods=["GET"])
def get_layers():
    """List all layers."""
    layers = query_db("SELECT * FROM layer ORDER BY sort_order ASC")
    return jsonify({"status": "success", "data": layers})

@api_bp.route("/entities", methods=["GET"])
def get_entities():
    """List entities with optional layer filter and search."""
    layer = request.args.get("layer")
    search = request.args.get("search")

    query = """
        SELECT e.*, l.name_ko as layer_name_ko, l.name_en as layer_name_en,
               (SELECT COUNT(*) FROM filing f WHERE f.entity_id = e.id) as filing_count,
               (SELECT close FROM stock_price sp WHERE sp.entity_id = e.id ORDER BY sp.date DESC LIMIT 1) as latest_close,
               (SELECT date FROM stock_price sp WHERE sp.entity_id = e.id ORDER BY sp.date DESC LIMIT 1) as latest_price_date
        FROM entity e
        JOIN layer l ON e.layer_code = l.code
        WHERE 1=1
    """
    params = []

    if layer:
        query += " AND e.layer_code = ?"
        params.append(layer)

    if search:
        query += " AND (e.ticker LIKE ? OR e.name_en LIKE ? OR e.name_ko LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " ORDER BY l.sort_order ASC, e.ticker ASC"
    entities = query_db(query, params)
    return jsonify({"status": "success", "data": entities, "count": len(entities)})

@api_bp.route("/entities/<ticker>", methods=["GET"])
def get_entity_detail(ticker):
    """Detailed profile for a specific company."""
    entity = query_db(
        """
        SELECT e.*, l.name_ko as layer_name_ko, l.name_en as layer_name_en
        FROM entity e
        JOIN layer l ON e.layer_code = l.code
        WHERE e.ticker = ?
        """,
        (ticker,),
        one=True
    )
    if not entity:
        return jsonify({"status": "error", "message": f"Entity {ticker} not found"}), 404

    filings = query_db(
        """
        SELECT id, filing_type, fiscal_year, fiscal_quarter, filed_date, period_end_date,
               accession_number, source_url, status
        FROM filing
        WHERE entity_id = ?
        ORDER BY filed_date DESC
        LIMIT 20
        """,
        (entity["id"],)
    )

    prices = query_db(
        """
        SELECT date, open, high, low, close, volume
        FROM stock_price
        WHERE entity_id = ?
        ORDER BY date DESC
        LIMIT 30
        """,
        (entity["id"],)
    )

    calendar = query_db(
        """
        SELECT fiscal_year, fiscal_quarter, expected_date, call_time_et, status
        FROM earning_calendar
        WHERE entity_id = ?
        ORDER BY expected_date DESC
        LIMIT 5
        """,
        (entity["id"],)
    )

    return jsonify({
        "status": "success",
        "data": {
            "entity": entity,
            "filings": filings,
            "recent_prices": list(reversed(prices)),
            "calendar": calendar
        }
    })

@api_bp.route("/filings", methods=["GET"])
def get_filings():
    """List filings with filter options."""
    ticker = request.args.get("ticker")
    form_type = request.args.get("type")
    limit = int(request.args.get("limit", 50))

    query = """
        SELECT f.id, f.filing_type, f.fiscal_year, f.fiscal_quarter, f.period_end_date,
               f.filed_date, f.accession_number, f.source_url, f.status,
               e.ticker, e.name_en, e.name_ko, e.layer_code
        FROM filing f
        JOIN entity e ON f.entity_id = e.id
        WHERE 1=1
    """
    params = []

    if ticker:
        query += " AND e.ticker = ?"
        params.append(ticker)

    if form_type:
        query += " AND f.filing_type = ?"
        params.append(form_type)

    query += " ORDER BY f.filed_date DESC LIMIT ?"
    params.append(limit)

    filings = query_db(query, params)
    return jsonify({"status": "success", "data": filings, "count": len(filings)})

@api_bp.route("/filings/<int:filing_id>", methods=["GET"])
def get_filing_detail(filing_id):
    """Filing detail including text excerpt."""
    filing = query_db(
        """
        SELECT f.*, e.ticker, e.name_en, e.name_ko, e.layer_code
        FROM filing f
        JOIN entity e ON f.entity_id = e.id
        WHERE f.id = ?
        """,
        (filing_id,),
        one=True
    )
    if not filing:
        return jsonify({"status": "error", "message": "Filing not found"}), 404

    # Provide safe preview of raw text
    text_preview = (filing.get("raw_text") or "")[:5000]
    result = dict(filing)
    result["raw_text_preview"] = text_preview
    result.pop("raw_text", None)

    return jsonify({"status": "success", "data": result})

@api_bp.route("/calendar", methods=["GET"])
def get_calendar():
    """Earnings calendar entries."""
    rows = query_db(
        """
        SELECT ec.*, e.ticker, e.name_en, e.name_ko, e.layer_code
        FROM earning_calendar ec
        JOIN entity e ON ec.entity_id = e.id
        ORDER BY ec.expected_date ASC
        """
    )
    for r in rows:
        try:
            exp = datetime.strptime(r["expected_date"], "%Y-%m-%d").date()
            diff = (exp - date.today()).days
            r["days_left"] = diff
            r["d_day"] = f"D-{diff}" if diff > 0 else ("D-Day" if diff == 0 else f"D+{abs(diff)}")
        except Exception:
            r["days_left"] = 999
            r["d_day"] = "-"

    return jsonify({"status": "success", "data": rows, "count": len(rows)})

@api_bp.route("/prices/<ticker>", methods=["GET"])
def get_prices(ticker):
    """Historical stock prices for chart."""
    limit = int(request.args.get("limit", 90))
    entity = query_db("SELECT id FROM entity WHERE ticker = ?", (ticker,), one=True)
    if not entity:
        return jsonify({"status": "error", "message": "Entity not found"}), 404

    prices = query_db(
        """
        SELECT date, open, high, low, close, volume
        FROM stock_price
        WHERE entity_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (entity["id"], limit)
    )
    return jsonify({"status": "success", "ticker": ticker, "data": list(reversed(prices))})

@api_bp.route("/collect/trigger", methods=["POST"])
def trigger_collection():
    """Trigger manual data collection for filings or stock prices."""
    payload = request.get_json() or {}
    target_type = payload.get("type", "filings") # 'filings' or 'prices'
    ticker = payload.get("ticker")

    if target_type == "filings":
        collector = EdgarCollector()
        if ticker:
            res = collector.collect_for_entity(ticker, form_types=["10-Q", "10-K", "8-K"], limit=10, download_docs=False)
            return jsonify({"status": "success", "result": res})
        else:
            # Batch collect for top AI firms
            sample_tickers = ["NVDA", "GOOGL", "MSFT", "AMZN", "META", "AMD", "TSM", "MU"]
            results = []
            for t in sample_tickers:
                r = collector.collect_for_entity(t, form_types=["10-Q", "10-K"], limit=5, download_docs=False)
                results.append(r)
            return jsonify({"status": "success", "batch_results": results})

    elif target_type == "prices":
        collector = PriceCollector()
        if ticker:
            res = collector.collect_for_entity(ticker, period="6mo")
            return jsonify({"status": "success", "result": res})
        else:
            res = collector.collect_all_entities(period="3mo")
            return jsonify({"status": "success", "batch_results": res})

    return jsonify({"status": "error", "message": "Invalid target type"}), 400

@api_bp.route("/search", methods=["GET"])
def search_fts():
    """Full-text search in filings."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"status": "success", "data": []})

    try:
        results = query_db(
            """
            SELECT f.filing_id, f.ticker, f.filing_type, f.fiscal_period,
                   snippet(filing_fts, 4, '<mark>', '</mark>', '...', 25) as snippet
            FROM filing_fts f
            WHERE filing_fts MATCH ?
            ORDER BY rank
            LIMIT 20
            """,
            (q,)
        )
        return jsonify({"status": "success", "query": q, "data": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ─── Industry Indicators ───

@api_bp.route("/indicators", methods=["GET"])
def get_indicators():
    """Retrieve industry leading indicators with type/date filtering."""
    ind_type = request.args.get("type")
    limit = int(request.args.get("limit", 100))

    if ind_type:
        rows = query_db(
            "SELECT * FROM industry_indicator WHERE indicator_type = ? ORDER BY date DESC LIMIT ?",
            (ind_type, limit)
        )
    else:
        rows = query_db(
            "SELECT * FROM industry_indicator ORDER BY date DESC, indicator_type ASC LIMIT ?",
            (limit,)
        )
    return jsonify({"status": "success", "data": rows, "count": len(rows)})

@api_bp.route("/indicators", methods=["POST"])
def add_indicator():
    """Add a manual industry indicator entry."""
    payload = request.get_json() or {}
    required = ["indicator_type", "date", "value"]
    for field in required:
        if field not in payload:
            return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400

    execute_db(
        """
        INSERT INTO industry_indicator (indicator_type, date, value, unit, source, note)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(indicator_type, date)
        DO UPDATE SET value=excluded.value, unit=excluded.unit, source=excluded.source, note=excluded.note
        """,
        (
            payload["indicator_type"], payload["date"], payload["value"],
            payload.get("unit", ""), payload.get("source", "MANUAL"),
            payload.get("note", "")
        )
    )
    return jsonify({"status": "success", "message": "Indicator added/updated"})

# ─── Korea Semiconductor Export (순별) ───

@api_bp.route("/indicators/kr-export", methods=["GET"])
def get_kr_export():
    """Retrieve Korea 10-day semiconductor export data."""
    collector = KoreaExportCollector()
    ind_type = request.args.get("type", "KR_SEMI_EXPORT_AMT")
    limit = int(request.args.get("limit", 36))
    data = collector.get_export_history(indicator_type=ind_type, limit=limit)
    return jsonify({
        "status": "success",
        "indicator_info": KR_INDICATOR_TYPES.get(ind_type, {}),
        "data": data,
        "count": len(data)
    })

@api_bp.route("/indicators/kr-export", methods=["POST"])
def add_kr_export():
    """Add a 10-day Korea semiconductor export report (관세청 순별 잠정치)."""
    payload = request.get_json() or {}
    required = ["year", "month", "period", "semi_export_amt"]
    for field in required:
        if field not in payload:
            return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400

    collector = KoreaExportCollector()
    result = collector.add_10day_report(
        year=int(payload["year"]),
        month=int(payload["month"]),
        period=payload["period"],  # 상순, 중순, 하순
        semi_export_amt=float(payload["semi_export_amt"]),
        semi_yoy_pct=payload.get("semi_yoy_pct"),
        total_export_amt=payload.get("total_export_amt"),
        note=payload.get("note")
    )
    return jsonify(result)

@api_bp.route("/indicators/kr-export/types", methods=["GET"])
def get_kr_indicator_types():
    """Return available Korea export indicator types and their metadata."""
    return jsonify({"status": "success", "data": KR_INDICATOR_TYPES})
