# AGENTS.md — AI Agent Guidelines for 10_QK_EARNING

Welcome to the **10_QK_EARNING** project repository. This document defines the architectural guidelines, domain knowledge, coding conventions, and operational rules for AI coding agents (Antigravity, Cursor, Copilot, etc.) working on this codebase.

---

## 1. Project Overview & Domain

* **Domain**: AI Semiconductor Value Chain Monitoring & SEC Filings Intelligence
* **Core Purpose**:
  * Track SEC EDGAR filings (`10-K`, `10-Q`, `8-K`, `S-1`) for major AI/tech companies (NVDA, TSM, MSFT, GOOGL, AMZN, META, AAPL, etc.).
  * Track leading business indicators: Korea Customs Service (관세청 UNIPASS) 10-day semiconductor export stats (released on the 1st, 11th, and 21st of each month).
  * Monitor market consensus (EPS / Revenue), compute Beat/Miss surprises, and measure stock price reaction.
  * Monitor GPU rental spot pricing and supply chain indicators.
* **Stack**:
  * **Backend**: Python 3.10+, Flask (App Factory pattern)
  * **Database**: SQLite3 (`data/qk_earning.db`) with FTS5 for full-text search
  * **Frontend**: Vanilla HTML5, Vanilla CSS3 (Dark modern UI), Vanilla JavaScript, Chart.js (CDN)
  * **Testing**: `pytest`

---

## 2. Critical Operating Rules for Agents

### ⚠️ Rule 1: Git Commit & Push Policy
* **NEVER automatically run `git commit` or `git push` without explicit user instruction.**
* The user explicitly manages staging, committing, and pushing changes. Agents should only modify files and provide git command suggestions for the user to execute.

### ⚠️ Rule 2: SEC EDGAR Rate Limiting & User-Agent
* Any request to `sec.gov` or `data.sec.gov` **MUST** include a compliant User-Agent header:
  * Format: `User-Agent: SampleCompanyName AdminContact@sampledomain.com`
  * Defined in: `app/config.py` (`SEC_USER_AGENT`)
* Enforce request pacing: **Maximum 10 requests per second** (use `SEC_RATE_LIMIT_DELAY = 0.2s` or greater).

### ⚠️ Rule 3: Database & File Handling
* The SQLite DB resides at `data/qk_earning.db`.
* Downloaded raw filing files reside at `data/filings/`.
* Both are intentionally excluded from Git via `.gitignore`. Do not commit binaries or raw data into git.
* Keep DB queries parameterized to prevent SQL injection.

### ⚠️ Rule 4: Server & Port Management
* Default port is **`5001`** (configured via `PORT` environment variable in `app/config.py`).
* Before attempting to spawn or restart the server, check if port 5001 is already occupied using `lsof -i :5001` or check background tasks.

---

## 3. Architecture & Code Layout

```text
10_QK_EARNING/
├── app/
│   ├── config.py                 # App configurations (port, DB path, SEC User-Agent)
│   ├── __init__.py               # Flask app factory (create_app)
│   ├── models/
│   │   └── database.py           # SQLite connection helper, table schema definitions
│   ├── routes/
│   │   └── api.py                # REST API endpoints (/api/*)
│   └── services/
│       ├── edgar_collector.py    # SEC EDGAR metadata & filing collector
│       ├── kr_export_collector.py# Korea Customs Service 10-day export collector
│       └── price_collector.py    # Yahoo Finance daily price collector
├── data/                         # Local database & filing cache (git ignored)
├── docs/                         # Specification & design documentation
├── scripts/
│   ├── init_db.py                # DB schema initialization script
│   └── seed_entities.py          # Initial target company seeding script
├── static/
│   ├── css/style.css             # Main styling (Dark theme)
│   ├── js/app.js                 # Dashboard logic & Chart.js rendering
│   └── index.html                # Single-page dashboard UI
├── tests/
│   └── test_basic.py             # Basic route & integration tests
├── requirements.txt              # Production/development dependencies
├── run.py                        # Application entry point
├── README.md                     # Human-facing project overview
└── AGENTS.md                     # This agent instruction file
```

---

## 4. Coding Conventions

* **Python**:
  * Use Python 3.10+ type hints where applicable (`str`, `dict[str, Any]`, `Optional[int]`).
  * Service modules must return structured dictionaries or dataclasses, catching network errors gracefully without crashing the web app.
  * Maintain database transactions properly (`conn.commit()`, `conn.rollback()` in try/finally blocks).
* **Frontend**:
  * Do **NOT** introduce heavy build tools (Webpack, Vite, npm builds) unless requested. Keep it Vanilla HTML/CSS/JS for fast, lightweight local execution.
  * Maintain the dark modern palette and responsive layout defined in `static/css/style.css`.
* **Testing**:
  * Write test cases in `tests/test_*.py` using `pytest`.
  * Ensure tests can run against an in-memory SQLite database or temporary file without polluting production `data/qk_earning.db`.

---

## 5. Next Planned Work Items (Roadmap Reference)

When assisting the user with ongoing tasks, refer to these roadmap priorities:
1. **Filing Raw Text Parser & Viewer**: Complete `download_docs=True` in `edgar_collector.py`, extract clean text with `BeautifulSoup`, and enable full-text modal viewing.
2. **Consensus & Beat/Miss Dashboard**: Implement `consensus` table UI, Beat/Inline/Miss calculation, and 1-day/5-day post-earnings price delta calculation.
3. **Korea Customs 10-Day Export Tracker**: Complete automated parsing of semiconductor 10-day export data and visualize YoY trends in the dashboard.
4. **Earnings Call Transcript Pipeline**: Parse 8-K Exhibit 99.1 press releases and earnings call transcripts.

---

## 6. Key Reference Documents

* [docs/2026-09-17_요건정의서.md](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/docs/2026-09-17_%EC%92%94%EA%B1%B4%EC%A0%95%EC%9D%98%EC%84%9C.md) — System requirements v1.1
* [docs/2026-09-17_데이터수집가이드.md](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/docs/2026-09-17_%EB%8D%B0%EC%9D%B4%ED%84%B0%EC%88%98%EC%A7%91%EA%B0%80%EC%9D%B4%EB%93%9C.md) — Data collection guide
* [docs/2026-09-18_보완및제안사항.md](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/docs/2026-09-18_%EB%B3%B4%EC%99%84%EB%B0%8F%EC%A0%9C%EC%95%88%EC%82%AC%ED%95%AD.md) — Enhancement & proposals
