"""
PDF Indexer Service for Analyst Reports.
Extracts full text from downloaded Korean/Global research PDFs using pypdf
and indexes them into SQLite FTS5 (analyst_report_fts) for ultra-fast full-text search.
Runs background worker to prevent HTTP timeouts and database lock contention.
"""
import os
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
import pypdf

from app.config import REPORTS_DIR
from app.models.database import get_db, query_db, execute_db


class PdfReportIndexer:
    """Extracts text from downloaded research PDFs and indexes into FTS5."""

    _is_indexing = False
    _progress = {
        "status": "idle",
        "indexed_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "total": 0,
        "current_file": ""
    }

    @classmethod
    def extract_text_from_pdf(cls, pdf_path: str, max_pages: int = 10) -> str:
        """Extract all readable text from a local PDF file up to max_pages."""
        p = Path(pdf_path)
        if not p.is_file():
            return ""

        extracted_text_parts = []
        try:
            reader = pypdf.PdfReader(str(p))
            num_pages = min(len(reader.pages), max_pages)
            for page_idx in range(num_pages):
                try:
                    txt = reader.pages[page_idx].extract_text()
                    if txt and txt.strip():
                        extracted_text_parts.append(f"[Page {page_idx + 1}]\n" + txt.strip())
                except Exception:
                    continue
        except Exception as e:
            print(f"[PdfIndexer] Error extracting text from {p.name}: {e}")
            return ""

        return "\n\n".join(extracted_text_parts)

    @classmethod
    def get_indexing_status(cls) -> Dict[str, Any]:
        """Return current status of background indexing process."""
        fts_count = query_db("SELECT count(*) as cnt FROM analyst_report_fts", one=True)
        total_reports = query_db(
            "SELECT count(*) as cnt FROM analyst_report WHERE local_pdf_path IS NOT NULL AND local_pdf_path != ''",
            one=True
        )

        res = dict(cls._progress)
        res["total_fts_indexed"] = fts_count["cnt"] if fts_count else 0
        res["total_pdf_candidates"] = total_reports["cnt"] if total_reports else 0
        res["is_running"] = cls._is_indexing
        return res

    @classmethod
    def index_all_reports_background(cls) -> Dict[str, Any]:
        """Start background indexing thread if not already running."""
        if cls._is_indexing:
            return {"status": "already_running", **cls.get_indexing_status()}

        thread = threading.Thread(target=cls._run_indexing_worker, daemon=True)
        thread.start()
        return {"status": "started", "message": "Background PDF indexing started."}

    @classmethod
    def _run_indexing_worker(cls):
        """Worker function running in a separate thread."""
        cls._is_indexing = True
        cls._progress["status"] = "indexing"
        cls._progress["indexed_count"] = 0
        cls._progress["skipped_count"] = 0
        cls._progress["failed_count"] = 0

        try:
            reports = query_db(
                """
                SELECT id, ticker, broker_name, title, local_pdf_path
                FROM analyst_report
                WHERE local_pdf_path IS NOT NULL AND local_pdf_path != ''
                """
            )
            cls._progress["total"] = len(reports)

            for r in reports:
                report_id = r["id"]
                ticker = r["ticker"]
                broker = r["broker_name"]
                title = r["title"]
                pdf_path = r["local_pdf_path"]
                cls._progress["current_file"] = f"{ticker} - {title[:30]}"

                # Check if already in FTS
                check = query_db(
                    "SELECT 1 FROM analyst_report_fts WHERE report_id = ?",
                    (report_id,),
                    one=True
                )
                if check:
                    cls._progress["skipped_count"] += 1
                    continue

                # Resolve file path
                resolved = None
                if os.path.exists(pdf_path):
                    resolved = Path(pdf_path)
                elif (REPORTS_DIR / pdf_path).is_file():
                    resolved = REPORTS_DIR / pdf_path
                elif Path(pdf_path).is_file():
                    resolved = Path(pdf_path)

                if not resolved:
                    cls._progress["failed_count"] += 1
                    continue

                # Extract text outside of DB transaction
                content_text = cls.extract_text_from_pdf(str(resolved), max_pages=10)
                if not content_text or len(content_text.strip()) < 10:
                    cls._progress["failed_count"] += 1
                    continue

                # Short atomic insert per file
                try:
                    execute_db(
                        """
                        INSERT INTO analyst_report_fts(report_id, ticker, broker_name, title, content_text)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (report_id, ticker, broker, title, content_text),
                        commit=True
                    )
                    cls._progress["indexed_count"] += 1
                except Exception as insert_err:
                    print(f"[PdfIndexer] Insert error for report {report_id}: {insert_err}")
                    cls._progress["failed_count"] += 1

            cls._progress["status"] = "completed"
            cls._progress["current_file"] = ""
        except Exception as e:
            cls._progress["status"] = f"error: {e}"
            print(f"[PdfIndexer] Worker exception: {e}")
        finally:
            cls._is_indexing = False

    @classmethod
    def search_reports(
        cls,
        query: str,
        ticker: Optional[str] = None,
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Full-text search in analyst report contents using SQLite FTS5.
        Returns matched reports with highlighted snippets.
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        # Remove special FTS syntax characters
        sanitized = clean_q.replace('"', '').replace("'", "").replace("*", "").replace(":", "")
        tokens = [f"{tok}*" for tok in sanitized.split() if tok]
        if not tokens:
            return []
        match_clause = " AND ".join(tokens)

        sql = """
            SELECT 
                f.report_id,
                f.ticker,
                f.broker_name,
                f.title,
                snippet(analyst_report_fts, 4, '<mark class="fts-hl">', '</mark>', '...', 25) AS snippet,
                ar.report_date,
                ar.target_price,
                ar.rating AS investment_opinion,
                ar.currency,
                ar.local_pdf_path
            FROM analyst_report_fts f
            JOIN analyst_report ar ON f.report_id = ar.id
            WHERE analyst_report_fts MATCH ?
        """
        params = [match_clause]

        if ticker and ticker.strip():
            sql += " AND f.ticker = ?"
            params.append(ticker.strip().upper())

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        try:
            results = query_db(sql, tuple(params))
            return [dict(r) for r in results]
        except Exception as e:
            print(f"[PdfIndexer] Search error: {e}")
            return []
