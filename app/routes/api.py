"""
REST API Routes for QK_EARNING Application
"""
from datetime import datetime, date
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file
from app.models.database import query_db, execute_db
from app.services.edgar_collector import EdgarCollector
from app.services.price_collector import PriceCollector
from app.services.kr_export_collector import KoreaExportCollector, INDICATOR_TYPES as KR_INDICATOR_TYPES
from app.services.consensus_service import ConsensusService
from app.services.memory_spot_collector import MemorySpotCollector, MEMORY_SPOT_TYPES
from app.services.financial_service import FinancialService
from app.services.filing_section_extractor import FilingSectionExtractor
from app.services.transcript_collector import TranscriptCollector

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
    """Filing detail including text excerpt and download status."""
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
    raw_text = filing.get("raw_text") or ""
    text_preview = raw_text[:8000]
    result = dict(filing)
    result["raw_text_preview"] = text_preview
    result["raw_text_length"] = len(raw_text)
    result["has_local_file"] = bool(filing.get("local_file_path") and Path(filing.get("local_file_path")).exists())
    result.pop("raw_text", None)

    return jsonify({"status": "success", "data": result})

@api_bp.route("/filings/<int:filing_id>/text", methods=["GET"])
def get_filing_full_text(filing_id):
    """Retrieve full text content of a filing."""
    filing = query_db(
        """
        SELECT f.id, f.filing_type, f.fiscal_year, f.fiscal_quarter, f.filed_date,
               f.raw_text, e.ticker, e.name_en, e.name_ko
        FROM filing f
        JOIN entity e ON f.entity_id = e.id
        WHERE f.id = ?
        """,
        (filing_id,),
        one=True
    )
    if not filing:
        return jsonify({"status": "error", "message": "Filing not found"}), 404

    return jsonify({
        "status": "success",
        "data": {
            "id": filing["id"],
            "ticker": filing["ticker"],
            "name_en": filing["name_en"],
            "form": filing["filing_type"],
            "period": f"{filing['fiscal_year']}-{filing['fiscal_quarter']}",
            "filed_date": filing["filed_date"],
            "text": filing["raw_text"] or "(원문 텍스트가 아직 수집되지 않았습니다. 원문 다운로드를 실행해 주세요.)"
        }
    })

@api_bp.route("/filings/<int:filing_id>/download", methods=["POST"])
def download_filing(filing_id):
    """Download filing raw document and update text/FTS index on demand."""
    collector = EdgarCollector()
    res = collector.download_single_filing(filing_id)
    if res.get("status") == "error":
        return jsonify(res), 400
    return jsonify(res)

@api_bp.route("/filings/<int:filing_id>/raw", methods=["GET"])
def get_filing_raw_file(filing_id):
    """Serve the downloaded local HTML file directly."""
    filing = query_db("SELECT local_file_path FROM filing WHERE id = ?", (filing_id,), one=True)
    if not filing or not filing["local_file_path"]:
        return jsonify({"status": "error", "message": "Local file not found"}), 404

    path = Path(filing["local_file_path"])
    if not path.exists():
        return jsonify({"status": "error", "message": "File does not exist on disk"}), 404

    return send_file(path, mimetype="text/html")

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
    download_docs = payload.get("download_docs", True)

    if target_type == "filings":
        collector = EdgarCollector()
        if ticker:
            res = collector.collect_for_entity(ticker, form_types=["10-Q", "10-K", "8-K"], limit=10, download_docs=download_docs)
            return jsonify({"status": "success", "result": res})
        else:
            # Batch collect for top AI firms
            sample_tickers = ["NVDA", "GOOGL", "MSFT", "AMZN", "META", "AMD", "TSM", "MU"]
            results = []
            for t in sample_tickers:
                r = collector.collect_for_entity(t, form_types=["10-Q", "10-K"], limit=5, download_docs=download_docs)
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

@api_bp.route("/indicators/kr-export/seed", methods=["POST"])
def seed_kr_export():
    """Seed sample Korea 10-day semiconductor export stats."""
    collector = KoreaExportCollector()
    cnt = collector.seed_sample_export_data()
    return jsonify({"status": "success", "seeded_count": cnt, "message": "10-day semiconductor export sample data seeded"})

@api_bp.route("/indicators/kr-export/fetch", methods=["POST"])
def fetch_kr_export_api():
    """Fetch official semiconductor export statistics from Korea Customs Service Open API."""
    payload = request.get_json(silent=True) or {}
    start_year = payload.get("start_year")
    end_year = payload.get("end_year")
    hs_code = payload.get("hs_code", "8542")

    collector = KoreaExportCollector()
    result = collector.fetch_customs_api(
        start_year=int(start_year) if start_year else None,
        end_year=int(end_year) if end_year else None,
        hs_code=hs_code
    )
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)

@api_bp.route("/indicators/kr-export/fetch-10day", methods=["POST"])
def fetch_10day_export_api():
    """Fetch 10-day provisional trade statistics from Korea Customs Service Open API."""
    payload = request.get_json(silent=True) or {}
    strt_yymm = payload.get("strt_yymm")
    end_yymm = payload.get("end_yymm")

    collector = KoreaExportCollector()
    result = collector.fetch_10day_customs_api(strt_yymm=strt_yymm, end_yymm=end_yymm)
    return jsonify(result)

# ─── Consensus & Beat/Miss Endpoints ───

@api_bp.route("/consensus", methods=["GET"])
def get_consensus():
    """Retrieve consensus and beat/miss items."""
    ticker = request.args.get("ticker")
    metric = request.args.get("metric")
    limit = int(request.args.get("limit", 100))

    service = ConsensusService()
    items = service.get_consensus_list(ticker=ticker, metric_type=metric, limit=limit)
    return jsonify({"status": "success", "data": items, "count": len(items)})

@api_bp.route("/consensus", methods=["POST"])
def add_consensus():
    """Record or update consensus and actual results."""
    payload = request.get_json() or {}
    required = ["ticker", "fiscal_year", "fiscal_quarter", "metric_type", "consensus_value"]
    for field in required:
        if field not in payload:
            return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400

    service = ConsensusService()
    res = service.record_consensus(
        ticker=payload["ticker"],
        fiscal_year=str(payload["fiscal_year"]),
        fiscal_quarter=str(payload["fiscal_quarter"]),
        metric_type=payload["metric_type"],
        consensus_value=float(payload["consensus_value"]),
        actual_value=float(payload["actual_value"]) if payload.get("actual_value") is not None else None,
        announcement_date=payload.get("announcement_date"),
        source=payload.get("source", "MANUAL")
    )
    if res.get("status") == "error":
        return jsonify(res), 400
    return jsonify(res)

@api_bp.route("/consensus/matrix", methods=["GET"])
def get_consensus_matrix():
    """Retrieve Company x Quarter matrix for Beat/Miss Heatmap."""
    service = ConsensusService()
    matrix = service.get_matrix_view()
    return jsonify({"status": "success", "data": matrix})

@api_bp.route("/consensus/seed", methods=["POST"])
def seed_consensus():
    """Seed representative consensus and actual results for top AI companies."""
    service = ConsensusService()
    cnt = service.seed_sample_consensus()
    return jsonify({"status": "success", "seeded_count": cnt, "message": "Consensus sample data successfully seeded"})

# ─── Memory Semiconductor Spot Price Endpoints ───

@api_bp.route("/indicators/memory-spot", methods=["GET"])
def get_memory_spot():
    """Retrieve memory spot price summary and historical trend."""
    indicator_type = request.args.get("type", "SPOT_DRAM_DDR5_16GB")
    limit = int(request.args.get("limit", 30))

    collector = MemorySpotCollector()
    summary = collector.get_latest_summary()
    history = collector.get_spot_history(indicator_type=indicator_type, limit=limit)

    return jsonify({
        "status": "success",
        "indicator_type": indicator_type,
        "indicator_info": MEMORY_SPOT_TYPES.get(indicator_type, {}),
        "summary": summary,
        "history": history
    })

@api_bp.route("/indicators/memory-spot", methods=["POST"])
def add_memory_spot():
    """Add a manual memory spot price point."""
    payload = request.get_json() or {}
    required = ["indicator_type", "date", "value"]
    for f in required:
        if f not in payload:
            return jsonify({"status": "error", "message": f"Missing required field: {f}"}), 400

    collector = MemorySpotCollector()
    res = collector.add_spot_entry(
        indicator_type=payload["indicator_type"],
        date_str=payload["date"],
        value=float(payload["value"]),
        unit=payload.get("unit", "USD"),
        note=payload.get("note"),
        source=payload.get("source", "MANUAL")
    )
    if res.get("status") == "error":
        return jsonify(res), 400
    return jsonify(res)

@api_bp.route("/indicators/memory-spot/seed", methods=["POST"])
def seed_memory_spot():
    """Seed 2025~2026 weekly memory spot price series for DDR5, DDR4, NAND, DXI."""
    collector = MemorySpotCollector()
    cnt = collector.seed_sample_spot_data()
    return jsonify({
        "status": "success",
        "seeded_count": cnt,
        "message": f"{cnt} memory spot data points successfully seeded"
    })

@api_bp.route("/indicators/memory-spot/fetch", methods=["POST"])
def fetch_memory_spot_api():
    """Fetch spot prices from public MemoryIndex API."""
    collector = MemorySpotCollector()
    res = collector.fetch_public_api()
    return jsonify(res)

@api_bp.route("/indicators/memory-spot/types", methods=["GET"])
def get_memory_spot_types():
    """Retrieve list of available memory spot indicators."""
    return jsonify({"status": "success", "data": MEMORY_SPOT_TYPES})

# ─── Quarterly Financials (2020~Present) ───

@api_bp.route("/financials/<ticker>", methods=["GET"])
def get_quarterly_financials(ticker):
    """Retrieve complete quarterly financial series from 2020 to present."""
    start_year = int(request.args.get("start_year", 2020))
    service = FinancialService()
    res = service.get_quarterly_financials(ticker=ticker, start_year=start_year)
    if res.get("status") == "error":
        return jsonify(res), 404
    return jsonify(res)

@api_bp.route("/financials/seed", methods=["POST"])
def seed_quarterly_financials():
    """Seed historical quarterly financials for AI tech leaders from 2020-Q1."""
    service = FinancialService()
    cnt = service.seed_historical_financials_from_2020()
    return jsonify({
        "status": "success",
        "seeded_count": cnt,
        "message": f"Historical quarterly financials from 2020 seeded ({cnt} metrics)"
    })

# ─── Filing Section Extractor ───

@api_bp.route("/filings/<int:filing_id>/sections", methods=["GET"])
def get_filing_sections(filing_id):
    """Extract and isolate key sections (MD&A, Risk Factors, Financial Statements) from filing."""
    filing = query_db(
        """
        SELECT f.id, f.filing_type, f.fiscal_year, f.fiscal_quarter, f.filed_date,
               f.raw_text, e.ticker, e.name_en, e.name_ko
        FROM filing f
        JOIN entity e ON f.entity_id = e.id
        WHERE f.id = ?
        """,
        (filing_id,),
        one=True
    )
    if not filing:
        return jsonify({"status": "error", "message": "Filing not found"}), 404

    raw_text = filing.get("raw_text") or ""
    form_type = filing.get("filing_type", "10-Q")

    sections = FilingSectionExtractor.extract_sections(raw_text, form_type)

    return jsonify({
        "status": "success",
        "filing_id": filing_id,
        "ticker": filing["ticker"],
        "name_en": filing["name_en"],
        "form": form_type,
        "period": f"{filing['fiscal_year']}-{filing['fiscal_quarter']}",
        "sections": sections
    })


# ─── Earnings Call Transcripts ───

@api_bp.route("/earning-calls", methods=["GET"])
def get_earning_calls():
    """Retrieve list of earnings call transcripts with optional filters."""
    ticker = request.args.get("ticker")
    layer = request.args.get("layer")
    year = request.args.get("year")
    limit = int(request.args.get("limit", 50))

    collector = TranscriptCollector()
    calls = collector.get_transcripts_list(ticker=ticker, layer_code=layer, fiscal_year=year, limit=limit)
    return jsonify({
        "status": "success",
        "count": len(calls),
        "data": calls
    })

@api_bp.route("/earning-calls/<int:call_id>", methods=["GET"])
def get_earning_call_detail(call_id):
    """Retrieve detailed transcript text and parsed sections."""
    collector = TranscriptCollector()
    detail = collector.get_transcript_detail(call_id)
    if not detail:
        return jsonify({"status": "error", "message": f"Transcript {call_id} not found"}), 404
    return jsonify({
        "status": "success",
        "data": detail
    })

@api_bp.route("/earning-calls/by-quarter", methods=["GET"])
def get_earning_call_by_quarter():
    """Find transcript by ticker, fiscal year, and quarter."""
    ticker = request.args.get("ticker")
    year = request.args.get("year")
    quarter = request.args.get("quarter")

    if not ticker or not year or not quarter:
        return jsonify({"status": "error", "message": "Missing ticker, year, or quarter parameter"}), 400

    collector = TranscriptCollector()
    detail = collector.get_transcript_by_quarter(ticker, year, quarter)
    if not detail:
        return jsonify({"status": "error", "message": f"Transcript for {ticker} {year}-{quarter} not found"}), 404
    return jsonify({
        "status": "success",
        "data": detail
    })

@api_bp.route("/earning-calls", methods=["POST"])
def upload_earning_call():
    """Save or upload a new conference call transcript."""
    payload = request.get_json(silent=True) or {}
    ticker = payload.get("ticker")
    fiscal_year = payload.get("fiscal_year")
    fiscal_quarter = payload.get("fiscal_quarter")
    call_date = payload.get("call_date") or date.today().strftime("%Y-%m-%d")
    transcript_text = payload.get("transcript_text")
    call_time_et = payload.get("call_time_et", "17:00 ET")
    source_url = payload.get("source_url")

    if not ticker or not fiscal_year or not fiscal_quarter or not transcript_text:
        return jsonify({
            "status": "error",
            "message": "Required fields: ticker, fiscal_year, fiscal_quarter, transcript_text"
        }), 400

    collector = TranscriptCollector()
    res = collector.save_transcript(
        ticker=ticker,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        call_date=call_date,
        transcript_text=transcript_text,
        call_time_et=call_time_et,
        source_url=source_url
    )
    if res.get("status") == "error":
        return jsonify(res), 400
    return jsonify(res), 201

@api_bp.route("/earning-calls/seed", methods=["POST"])
def seed_earning_calls():
    """Seed authentic sample conference call transcripts."""
    collector = TranscriptCollector()
    cnt = collector.seed_sample_transcripts()
    return jsonify({
        "status": "success",
        "seeded_count": cnt,
        "message": f"{cnt} conference call transcripts seeded successfully"
    })

# ─── AI Report Studio & Agent Endpoints ───

@api_bp.route("/reports/engine-status", methods=["GET"])
def get_report_engine_status():
    """Check availability of Gemini API and local Ollama server."""
    from app.services.report_agent import ReportAgent
    status = ReportAgent.check_engine_status()
    return jsonify({"status": "success", "data": status})

@api_bp.route("/reports/templates", methods=["GET"])
def get_report_templates():
    """Return pre-configured outline templates."""
    from app.services.report_agent import REPORT_TEMPLATES
    return jsonify({"status": "success", "templates": REPORT_TEMPLATES})

@api_bp.route("/reports/generate", methods=["POST"])
def generate_custom_report():
    """Generate structured cross-company report using AI ReportAgent."""
    from app.services.report_agent import ReportAgent

    payload = request.get_json() or {}
    target_ticker = payload.get("target_ticker", "NVDA")
    peer_tickers = payload.get("peer_tickers", [])
    chapters = payload.get("chapters", [])
    user_notes = payload.get("user_notes", "")
    timeframe = payload.get("timeframe", "latest")
    tone_style = payload.get("tone_style", "analyst")
    engine = payload.get("engine", "gemini")
    model_name = payload.get("model_name")

    if not chapters:
        return jsonify({"status": "error", "message": "At least one chapter must be specified."}), 400

    try:
        agent = ReportAgent(engine=engine, model_name=model_name)
        result = agent.generate_report(
            target_ticker=target_ticker,
            peer_tickers=peer_tickers,
            chapters=chapters,
            user_notes=user_notes,
            timeframe=timeframe,
            tone_style=tone_style
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ─── GPU Cloud Rental Spot Price Endpoints ───

@api_bp.route("/gpu/prices", methods=["GET"])
def get_gpu_prices():
    """Retrieve latest GPU spot prices, KPIs, and provider quotes."""
    from app.services.gpu_price_collector import GpuPriceCollector
    collector = GpuPriceCollector()
    data = collector.get_latest_summary()
    return jsonify(data)

@api_bp.route("/gpu/history", methods=["GET"])
def get_gpu_history():
    """Retrieve historical rental price series for a specific GPU model."""
    from app.services.gpu_price_collector import GpuPriceCollector
    model_key = request.args.get("model", "H100")
    limit = int(request.args.get("limit", 50))
    collector = GpuPriceCollector()
    data = collector.get_price_history(model_key=model_key, limit=limit)
    return jsonify(data)

@api_bp.route("/gpu/seed", methods=["POST"])
def seed_gpu_prices():
    """Seed benchmark GPU cloud rental spot history (2023~2026)."""
    from app.services.gpu_price_collector import GpuPriceCollector
    collector = GpuPriceCollector()
    cnt = collector.seed_gpu_rental_history()
    return jsonify({
        "status": "success",
        "seeded_count": cnt,
        "message": f"{cnt} GPU rental spot price data points seeded successfully."
    })

@api_bp.route("/gpu/sync", methods=["POST"])
def sync_gpu_prices():
    """Synchronize latest real-market GPU cloud rental spot prices to current date."""
    from app.services.gpu_price_collector import GpuPriceCollector
    collector = GpuPriceCollector()
    body = request.get_json(silent=True) or {}
    target_date = body.get("target_date")
    result = collector.sync_latest_spot_prices(target_date=target_date)
    return jsonify(result)


# ==============================================================================
# Analyst Reports & Target Price Tracking APIs
# ==============================================================================

@api_bp.route("/reports/analysts", methods=["GET"])
def get_analyst_reports():
    """
    Get list of analyst reports and target prices for a ticker.
    Returns consensus mean/high/low and individual report actions.
    """
    ticker = request.args.get("ticker", "").strip()
    source_type = request.args.get("source_type", "ALL").strip()
    tier_filter = request.args.get("tier", "ALL").strip().upper()
    limit = int(request.args.get("limit", 60))

    if not ticker:
        return jsonify({"error": "ticker parameter is required"}), 400

    entity = query_db("SELECT id, ticker, name_en, name_ko, country FROM entity WHERE ticker = ?", (ticker,), one=True)
    if not entity:
        return jsonify({"error": f"Entity not found for ticker {ticker}"}), 404

    # Latest stock price
    price_row = query_db(
        "SELECT close, date FROM stock_price WHERE entity_id = ? ORDER BY date DESC LIMIT 1",
        (entity["id"],),
        one=True
    )
    current_price = float(price_row["close"]) if price_row else None
    latest_price_date = price_row["date"] if price_row else None

    # Latest consensus snapshot from target_price_history
    hist_row = query_db(
        "SELECT * FROM target_price_history WHERE entity_id = ? ORDER BY date DESC LIMIT 1",
        (entity["id"],),
        one=True
    )

    # Build SQL for reports
    sql = """
        SELECT id, entity_id, ticker, source_type, broker_name, analyst_name,
               report_date, title, rating, action_type, target_price,
               current_price_at_report, upside_pct, currency, pdf_url,
               local_pdf_path, summary_text, created_at
        FROM analyst_report
        WHERE entity_id = ?
    """
    params = [entity["id"]]

    if source_type and source_type != "ALL":
        sql += " AND source_type = ?"
        params.append(source_type)

    sql += " ORDER BY report_date DESC, id DESC LIMIT ?"
    params.append(limit * 2 if tier_filter != "ALL" else limit)

    raw_reports = query_db(sql, params)

    from app.services.ib_target_collector import IBTargetCollector
    filtered_reports = []
    for r in raw_reports:
        # Determine tier
        r["broker_tier"] = IBTargetCollector.get_broker_tier(r["broker_name"])
        r["has_pdf"] = bool(r["local_pdf_path"])
        # Recalculate upside vs current price if missing
        if r["target_price"] and current_price and current_price > 0 and not r.get("upside_pct"):
            r["upside_pct"] = round(((r["target_price"] - current_price) / current_price) * 100.0, 2)

        # Apply tier filter if requested
        if tier_filter != "ALL":
            if r["broker_tier"] != tier_filter:
                continue

        filtered_reports.append(r)
        if len(filtered_reports) >= limit:
            break

    reports = filtered_reports

    # Compute consensus stats dynamically from reports if history is empty
    target_prices = [r["target_price"] for r in reports if r["target_price"] and r["target_price"] > 0]
    mean_target = (sum(target_prices) / len(target_prices)) if target_prices else (hist_row["target_mean"] if hist_row else None)
    high_target = max(target_prices) if target_prices else (hist_row["target_high"] if hist_row else None)
    low_target = min(target_prices) if target_prices else (hist_row["target_low"] if hist_row else None)

    mean_upside = None
    if mean_target and current_price and current_price > 0:
        mean_upside = round(((mean_target - current_price) / current_price) * 100.0, 2)

    return jsonify({
        "ticker": ticker,
        "entity": {
            "id": entity["id"],
            "name_en": entity["name_en"],
            "name_ko": entity["name_ko"],
            "country": entity["country"]
        },
        "current_price": current_price,
        "latest_price_date": latest_price_date,
        "consensus": {
            "mean": round(mean_target, 2) if mean_target else None,
            "high": round(high_target, 2) if high_target else None,
            "low": round(low_target, 2) if low_target else None,
            "mean_upside_pct": mean_upside,
            "total_opinions": len(target_prices) or (hist_row["num_analysts"] if hist_row else 0)
        },
        "total_reports": len(reports),
        "reports": reports
    })

@api_bp.route("/reports/collect/naver", methods=["POST"])
def collect_naver_reports():
    """Trigger collection of Naver Securities research reports and download PDFs."""
    from app.services.naver_report_collector import NaverReportCollector
    data = request.get_json() or {}
    ticker = data.get("ticker", "000660.KS").strip()
    download_pdf = data.get("download_pdf", True)
    max_scan_pages = int(data.get("max_scan_pages", 6))

    collector = NaverReportCollector(delay_sec=0.5)
    result = collector.collect_reports_for_ticker(
        ticker=ticker,
        download_pdf=download_pdf,
        max_scan_pages=max_scan_pages
    )
    return jsonify({
        "status": "success",
        "result": result
    })

@api_bp.route("/reports/collect/global-ib", methods=["POST"])
def collect_global_ib_reports():
    """Trigger collection of Global IB target prices and recommendations."""
    from app.services.ib_target_collector import IBTargetCollector
    data = request.get_json() or {}
    ticker = data.get("ticker", "NVDA").strip()

    collector = IBTargetCollector()
    result = collector.collect_ib_targets_for_ticker(ticker=ticker)
    return jsonify({
        "status": "success",
        "result": result
    })

@api_bp.route("/reports/target-bands", methods=["GET"])
def get_target_bands():
    """
    Get historical stock prices along with target price bands (Mean, High, Low)
    for chart overlay visualization.
    """
    ticker = request.args.get("ticker", "").strip()
    days = int(request.args.get("days", 180))

    if not ticker:
        return jsonify({"error": "ticker parameter is required"}), 400

    entity = query_db("SELECT id, ticker FROM entity WHERE ticker = ?", (ticker,), one=True)
    if not entity:
        return jsonify({"error": f"Entity not found for ticker {ticker}"}), 404

    # Stock prices
    prices = query_db(
        """
        SELECT date, close FROM stock_price
        WHERE entity_id = ?
        ORDER BY date ASC
        """,
        (entity["id"],)
    )

    if not prices:
        return jsonify({"ticker": ticker, "dates": [], "prices": [], "target_means": []})

    # Slice to last N days
    prices = prices[-days:]
    dates = [p["date"] for p in prices]
    close_prices = [p["close"] for p in prices]

    # Target price history snapshots
    t_hist = query_db(
        """
        SELECT date, target_mean, target_high, target_low FROM target_price_history
        WHERE entity_id = ?
        ORDER BY date ASC
        """,
        (entity["id"],)
    )
    t_map = {row["date"]: row for row in t_hist}

    # Analyst reports points for scatter markers
    actions = query_db(
        """
        SELECT report_date, broker_name, target_price, rating, action_type, source_type
        FROM analyst_report
        WHERE entity_id = ? AND target_price IS NOT NULL AND target_price > 0
        ORDER BY report_date ASC
        """,
        (entity["id"],)
    )

    # Current consensus fallback to fill line across dates if history is sparse
    latest_hist = t_hist[-1] if t_hist else None
    latest_mean = latest_hist["target_mean"] if latest_hist else None
    latest_high = latest_hist["target_high"] if latest_hist else None
    latest_low = latest_hist["target_low"] if latest_hist else None

    # If no target_price_history, compute from latest reports
    if not latest_mean and actions:
        recent_targets = [a["target_price"] for a in actions[-10:] if a["target_price"]]
        if recent_targets:
            latest_mean = round(sum(recent_targets) / len(recent_targets), 2)
            latest_high = max(recent_targets)
            latest_low = min(recent_targets)

    target_means = []
    target_highs = []
    target_lows = []
    for d in dates:
        if d in t_map:
            target_means.append(t_map[d]["target_mean"])
            target_highs.append(t_map[d]["target_high"])
            target_lows.append(t_map[d]["target_low"])
        else:
            # Carry forward or fallback to latest
            target_means.append(latest_mean)
            target_highs.append(latest_high)
            target_lows.append(latest_low)

    return jsonify({
        "ticker": ticker,
        "dates": dates,
        "close_prices": close_prices,
        "target_means": target_means,
        "target_highs": target_highs,
        "target_lows": target_lows,
        "actions": actions
    })

@api_bp.route("/reports/pdf/<int:report_id>", methods=["GET"])
def stream_report_pdf(report_id):
    """Stream locally stored analyst report PDF to browser viewer."""
    from app.config import DATA_DIR
    row = query_db("SELECT local_pdf_path, title FROM analyst_report WHERE id = ?", (report_id,), one=True)
    if not row or not row["local_pdf_path"]:
        return jsonify({"error": "Report PDF not found on server"}), 404

    local_path = DATA_DIR / row["local_pdf_path"]
    if not local_path.exists():
        # Try relative to reports dir
        from app.config import REPORTS_DIR
        alt_path = REPORTS_DIR / row["local_pdf_path"]
        if alt_path.exists():
            local_path = alt_path
        else:
            return jsonify({"error": f"PDF file missing on disk: {row['local_pdf_path']}"}), 404

    return send_file(
        local_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"Report_{report_id}.pdf"
    )

@api_bp.route("/fintwit/ask", methods=["POST"])
def ask_fintwit_agent():
    """
    On-Demand FinTwit Q&A Agent Endpoint.
    Takes natural language questions about price targets & comments and returns
    structured markdown tables, sentiment, and quotes.
    """
    from app.services.fintwit_qa_agent import FinTwitQAAgent
    data = request.get_json() or {}
    query_text = data.get("query", "").strip()
    ticker = data.get("ticker", "").strip() or None

    if not query_text:
        return jsonify({"error": "query parameter is required"}), 400

    agent = FinTwitQAAgent()
    result = agent.answer_query(user_query=query_text, ticker=ticker)
    return jsonify(result)

@api_bp.route("/fintwit/stream", methods=["GET"])
def get_fintwit_stream():
    """Get live social and news stream from StockTwits for a ticker."""
    from app.services.fintwit_qa_agent import FinTwitQAAgent
    ticker = request.args.get("ticker", "NVDA").strip()
    limit = int(request.args.get("limit", 20))

    agent = FinTwitQAAgent()
    posts = agent.fetch_live_fintwit_stream(ticker=ticker, limit=limit)
    return jsonify({
        "ticker": ticker,
        "total_posts": len(posts),
        "posts": posts
    })


# ─── PDF Full-Text Search (FTS5) ───

@api_bp.route("/reports/search", methods=["GET"])
def search_analyst_reports_fts():
    """Full-text search inside analyst report PDFs via FTS5."""
    from app.services.pdf_indexer import PdfReportIndexer
    query = request.args.get("q", "").strip()
    ticker = request.args.get("ticker", "").strip() or None
    limit = int(request.args.get("limit", 15))

    if not query:
        return jsonify({"status": "success", "results": [], "query": ""})

    results = PdfReportIndexer.search_reports(query=query, ticker=ticker, limit=limit)
    return jsonify({
        "status": "success",
        "query": query,
        "ticker": ticker,
        "count": len(results),
        "results": results
    })


@api_bp.route("/reports/index-all", methods=["POST"])
def index_all_reports_fts():
    """Trigger background text extraction and FTS5 indexing for all downloaded PDFs."""
    from app.services.pdf_indexer import PdfReportIndexer
    res = PdfReportIndexer.index_all_reports_background()
    return jsonify(res)


@api_bp.route("/reports/index-status", methods=["GET"])
def get_reports_index_status():
    """Check progress of PDF FTS5 indexing."""
    from app.services.pdf_indexer import PdfReportIndexer
    status = PdfReportIndexer.get_indexing_status()
    return jsonify({"status": "success", "data": status})


# ─── Automated Pre-Market Scheduler ───

@api_bp.route("/scheduler/status", methods=["GET"])
def get_scheduler_status():
    """Get current status, next run times, and recent logs of the scheduler."""
    from app.services.report_scheduler import ReportScheduler
    sch = ReportScheduler.get_instance()
    return jsonify({"status": "success", "data": sch.get_status()})


@api_bp.route("/scheduler/toggle", methods=["POST"])
def toggle_scheduler():
    """Start or stop the background scheduler."""
    from app.services.report_scheduler import ReportScheduler
    sch = ReportScheduler.get_instance()
    if sch.is_running:
        sch.stop()
    else:
        sch.start()
    return jsonify({"status": "success", "data": sch.get_status()})


@api_bp.route("/scheduler/run-now", methods=["POST"])
def run_scheduler_now():
    """Trigger immediate execution of pre-market jobs."""
    from app.services.report_scheduler import ReportScheduler
    data = request.get_json() or {}
    job_type = data.get("job_type", "ALL")
    sch = ReportScheduler.get_instance()
    result = sch.run_now(job_type=job_type)
    return jsonify({"status": "success", "data": result})



