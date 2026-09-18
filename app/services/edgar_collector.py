"""
SEC EDGAR Data Collector Service
Fetches 10-Q, 10-K, 8-K, 20-F, 6-K filings for companies with CIK numbers.
Complies with SEC rate limit rules (<10 requests/second with User-Agent header).
"""
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from app.config import SEC_USER_AGENT, SEC_RATE_LIMIT_DELAY, FILINGS_DIR
from app.models.database import get_db, query_db

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{primary_doc}"

class EdgarCollector:
    def __init__(self):
        self.headers = {
            "User-Agent": SEC_USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov"
        }
        self.archive_headers = {
            "User-Agent": SEC_USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"
        }

    def _rate_limit(self):
        time.sleep(SEC_RATE_LIMIT_DELAY)

    def fetch_submissions_meta(self, cik: str):
        """Fetch entity submissions JSON from SEC EDGAR."""
        cik_clean = cik.strip().zfill(10)
        url = SEC_SUBMISSIONS_URL.format(cik=cik_clean)
        self._rate_limit()

        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"[EDGAR] Failed to fetch CIK {cik}: HTTP {resp.status_code}")
                return None
        except Exception as e:
            print(f"[EDGAR] Error fetching CIK {cik}: {e}")
            return None

    def download_filing_document(self, cik: str, accession_number: str, primary_doc: str, target_folder: Path):
        """Download raw filing document (HTML or HTM) and extract clean readable text."""
        cik_int = str(int(cik))
        acc_nodash = accession_number.replace("-", "")
        url = SEC_ARCHIVE_URL.format(cik_int=cik_int, acc_nodash=acc_nodash, primary_doc=primary_doc)
        self._rate_limit()

        try:
            resp = requests.get(url, headers=self.archive_headers, timeout=25)
            if resp.status_code == 200:
                target_folder.mkdir(parents=True, exist_ok=True)
                local_path = target_folder / f"{accession_number}_{primary_doc}"
                with open(local_path, "wb") as f:
                    f.write(resp.content)

                # Extract cleaned text by stripping scripts and styles
                try:
                    soup = BeautifulSoup(resp.content, "lxml")
                    for s in soup(["script", "style", "noscript", "header", "footer"]):
                        s.decompose()
                    # Replace multiple whitespaces/newlines with single whitespace
                    lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = "\n".join(chunk for chunk in chunks if chunk)
                except Exception:
                    text = resp.text[:100000]

                return str(local_path), url, text[:300000]
            return None, url, ""
        except Exception as e:
            print(f"[EDGAR] Error downloading document {primary_doc}: {e}")
            return None, url, ""

    def download_single_filing(self, filing_id: int):
        """Download document and update FTS for an existing filing record."""
        filing = query_db(
            """
            SELECT f.*, e.sec_cik, e.ticker
            FROM filing f
            JOIN entity e ON f.entity_id = e.id
            WHERE f.id = ?
            """,
            (filing_id,),
            one=True
        )
        if not filing:
            return {"status": "error", "message": f"Filing {filing_id} not found"}

        cik = filing.get("sec_cik")
        acc_num = filing.get("accession_number")
        form = filing.get("filing_type")
        if not cik or not acc_num:
            return {"status": "error", "message": "Missing CIK or Accession Number"}

        # Look up primary document name from SEC submissions
        meta = self.fetch_submissions_meta(cik)
        if not meta or "filings" not in meta or "recent" not in meta["filings"]:
            return {"status": "error", "message": "Could not fetch SEC metadata"}

        recent = meta["filings"]["recent"]
        acc_list = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        primary_doc = ""
        if acc_num in acc_list:
            idx = acc_list.index(acc_num)
            if idx < len(primary_docs):
                primary_doc = primary_docs[idx]

        if not primary_doc:
            # fallback common naming
            primary_doc = f"{acc_num}.txt"

        folder = FILINGS_DIR / form
        local_path, src_url, raw_text = self.download_filing_document(cik, acc_num, primary_doc, folder)

        if not raw_text and not local_path:
            return {"status": "error", "message": "Failed to download filing document"}

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE filing
                SET source_url = ?, local_file_path = ?, raw_text = ?, status = 'DOWNLOADED'
                WHERE id = ?
                """,
                (src_url, local_path, raw_text, filing_id)
            )
            # Refresh FTS5 index
            cur.execute("DELETE FROM filing_fts WHERE filing_id = ?", (filing_id,))
            cur.execute(
                """
                INSERT INTO filing_fts (filing_id, ticker, filing_type, fiscal_period, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (filing_id, filing["ticker"], form, f"{filing['fiscal_year']}-{filing['fiscal_quarter']}", raw_text[:50000])
            )

        return {
            "status": "success",
            "filing_id": filing_id,
            "ticker": filing["ticker"],
            "form": form,
            "text_length": len(raw_text),
            "local_path": local_path
        }

    def collect_for_entity(self, ticker: str, form_types=None, limit=10, download_docs=True):
        """Collect filings for a single ticker."""
        if form_types is None:
            form_types = ["10-Q", "10-K", "8-K", "20-F", "6-K"]

        entity = query_db("SELECT id, ticker, name_en, sec_cik, fiscal_year_end FROM entity WHERE ticker = ?", (ticker,), one=True)
        if not entity:
            return {"error": f"Entity not found for ticker {ticker}", "count": 0}

        cik = entity["sec_cik"]
        if not cik:
            return {"error": f"No SEC CIK configured for {ticker} ({entity['name_en']})", "count": 0}

        meta = self.fetch_submissions_meta(cik)
        if not meta or "filings" not in meta or "recent" not in meta["filings"]:
            return {"error": f"No filing data available from SEC for {ticker}", "count": 0}

        recent = meta["filings"]["recent"]
        forms = recent.get("form", [])
        accession_nums = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])

        collected = []
        target_indices = [i for i, f in enumerate(forms) if f in form_types][:limit]

        with get_db() as conn:
            cur = conn.cursor()
            for idx in target_indices:
                form = forms[idx]
                acc_num = accession_nums[idx]
                f_date = filing_dates[idx] if idx < len(filing_dates) else None
                r_date = report_dates[idx] if idx < len(report_dates) else None
                p_doc = primary_docs[idx] if idx < len(primary_docs) else ""

                # Estimate fiscal year and quarter respecting entity's fiscal year end
                fy_end = entity.get("fiscal_year_end") or "12"
                date_str = r_date or f_date or ""
                year = int(date_str[:4]) if len(date_str) >= 4 else None
                month = int(date_str[5:7]) if len(date_str) >= 7 else 1

                if fy_end == "01":
                    # For entities with January fiscal year end (e.g. NVDA):
                    # Feb-Apr: Q1, May-Jul: Q2, Aug-Oct: Q3, Nov-Jan: Q4 / FY
                    if month in [2, 3, 4]:
                        quarter = "Q1"
                        fiscal_year = str(year)
                    elif month in [5, 6, 7]:
                        quarter = "Q2"
                        fiscal_year = str(year)
                    elif month in [8, 9, 10]:
                        quarter = "Q3"
                        fiscal_year = str(year)
                    else: # month in [11, 12, 1]
                        quarter = "FY" if form in ["10-K", "20-F"] else "Q4"
                        fiscal_year = str(year - 1 if month == 1 else year)
                else:
                    fiscal_year = str(year) if year else ""
                    quarter = "FY" if form in ["10-K", "20-F"] else f"Q{(month - 1) // 3 + 1}"

                # Download filing if enabled
                local_path, src_url, raw_text = None, "", ""
                if download_docs and p_doc:
                    folder = FILINGS_DIR / form
                    local_path, src_url, raw_text = self.download_filing_document(cik, acc_num, p_doc, folder)

                cur.execute(
                    """
                    INSERT INTO filing (
                        entity_id, filing_type, fiscal_year, fiscal_quarter,
                        period_end_date, filed_date, accession_number,
                        source_url, local_file_path, raw_text, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(entity_id, filing_type, fiscal_year, fiscal_quarter, accession_number)
                    DO UPDATE SET
                        source_url=coalesce(excluded.source_url, filing.source_url),
                        local_file_path=coalesce(excluded.local_file_path, filing.local_file_path),
                        raw_text=coalesce(excluded.raw_text, filing.raw_text),
                        status='DOWNLOADED'
                    """,
                    (
                        entity["id"], form, fiscal_year, quarter,
                        r_date, f_date, acc_num,
                        src_url, local_path, raw_text, "DOWNLOADED"
                    )
                )

                # Robust filing_id resolution
                cur.execute(
                    "SELECT id FROM filing WHERE entity_id = ? AND accession_number = ?",
                    (entity["id"], acc_num)
                )
                f_row = cur.fetchone()
                filing_id = f_row[0] if f_row else None

                # Update FTS index if text available
                if raw_text and filing_id:
                    cur.execute("DELETE FROM filing_fts WHERE filing_id = ?", (filing_id,))
                    cur.execute(
                        """
                        INSERT INTO filing_fts (filing_id, ticker, filing_type, fiscal_period, content)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (filing_id, ticker, form, f"{fiscal_year}-{quarter}", raw_text[:50000])
                    )

                collected.append({
                    "form": form,
                    "accessionNumber": acc_num,
                    "filingDate": f_date,
                    "reportDate": r_date,
                    "fiscalYear": fiscal_year,
                    "quarter": quarter,
                    "hasText": bool(raw_text)
                })

        return {"ticker": ticker, "collected": collected, "count": len(collected)}
