"""
REST API Routes for QK_EARNING Application
"""
from datetime import datetime, date
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file
from app.models.database import query_db, execute_db, get_db
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
        SELECT ec.*, e.ticker, e.name_en, e.name_ko, e.layer_code, l.name_ko as layer_name_ko
        FROM earning_calendar ec
        JOIN entity e ON ec.entity_id = e.id
        LEFT JOIN layer l ON e.layer_code = l.code
        ORDER BY ec.expected_date ASC
        """
    )
    for r in rows:
        try:
            exp = datetime.strptime(r["expected_date"], "%Y-%m-%d").date()
            diff = (exp - date.today()).days
            r["days_left"] = diff
            r["d_day"] = f"D-{diff}" if diff > 0 else ("D-Day" if diff == 0 else f"D+{abs(diff)}")
            if diff < 0 and r.get("status") == "UPCOMING":
                r["status"] = "COMPLETED"
        except Exception:
            r["days_left"] = 999
            r["d_day"] = "-"

    return jsonify({"status": "success", "data": rows, "count": len(rows)})

@api_bp.route("/calendar/sync", methods=["POST"])
def sync_calendar():
    """Trigger manual synchronization of earnings announcement dates via Yahoo Finance."""
    from app.services.earnings_calendar_collector import EarningsCalendarCollector
    ticker = (request.get_json() or {}).get("ticker")
    collector = EarningsCalendarCollector()
    if ticker:
        res = collector.sync_calendar_for_ticker(ticker)
        if not res:
            return jsonify({"status": "error", "message": f"Could not sync calendar for {ticker}"}), 400
        return jsonify({"status": "success", "data": res})
    res = collector.sync_calendar_all_entities()
    return jsonify(res)

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

@api_bp.route("/indicators/kr-export/parse-press-release", methods=["POST"])
def parse_kr_export_press_release():
    """Parse customs 10-day press release or news text and optionally save to DB."""
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    if not text.strip():
        return jsonify({"status": "error", "message": "파싱할 보도자료 또는 기사 텍스트가 비어있습니다."}), 400

    collector = KoreaExportCollector()
    save_to_db = payload.get("save", True)
    default_year = int(payload.get("year", 2026))

    if save_to_db:
        res = collector.parse_and_save_press_release(text, default_year=default_year)
    else:
        from app.services.kr_export_collector import CustomsPressReleaseParser
        parsed = CustomsPressReleaseParser.parse_text(text, default_year=default_year)
        res = {"status": parsed["status"], "parsed": parsed}

    return jsonify(res)

@api_bp.route("/indicators/kr-export/auto-collect-press", methods=["POST"])
def auto_collect_kr_export_press():
    """Automatically crawl and parse the latest 10-day export press releases from news/RSS."""
    collector = KoreaExportCollector()
    res = collector.auto_collect_press_releases()
    return jsonify(res)

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
    limit = int(request.args.get("limit", 50))

    collector = MemorySpotCollector()
    summary = collector.get_latest_summary()
    history = collector.get_spot_history(indicator_type=indicator_type, limit=limit)

    series = {}
    for code in MEMORY_SPOT_TYPES.keys():
        series[code] = collector.get_spot_history(indicator_type=code, limit=limit)

    return jsonify({
        "status": "success",
        "indicator_type": indicator_type,
        "indicator_info": MEMORY_SPOT_TYPES.get(indicator_type, {}),
        "summary": summary,
        "history": history,
        "data": history,
        "series": series
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
    """Retrieve historical rental price series for a specific GPU model or all models."""
    from app.services.gpu_price_collector import GpuPriceCollector
    model_key = request.args.get("model", "H100")
    limit = int(request.args.get("limit", 50))
    collector = GpuPriceCollector()
    data = collector.get_price_history(model_key=model_key, limit=limit)

    all_series = {}
    for m in ["H100", "H200", "B200", "A100"]:
        all_series[m] = collector.get_price_history(model_key=m, limit=limit).get("history", [])
    data["series"] = all_series
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
    job_type = data.get("job_type", data.get("job", "ALL")).upper()
    sch = ReportScheduler.get_instance()
    result = sch.run_now(job_type=job_type)
    return jsonify({"status": "success", "data": result})


# ═════════════════════════════════════════════════════════════════════
# ─── Company-Centric & Memory Claude Macro Intelligence Endpoints ───
# ═════════════════════════════════════════════════════════════════════

TICKER_TO_MEM_ID = {
    'NVDA': 'NVIDIA',
    'TSM': 'TSMC',
    '000660.KS': 'SK_HYNIX',
    '005930.KS': 'SAMSUNG',
    'MU': 'MICRON',
    'MSFT': 'MICROSOFT',
    'GOOGL': 'GOOGLE',
    'AMZN': 'AMAZON',
    'META': 'META',
    'AVGO': 'BROADCOM',
    'AMD': 'AMD',
    'INTC': 'INTEL',
    'ARM': 'ARM',
    'ASML': 'ASML',
    'AMAT': 'AMAT',
    'LRCX': 'LAM_RESEARCH',
    'KLAC': 'KLA',
    'ASX': 'ASE',
    'AMKR': 'AMKOR',
    'WDC': 'WESTERN_DIGITAL',
    'SNDK': 'SANDISK',
    '6600.T': 'KIOXIA',
    'ANET': 'ARISTA',
    'MRVL': 'MARVELL',
    'COHR': 'COHERENT',
    'AAPL': 'APPLE',
    '9984.T': 'SOFTBANK',
    'SPACEX': 'SPACEX',
    'VRT': 'VERTIV',
    'ETN': 'EATON',
    'GEV': 'GE_VERNOVA',
    'SBGSF': 'SCHNEIDER',
    'ORCL': 'ORACLE',
    'CRWV': 'COREWEAVE',
    'NBIS': 'NEBIUS'
}
MEM_ID_TO_TICKER = {v: k for k, v in TICKER_TO_MEM_ID.items()}

# Curated Value Chain Relationships
SUPPLY_CHAIN_MAP = {
    'SNDK': {
        'role': 'L5 글로벌 선단 낸드 플래시(NAND Flash) 및 AI 데이터센터 eSSD 선도 (WDC 분사)',
        'suppliers': [
            {'ticker': 'AMAT', 'name': '어플라이드', 'role': '3D 낸드 고단화 증착 장비'},
            {'ticker': 'LRCX', 'name': '램리서치', 'role': '고종횡비 HARC 채널홀 식각 장비 공급'},
            {'ticker': '6600.T', 'name': '키옥시아', 'role': 'BiCS FLASH 합작 팹(JV) 공동 생산 및 R&D'}
        ],
        'customers': [
            {'ticker': 'MSFT', 'name': '마이크로소프트', 'share': 'Azure AI 클라우드 고용량 PCIe Gen5 NVMe eSSD 공급'},
            {'ticker': 'AMZN', 'name': '아마존 AWS', 'share': '데이터센터 스토리지 풀 eSSD 대량 조달'},
            {'ticker': 'GOOGL', 'name': '구글', 'share': 'AI 워크로드 캐싱용 엔터프라이즈 QLC SSD 공급'}
        ],
        'segments': [
            {'name': '엔터프라이즈 eSSD (AI/클라우드)', 'pct': 48.0, 'color': '#f59e0b'},
            {'name': '클라이언트 SSD & 임베디드', 'pct': 34.0, 'color': '#3b82f6'},
            {'name': '소비자 플래시 스토리지', 'pct': 18.0, 'color': '#10b981'}
        ]
    },
    'NVDA': {
        'role': 'L3 AI 가속기 시장 점유율 85%+ 독점적 리더',
        'suppliers': [
            {'ticker': 'TSM', 'name': 'TSMC', 'role': '3nm 파운드리 및 CoWoS-L 첨단 패키징 독점 공급'},
            {'ticker': '000660.KS', 'name': 'SK하이닉스', 'role': 'HBM3E 8단/12단 주력 70%+ 공급'},
            {'ticker': 'MU', 'name': '마이크론', 'role': 'HBM3E 보조 공급사 (H200 탑재)'},
            {'ticker': '005930.KS', 'name': '삼성전자', 'role': 'HBM3E 12단 및 파운드리 대안 공급사'},
            {'ticker': 'VRT', 'name': '버티브', 'role': 'GB200 NVL72 액체냉각 CDU 및 고전력 배전 독점'}
        ],
        'customers': [
            {'ticker': 'MSFT', 'name': '마이크로소프트', 'share': 'CapEx 38% GPU 할당 (Azure AI)'},
            {'ticker': 'META', 'name': '메타', 'share': 'Llama 4 학습용 20만장 클러스터 구축'},
            {'ticker': 'AMZN', 'name': '아마존 AWS', 'share': 'Trainium 보완 및 EC2 P5/UltraServer'},
            {'ticker': 'GOOGL', 'name': '구글 GCP', 'share': 'TPU 보완 및 A3/A4 인스턴스'},
            {'ticker': 'CRWV', 'name': '코어위브', 'share': '네오클라우드 Blackwell 우선 할당 파트너'}
        ],
        'segments': [
            {'name': '데이터센터 (Compute & Networking)', 'pct': 87.5, 'color': '#76b900'},
            {'name': '게이밍 (GeForce)', 'pct': 8.2, 'color': '#3b82f6'},
            {'name': '프로페셔널 시각화', 'pct': 2.3, 'color': '#8b5cf6'},
            {'name': '오토모티브 & 로보틱스', 'pct': 2.0, 'color': '#f59e0b'}
        ]
    },
    '000660.KS': {
        'role': 'L5 AI 고대역폭 메모리(HBM3E/HBM4) 글로벌 독점적 1위',
        'suppliers': [
            {'ticker': 'ASML', 'name': 'ASML', 'role': '1c/1b D램용 EUV 노광장비 공급'},
            {'ticker': 'AMAT', 'name': '어플라이드', 'role': 'MR-MUF 공정 증착/식각 장비'},
            {'ticker': 'LRCX', 'name': '램리서치', 'role': 'TSV(실리콘 관통전극) 고종횡비 식각 장비'}
        ],
        'customers': [
            {'ticker': 'NVDA', 'name': '엔비디아', 'share': 'HBM3E 공급 점유율 75% 독점적 벤더'},
            {'ticker': 'AMD', 'name': 'AMD', 'share': 'MI300X/MI325X HBM3/3E 공급'},
            {'ticker': 'AVGO', 'name': '브로드컴', 'share': '빅테크 커스텀 ASIC용 HBM 공급'}
        ],
        'segments': [
            {'name': 'DRAM (HBM3E/DDR5)', 'pct': 72.0, 'color': '#f59e0b'},
            {'name': 'NAND Flash (eSSD)', 'pct': 24.5, 'color': '#3b82f6'},
            {'name': '기타 및 파운드리', 'pct': 3.5, 'color': '#6b7280'}
        ]
    },
    'TSM': {
        'role': 'L4 글로벌 첨단 파운드리 및 CoWoS 어드밴스드 패키징 독점',
        'suppliers': [
            {'ticker': 'ASML', 'name': 'ASML', 'role': 'High-NA 및 EUV 독점 공급'},
            {'ticker': 'AMAT', 'name': '어플라이드', 'role': '원자층 증착(ALD) 및 CMP 장비'},
            {'ticker': 'KLAC', 'name': 'KLA', 'role': '웨이퍼 광학 검사 및 수율 관리'}
        ],
        'customers': [
            {'ticker': 'NVDA', 'name': '엔비디아', 'share': 'Blackwell/Hopper 4nm/3nm 웨이퍼 전량 위탁'},
            {'ticker': 'AAPL', 'name': '애플', 'share': 'A18/M4 3nm 최선단 공정 최대 고객'},
            {'ticker': 'AMD', 'name': 'AMD', 'share': 'Zen 5 및 Instinct MI300 4nm/5nm 생산'},
            {'ticker': 'AVGO', 'name': '브로드컴', 'share': '커스텀 XPU 및 스위치 실리콘 위탁'}
        ],
        'segments': [
            {'name': 'HPC (고성능 컴퓨팅)', 'pct': 52.0, 'color': '#e05e2b'},
            {'name': '스마트폰', 'pct': 34.0, 'color': '#3b82f6'},
            {'name': 'IoT & 오토모티브', 'pct': 10.0, 'color': '#10b981'},
            {'name': '기타', 'pct': 4.0, 'color': '#6b7280'}
        ]
    },
    'MSFT': {
        'role': 'L2 글로벌 1위 엔터프라이즈 AI 클라우드 하이퍼스케일러',
        'suppliers': [
            {'ticker': 'NVDA', 'name': '엔비디아', 'role': 'GB200/H100 연간 수십만 대 조달'},
            {'ticker': 'VRT', 'name': '버티브', 'role': '차세대 액체냉각 데이터센터 모듈러 인프라'},
            {'ticker': 'ANET', 'name': '아리스타', 'role': '400G/800G 이더넷 스위치 네트워킹'}
        ],
        'customers': [
            {'ticker': 'SPACEX', 'name': 'OpenAI / xAI', 'share': 'GPT-4 / GPT-5 전용 인프라 클러스터 지원'},
            {'ticker': 'ENTERPRISE', 'name': '글로벌 포춘 500대 기업', 'share': 'M365 Copilot & Azure OpenAI API'}
        ],
        'segments': [
            {'name': '지능형 클라우드 (Azure/Server)', 'pct': 43.5, 'color': '#00a4ef'},
            {'name': '생산성 및 비즈니스 (Office/LinkedIn)', 'pct': 31.8, 'color': '#10b981'},
            {'name': '개인 컴퓨팅 (Windows/Gaming)', 'pct': 24.7, 'color': '#8b5cf6'}
        ]
    },
    'OAI': {
        'role': 'L7 초거대 파운데이션 LLM 및 Frontier AI 인프라 선도사 (비상장)',
        'suppliers': [
            {'ticker': 'MSFT', 'name': '마이크로소프트', 'role': 'Azure 수십만 대 AI 가속기 컴퓨팅 클러스터 & 독점 라이선스'},
            {'ticker': 'NVDA', 'name': '엔비디아', 'role': 'H100/H200/GB200 AI 가속기 하드웨어'},
            {'ticker': 'ORCL', 'name': '오라클', 'role': 'OCI 베어메탈 GPU 클라우드 훈련 인프라 연계'}
        ],
        'customers': [
            {'ticker': 'AAPL', 'name': '애플', 'share': 'Apple Intelligence Siri 백엔드 ChatGPT 공식 통합'},
            {'ticker': 'MSFT', 'name': '마이크로소프트', 'share': 'GitHub Copilot 및 M365 Copilot 모델 제공'},
            {'ticker': 'ENTERPRISE', 'name': '글로벌 엔터프라이즈', 'share': '3억+ 주간 활성 사용자(WAU) 및 기업용 API'}
        ],
        'segments': [
            {'name': 'ChatGPT 구독 (Plus/Team/Ent)', 'pct': 58.0, 'color': '#10a37f'},
            {'name': 'API 개발자 플랫폼', 'pct': 32.0, 'color': '#00a4ef'},
            {'name': '전략적 라이선스 & 기타', 'pct': 10.0, 'color': '#6366f1'}
        ]
    },
    'ANTHROPIC': {
        'role': 'L7 차세대 Frontier AI 안전성 연구 및 Claude 모델 개발사 (비상장)',
        'suppliers': [
            {'ticker': 'AMZN', 'name': '아마존 (AWS)', 'role': '$8B 전략 투자, AWS 전용 Trainium2 & Bedrock 공급'},
            {'ticker': 'GOOGL', 'name': '구글 (GCP)', 'role': '$2B 투자 및 Google Cloud TPU v5p 인프라 공급'},
            {'ticker': 'NVDA', 'name': '엔비디아', 'role': 'Blackwell / Hopper GPU 클러스터 컴퓨팅'}
        ],
        'customers': [
            {'ticker': 'AMZN', 'name': '아마존 베드록', 'share': 'AWS Bedrock 최다 채택 모델 (Claude 3.5 Sonnet)'},
            {'ticker': 'ENTERPRISE', 'name': '글로벌 테크/금융 기업', 'share': '코딩 에이전트(Cursor 등), 사내 리서치 자동화'},
            {'ticker': 'CLAUDE', 'name': 'Claude Pro/Team 구독', 'share': '전문가 및 엔터프라이즈 워크플로우'}
        ],
        'segments': [
            {'name': '클라우드 Bedrock/Vertex API', 'pct': 62.0, 'color': '#d97706'},
            {'name': 'Claude Direct 구독', 'pct': 28.0, 'color': '#8b5cf6'},
            {'name': '엔터프라이즈 맞춤형 모델', 'pct': 10.0, 'color': '#10b981'}
        ]
    }
}


@api_bp.route("/companies/<ticker>/full", methods=["GET"])
def get_company_full_profile(ticker):
    """Return consolidated company intelligence profile for single-company hub."""
    with get_db() as conn:
        cur = conn.cursor()

        # 1. Entity & Layer
        cur.execute("""
            SELECT e.*, l.name_ko AS layer_name_ko, l.name_en AS layer_name_en, l.sort_order
            FROM entity e
            JOIN layer l ON e.layer_code = l.code
            WHERE UPPER(e.ticker) = UPPER(?)
        """, (ticker,))
        entity = cur.fetchone()
        if not entity:
            return jsonify({"status": "error", "message": f"Entity not found: {ticker}"}), 404
        entity = dict(entity)

        # 2. Latest Stock Price & 1D Change
        cur.execute("""
            SELECT date, close, open, high, low, volume
            FROM stock_price
            WHERE entity_id = ?
            ORDER BY date DESC
            LIMIT 2
        """, (entity["id"],))
        price_rows = cur.fetchall()
        stock_info = {
            "price": None,
            "change": 0.0,
            "change_pct": 0.0,
            "date": None,
            "volume": 0
        }
        if price_rows:
            latest = price_rows[0]
            stock_info["price"] = latest["close"]
            stock_info["date"] = latest["date"]
            stock_info["volume"] = latest["volume"]
            if len(price_rows) > 1:
                prev = price_rows[1]
                chg = latest["close"] - prev["close"]
                stock_info["change"] = round(chg, 2)
                stock_info["change_pct"] = round((chg / prev["close"]) * 100, 2) if prev["close"] else 0.0

        # 3. Next Earning D-Day
        from datetime import datetime, date
        cur.execute("""
            SELECT fiscal_year, fiscal_quarter, expected_date, call_time_et, status
            FROM earning_calendar
            WHERE entity_id = ?
            ORDER BY expected_date DESC
            LIMIT 1
        """, (entity["id"],))
        calendar_row = cur.fetchone()
        calendar_info = {
            "expected_date": None,
            "d_day": None,
            "d_day_label": "-",
            "call_time_et": None,
            "fiscal_period": None
        }
        if calendar_row:
            calendar_info["expected_date"] = calendar_row["expected_date"]
            calendar_info["call_time_et"] = calendar_row["call_time_et"]
            calendar_info["fiscal_period"] = f"{calendar_row['fiscal_year']}-{calendar_row['fiscal_quarter']}"
            try:
                exp_d = datetime.strptime(calendar_row["expected_date"][:10], "%Y-%m-%d").date()
                today = date.today()
                delta = (exp_d - today).days
                calendar_info["d_day"] = delta
                if delta == 0:
                    calendar_info["d_day_label"] = "🔥 D-Day"
                elif delta > 0:
                    calendar_info["d_day_label"] = f"D-{delta}"
                else:
                    calendar_info["d_day_label"] = f"D+{abs(delta)}"
            except Exception:
                calendar_info["d_day_label"] = "예정"

        # 4. Latest Financial Metrics Summary
        cur.execute("""
            SELECT fiscal_year, fiscal_quarter, metric_type, value, unit, currency
            FROM financial_metric
            WHERE entity_id = ?
            ORDER BY fiscal_year DESC, fiscal_quarter DESC
        """, (entity["id"],))
        fm_rows = cur.fetchall()
        financial_summary = {
            "latest_quarter": None,
            "revenue": None,
            "op_income": None,
            "op_margin_pct": None,
            "net_income": None,
            "capex": None,
            "revenue_yoy": None
        }
        by_quarter = {}
        for r in fm_rows:
            q_key = f"{r['fiscal_year']}-{r['fiscal_quarter']}"
            if q_key not in by_quarter:
                by_quarter[q_key] = {}
            by_quarter[q_key][r["metric_type"]] = r["value"]

        quarters_sorted = sorted(by_quarter.keys(), reverse=True)
        if quarters_sorted:
            latest_q = quarters_sorted[0]
            financial_summary["latest_quarter"] = latest_q
            q_data = by_quarter[latest_q]
            financial_summary["revenue"] = q_data.get("revenue")
            financial_summary["op_income"] = q_data.get("operating_income") or q_data.get("op_income")
            financial_summary["op_margin_pct"] = q_data.get("op_margin_pct")
            if not financial_summary["op_margin_pct"] and financial_summary["revenue"] and financial_summary["op_income"]:
                financial_summary["op_margin_pct"] = round((financial_summary["op_income"] / financial_summary["revenue"]) * 100, 1)
            financial_summary["net_income"] = q_data.get("net_income")
            financial_summary["capex"] = q_data.get("capex")

            # calculate YoY if available
            year_part, q_part = latest_q.split("-")
            prev_year_q = f"{int(year_part)-1}-{q_part}"
            if prev_year_q in by_quarter and by_quarter[prev_year_q].get("revenue"):
                prev_rev = by_quarter[prev_year_q]["revenue"]
                curr_rev = financial_summary["revenue"]
                if prev_rev and curr_rev:
                    financial_summary["revenue_yoy"] = round(((curr_rev - prev_rev) / prev_rev) * 100, 1)

        # 5. Analyst Target Price & Upside
        cur.execute("""
            SELECT target_mean, target_high, target_low, num_analysts, date
            FROM target_price_history
            WHERE entity_id = ?
            ORDER BY date DESC
            LIMIT 1
        """, (entity["id"],))
        target_row = cur.fetchone()
        analyst_info = {
            "target_mean": None,
            "target_high": None,
            "target_low": None,
            "upside_pct": None,
            "num_analysts": None
        }
        if target_row:
            analyst_info["target_mean"] = target_row["target_mean"]
            analyst_info["target_high"] = target_row["target_high"]
            analyst_info["target_low"] = target_row["target_low"]
            analyst_info["num_analysts"] = target_row["num_analysts"]
            if stock_info["price"] and target_row["target_mean"]:
                upside = ((target_row["target_mean"] - stock_info["price"]) / stock_info["price"]) * 100
                analyst_info["upside_pct"] = round(upside, 1)

        # 6. Supply Chain & Role Mapping
        chain_info = SUPPLY_CHAIN_MAP.get(entity["ticker"].upper(), {
            "role": f"{entity['layer_name_ko']} 핵심 밸류체인 구성원",
            "suppliers": [],
            "customers": [],
            "segments": [
                {"name": "핵심 사업 부문", "pct": 75.0, "color": "#3b82f6"},
                {"name": "기타 비즈니스", "pct": 25.0, "color": "#6b7280"}
            ]
        })

        return jsonify({
            "status": "success",
            "entity": entity,
            "stock": stock_info,
            "calendar": calendar_info,
            "financials": financial_summary,
            "analyst": analyst_info,
            "value_chain": chain_info
        })


@api_bp.route("/companies/<ticker>/financials", methods=["GET"])
def get_company_financials_series(ticker):
    """Return long-term quarterly financial history (2020~present) for chart and table."""
    start_year = int(request.args.get("start_year", 2020))
    service = FinancialService()
    res = service.get_quarterly_financials(ticker=ticker, start_year=start_year)
    if res.get("status") == "error":
        return jsonify(res), 404
    # Ensure backwards compatibility for quarters key
    res["quarters"] = res.get("series", [])
    return jsonify(res)



@api_bp.route("/companies/<ticker>/filings", methods=["GET"])
def get_company_filings_list(ticker):
    """Return filing documents with optional FTS search and type filtering."""
    q = request.args.get("q", "").strip()
    filing_type = request.args.get("type", "").strip().upper()

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, ticker, name_en, name_ko FROM entity WHERE UPPER(ticker) = UPPER(?)", (ticker,))
        entity = cur.fetchone()
        if not entity:
            return jsonify({"status": "error", "message": f"Entity not found: {ticker}"}), 404
        entity = dict(entity)

        if q:
            # FTS Search
            fts_query = f"""
                SELECT f.id, f.entity_id, f.filing_type, f.fiscal_year, f.fiscal_quarter,
                       f.period_end_date, f.filed_date, f.accession_number, f.source_url,
                       f.local_file_path, f.status, snippet(filing_fts, 4, '<mark>', '</mark>', '...', 25) as snippet
                FROM filing_fts
                JOIN filing f ON filing_fts.filing_id = f.id
                WHERE f.entity_id = ? AND filing_fts MATCH ?
                ORDER BY f.filed_date DESC
                LIMIT 50
            """
            cur.execute(fts_query, (entity["id"], q))
        else:
            query = """
                SELECT id, entity_id, filing_type, fiscal_year, fiscal_quarter,
                       period_end_date, filed_date, accession_number, source_url,
                       local_file_path, status
                FROM filing
                WHERE entity_id = ?
            """
            params = [entity["id"]]
            if filing_type:
                query += " AND filing_type = ?"
                params.append(filing_type)
            query += " ORDER BY filed_date DESC LIMIT 100"
            cur.execute(query, params)

        filings = [dict(r) for r in cur.fetchall()]
        return jsonify({
            "status": "success",
            "ticker": entity["ticker"],
            "name": entity["name_ko"],
            "count": len(filings),
            "filings": filings
        })


@api_bp.route("/companies/<ticker>/news", methods=["GET"])
def get_company_news(ticker):
    """Return latest news for company from news table, with live auto-fetch fallback."""
    limit = int(request.args.get("limit", 40))
    source = request.args.get("source", "").strip().lower()
    force_refresh = request.args.get("refresh", "false").lower() in ("true", "1", "yes")

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, ticker, name_en, name_ko FROM entity WHERE UPPER(ticker) = UPPER(?)", (ticker,))
        entity = cur.fetchone()
        if not entity:
            return jsonify({"status": "error", "message": f"Entity not found: {ticker}"}), 404
        entity = dict(entity)

        clean_ticker = entity["ticker"].split(".")[0]

        def fetch_db_news():
            query = """
                SELECT id, url, title, snippet, source, company, ticker, score, published, collected_at
                FROM news
                WHERE (UPPER(ticker) = UPPER(?) OR UPPER(ticker) = UPPER(?) OR company LIKE ? OR company LIKE ? OR query LIKE ?)
            """
            params = [entity["ticker"], clean_ticker, f"%{entity['name_ko']}%", f"%{entity['name_en']}%", f"%{clean_ticker}%"]
            if source:
                query += " AND source = ?"
                params.append(source)
            query += " ORDER BY published DESC, score DESC LIMIT ?"
            params.append(limit)

            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

        news_items = fetch_db_news() if not force_refresh else []

        # If zero news found or user requested forced refresh, collect live via NewsCollector
        if len(news_items) == 0 or force_refresh:
            try:
                from app.services.news_collector import NewsCollector
                collector = NewsCollector()
                collector.collect_for_entity(entity["ticker"], entity["name_ko"], entity["name_en"])
                news_items = fetch_db_news()
            except Exception as e:
                print(f"[News API] Auto-fetch news error for {ticker}: {e}")

        return jsonify({
            "status": "success",
            "ticker": entity["ticker"],
            "name": entity["name_ko"],
            "count": len(news_items),
            "news": news_items
        })


@api_bp.route("/companies/<ticker>/analysts", methods=["GET"])
def get_company_analysts_data(ticker):
    """Return analyst reports and target price history for the company."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, ticker, name_en, name_ko FROM entity WHERE UPPER(ticker) = UPPER(?)", (ticker,))
        entity = cur.fetchone()
        if not entity:
            return jsonify({"status": "error", "message": f"Entity not found: {ticker}"}), 404
        entity = dict(entity)

        # 1. Analyst Reports
        cur.execute("""
            SELECT id, ticker, source_type, broker_name, analyst_name, report_date,
                   title, rating, action_type, target_price, current_price_at_report,
                   upside_pct, currency, pdf_url, summary_text
            FROM analyst_report
            WHERE entity_id = ?
            ORDER BY report_date DESC
            LIMIT 50
        """, (entity["id"],))
        reports = [dict(r) for r in cur.fetchall()]

        # 2. Target Price History (Bands)
        cur.execute("""
            SELECT date, close_price, target_mean, target_high, target_low, num_analysts
            FROM target_price_history
            WHERE entity_id = ?
            ORDER BY date ASC
        """, (entity["id"],))
        history = [dict(r) for r in cur.fetchall()]

        # Consensus Summary
        ratings_count = {}
        for r in reports:
            rt = (r.get("rating") or "BUY").upper()
            ratings_count[rt] = ratings_count.get(rt, 0) + 1

        return jsonify({
            "status": "success",
            "ticker": entity["ticker"],
            "name": entity["name_ko"],
            "reports_count": len(reports),
            "reports": reports,
            "target_history": history,
            "ratings_summary": ratings_count
        })


@api_bp.route("/companies/<ticker>/macro-links", methods=["GET"])
def get_company_macro_links(ticker):
    """Return company-specific Memory Claude connections (Contracts, Fabs, Datacenters)."""
    mem_id = TICKER_TO_MEM_ID.get(ticker.upper(), ticker.upper())

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, ticker, name_en, name_ko FROM entity WHERE UPPER(ticker) = UPPER(?)", (ticker,))
        entity = cur.fetchone()
        entity_name = entity["name_ko"] if entity else ticker

        # 1. Contracts where entity is buyer or seller
        alt_ticker = 'OPENAI' if ticker.upper() in ('OAI', 'OPENAI') else ticker
        cur.execute("""
            SELECT * FROM contracts
            WHERE buyer_id = ? OR seller_id = ?
               OR buyer_id = ? OR seller_id = ?
               OR buyer_id LIKE ? OR seller_id LIKE ?
               OR buyer_id LIKE ? OR seller_id LIKE ?
            ORDER BY announced_date DESC
        """, (mem_id, mem_id, alt_ticker, alt_ticker, f"%{ticker}%", f"%{ticker}%", f"%{alt_ticker}%", f"%{alt_ticker}%"))
        contracts = [dict(r) for r in cur.fetchall()]

        # 2. Fabs
        cur.execute("""
            SELECT * FROM fab_capacity
            WHERE entity_id = ? OR entity_id LIKE ? OR key_customers LIKE ?
            ORDER BY wspm_target DESC
        """, (mem_id, f"%{ticker}%", f"%{ticker}%"))
        fabs = [dict(r) for r in cur.fetchall()]

        # 3. Datacenters
        cur.execute("""
            SELECT * FROM datacenter_capacity
            WHERE entity_id = ? OR entity_id LIKE ?
            ORDER BY power_mw_target DESC
        """, (mem_id, f"%{ticker}%"))
        datacenters = [dict(r) for r in cur.fetchall()]

        return jsonify({
            "status": "success",
            "ticker": ticker,
            "name": entity_name,
            "contracts": contracts,
            "fabs": fabs,
            "datacenters": datacenters
        })


# ─── Macro Hub (Memory Claude Engine) Endpoints ───

@api_bp.route("/macro/sankey", methods=["GET"])
def get_macro_sankey_data():
    """Return Sankey nodes and flows for AI Capital Flows (L2 CapEx -> L8 Power)."""
    flows = [
        # [source, target, value_b, type, label]
        ['MS (마이크로소프트)', '오픈AI', 13.0, 'INVESTMENT', 'AI 파트너십 투자'],
        ['구글 (Alphabet)', '앤트로픽', 20.0, 'INVESTMENT', 'AI 모델 투자/크레딧'],
        ['아마존 (AWS)', '앤트로픽', 12.0, 'INVESTMENT', '베드록 모델 독점 파트너십'],
        ['오픈AI', '브로드컴', 65.0, 'ASIC', '10GW 커스텀 AI 가속기'],
        ['메타 (Meta)', '브로드컴', 10.0, 'ASIC', 'MTIA 커스텀 실리콘'],
        ['구글 (Alphabet)', '엔비디아', 30.0, 'SUPPLY', 'Blackwell GPU 클러스터'],
        ['메타 (Meta)', '엔비디아', 25.0, 'SUPPLY', 'B200 20만장 조달'],
        ['MS (마이크로소프트)', '엔비디아', 38.0, 'SUPPLY', 'Azure AI Blackwell 클러스터'],
        ['아마존 (AWS)', '엔비디아', 28.0, 'SUPPLY', 'EC2 UltraServer 인스턴스'],
        ['엔비디아', 'TSMC', 42.0, 'SUPPLY', '3nm 웨이퍼 & CoWoS-L 패키징'],
        ['브로드컴', 'TSMC', 20.0, 'SUPPLY', '4nm ASIC 파운드리'],
        ['엔비디아', 'SK하이닉스', 28.0, 'SUPPLY', 'HBM3E 8단/12단 독점 공급'],
        ['엔비디아', '삼성전자', 14.0, 'SUPPLY', 'HBM3E 보조 공급 및 인증'],
        ['엔비디아', '마이크론', 9.0, 'SUPPLY', 'HBM3E H200 납품'],
        ['브로드컴', 'SK하이닉스', 12.0, 'SUPPLY', '커스텀 XPU용 HBM3E'],
        ['앤트로픽', 'SK하이닉스', 15.0, 'SUPPLY', '메모리 다이렉트 구매'],
        ['구글 (Alphabet)', '버티브', 15.0, 'POWER', '고효율 액체냉각 CDU'],
        ['MS (마이크로소프트)', '버티브', 12.0, 'POWER', '모듈러 데이터센터 전력'],
        ['MS (마이크로소프트)', '이튼', 9.0, 'POWER', '변압기 및 배전 전력망'],
        ['엔비디아', '코어위브', 14.0, 'SUPPLY', 'Blackwell 우선 할당']
    ]

    # Node to Ticker Mapping for Drill-down
    node_to_ticker = {
        '구글 (Alphabet)': 'GOOGL',
        '아마존 (AWS)': 'AMZN',
        'MS (마이크로소프트)': 'MSFT',
        '메타 (Meta)': 'META',
        '엔비디아': 'NVDA',
        'AMD': 'AMD',
        '브로드컴': 'AVGO',
        'TSMC': 'TSM',
        'ASML': 'ASML',
        'SK하이닉스': '000660.KS',
        '삼성전자': '005930.KS',
        '마이크론': 'MU',
        '버티브': 'VRT',
        '이튼': 'ETN',
        '코어위브': 'CRWV',
        '오픈AI': 'MSFT',
        '앤트로픽': 'AMZN'
    }

    # Simulation sensitivities for companies
    companies_sens = [
        {'ticker': 'NVDA', 'name': '엔비디아', 'layer': 'L3 GPU', 'base': 160, 'sens': {'capex': 0.70, 'hbm': 0.10, 'asp': 0.85, 'yield': 0.30, 'reg': -0.40}},
        {'ticker': '000660.KS', 'name': 'SK하이닉스', 'layer': 'L5 HBM', 'base': 75, 'sens': {'capex': 0.35, 'hbm': 0.90, 'asp': 0.20, 'yield': 0.10, 'reg': -0.15}},
        {'ticker': 'TSM', 'name': 'TSMC', 'layer': 'L4 Foundry', 'base': 120, 'sens': {'capex': 0.50, 'hbm': 0.15, 'asp': 0.30, 'yield': 0.65, 'reg': -0.20}},
        {'ticker': 'AVGO', 'name': '브로드컴', 'layer': 'L3 ASIC', 'base': 70, 'sens': {'capex': 0.45, 'hbm': 0.05, 'asp': 0.10, 'yield': 0.20, 'reg': -0.25}},
        {'ticker': '005930.KS', 'name': '삼성전자', 'layer': 'L5 Memory', 'base': 270, 'sens': {'capex': 0.20, 'hbm': 0.50, 'asp': 0.15, 'yield': 0.40, 'reg': -0.10}},
        {'ticker': 'MRVL', 'name': '마벨', 'layer': 'L6 Optical', 'base': 8, 'sens': {'capex': 0.55, 'hbm': 0.05, 'asp': 0.05, 'yield': 0.10, 'reg': -0.30}},
        {'ticker': 'AMD', 'name': 'AMD', 'layer': 'L3 GPU', 'base': 25, 'sens': {'capex': 0.40, 'hbm': 0.08, 'asp': 0.50, 'yield': 0.15, 'reg': -0.20}},
        {'ticker': 'ASML', 'name': 'ASML', 'layer': 'L4 Equipment', 'base': 42, 'sens': {'capex': 0.30, 'hbm': 0.20, 'asp': 0.05, 'yield': -0.10, 'reg': -0.15}},
        {'ticker': 'MU', 'name': '마이크론', 'layer': 'L5 Memory', 'base': 38, 'sens': {'capex': 0.25, 'hbm': 0.60, 'asp': 0.15, 'yield': 0.30, 'reg': -0.12}},
        {'ticker': 'VRT', 'name': '버티브', 'layer': 'L8 Power/Cooling', 'base': 18, 'sens': {'capex': 0.65, 'hbm': 0.05, 'asp': 0.15, 'yield': 0.10, 'reg': -0.10}}
    ]

    return jsonify({
        "status": "success",
        "flows": flows,
        "drilldown_map": node_to_ticker,
        "companies": companies_sens
    })


@api_bp.route("/macro/hbm-balance", methods=["GET"])
def get_macro_hbm_balance_data():
    """Return HBM supply vs demand balance and Trio company share data."""
    timeline = [
        {"period": "2024-Q3", "demand_bit": 180, "supply_bit": 120, "gap_pct": -33.3, "status": "공급부족 심화"},
        {"period": "2024-Q4", "demand_bit": 260, "supply_bit": 190, "gap_pct": -26.9, "status": "공급부족"},
        {"period": "2025-Q1", "demand_bit": 360, "supply_bit": 290, "gap_pct": -19.4, "status": "공급부족"},
        {"period": "2025-Q2", "demand_bit": 480, "supply_bit": 410, "gap_pct": -14.6, "status": "공급부족 완화"},
        {"period": "2025-Q3", "demand_bit": 600, "supply_bit": 540, "gap_pct": -10.0, "status": "수급 균형 근접"},
        {"period": "2025-Q4", "demand_bit": 720, "supply_bit": 680, "gap_pct": -5.6, "status": "수급 균형 근접"},
        {"period": "2026-Q1", "demand_bit": 850, "supply_bit": 830, "gap_pct": -2.4, "status": "수급 균형"},
        {"period": "2026-Q2", "demand_bit": 980, "supply_bit": 990, "gap_pct": +1.0, "status": "크로스오버 (균형)"},
        {"period": "2026-Q3", "demand_bit": 1100, "supply_bit": 1150, "gap_pct": +4.5, "status": "공급과잉 진입"},
        {"period": "2026-Q4", "demand_bit": 1220, "supply_bit": 1310, "gap_pct": +7.4, "status": "공급과잉 확대"}
    ]

    asp_data = [
        {"name": "범용 DDR5", "asp": 0.42, "premium": 1.0},
        {"name": "HBM3 (8단)", "asp": 1.45, "premium": 3.45},
        {"name": "HBM3E (8/12단)", "asp": 2.00, "premium": 4.76},
        {"name": "HBM4 (12/16단)", "asp": 2.85, "premium": 6.78}
    ]

    market_share = [
        {"ticker": "000660.KS", "name": "SK하이닉스", "revenue_b": 20.0, "share_pct": 63.5, "color": "#f59e0b"},
        {"ticker": "005930.KS", "name": "삼성전자", "revenue_b": 8.0, "share_pct": 25.4, "color": "#38bdf8"},
        {"ticker": "MU", "name": "마이크론", "revenue_b": 3.5, "share_pct": 11.1, "color": "#a855f7"}
    ]

    return jsonify({
        "status": "success",
        "timeline": timeline,
        "asp_data": asp_data,
        "market_share": market_share
    })


@api_bp.route("/macro/contracts", methods=["GET"])
def get_macro_contracts_data():
    """Return all AI Mega Contracts with total valuation and status."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM contracts
            ORDER BY value_b DESC, announced_date DESC
        """)
        contracts = [dict(r) for r in cur.fetchall()]

        total_value = sum(c["value_b"] for c in contracts if c.get("value_b"))

        return jsonify({
            "status": "success",
            "count": len(contracts),
            "total_value_b": round(total_value, 1),
            "contracts": contracts
        })


@api_bp.route("/macro/capacity", methods=["GET"])
def get_macro_capacity_data():
    """Return Fab and Datacenter capacity monitoring lists."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM fab_capacity ORDER BY wspm_target DESC")
        fabs = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM datacenter_capacity ORDER BY power_mw_target DESC")
        datacenters = [dict(r) for r in cur.fetchall()]

        total_dc_gw = sum((dc.get("power_mw_target") or 0) for dc in datacenters) / 1000.0

        return jsonify({
            "status": "success",
            "fabs_count": len(fabs),
            "fabs": fabs,
            "datacenters_count": len(datacenters),
            "total_dc_target_gw": round(total_dc_gw, 2),
            "datacenters": datacenters
        })


@api_bp.route("/ledger/2026", methods=["GET"])
def get_2026_ledger():
    """
    Return 2026 full-year unpivoted ledger events (Plan A 8 columns).
    Supports filtering by ticker, layer, month, confidence, and search query.
    """
    from app.services.ledger_service import LedgerService
    
    ticker = request.args.get("ticker")
    layer = request.args.get("layer")
    month = request.args.get("month")
    confidence = request.args.get("confidence")
    query = request.args.get("query")
    limit = int(request.args.get("limit", 1500))
    offset = int(request.args.get("offset", 0))

    result = LedgerService.get_filtered_events(
        ticker=ticker,
        layer=layer,
        month=month,
        confidence=confidence,
        query=query,
        limit=limit,
        offset=offset
    )
    return jsonify(result)


@api_bp.route("/ledger/2026/export", methods=["GET"])
def export_2026_ledger_csv():
    """Export filtered 2026 ledger events as a CSV download."""
    from flask import Response
    from app.services.ledger_service import LedgerService
    
    ticker = request.args.get("ticker")
    layer = request.args.get("layer")
    month = request.args.get("month")
    confidence = request.args.get("confidence")
    query = request.args.get("query")

    result = LedgerService.get_filtered_events(
        ticker=ticker,
        layer=layer,
        month=month,
        confidence=confidence,
        query=query,
        limit=5000,
        offset=0
    )
    csv_data = LedgerService.export_csv(result["events"])
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=2026_AI_Semiconductor_ValueChain_Ledger.csv"}
    )





