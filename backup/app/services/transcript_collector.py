"""
Earnings Call Transcript Collector & Manager Service
Manages full conference call transcripts, executive prepared remarks,
and analyst Q&A sessions for key tech and semiconductor leaders.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from app.models.database import get_db, query_db
from app.config import FILINGS_DIR

TRANSCRIPTS_DIR = Path(FILINGS_DIR) / "earning_calls"
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


class TranscriptCollector:

    def save_transcript(
        self,
        ticker: str,
        fiscal_year: str,
        fiscal_quarter: str,
        call_date: str,
        transcript_text: str,
        call_time_et: Optional[str] = "17:00 ET",
        source_url: Optional[str] = None,
        status: str = "REVIEWED"
    ) -> Dict[str, Any]:
        """Insert or update a conference call transcript."""
        entity = query_db("SELECT id, ticker, name_ko, name_en FROM entity WHERE ticker = ?", (ticker,), one=True)
        if not entity:
            return {"status": "error", "message": f"Entity not found for ticker: {ticker}"}

        # Save to local file for backup/indexing
        clean_fy = str(fiscal_year)
        clean_fq = fiscal_quarter.upper()
        filename = f"{ticker}_{clean_fy}_{clean_fq}.txt"
        file_path = TRANSCRIPTS_DIR / filename
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(transcript_text)
            local_path = str(file_path)
        except Exception as e:
            local_path = None

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO earning_call (
                    entity_id, fiscal_year, fiscal_quarter, call_date, call_time_et,
                    transcript_text, source_url, local_file_path, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_id, fiscal_year, fiscal_quarter)
                DO UPDATE SET
                    call_date = excluded.call_date,
                    call_time_et = excluded.call_time_et,
                    transcript_text = excluded.transcript_text,
                    source_url = excluded.source_url,
                    local_file_path = excluded.local_file_path,
                    status = excluded.status
                """,
                (entity["id"], clean_fy, clean_fq, call_date, call_time_et, transcript_text, source_url, local_path, status)
            )
            call_id = cur.lastrowid

        return {
            "status": "success",
            "id": call_id,
            "ticker": ticker,
            "fiscal_year": clean_fy,
            "fiscal_quarter": clean_fq,
            "call_date": call_date,
            "char_count": len(transcript_text)
        }

    def get_transcripts_list(
        self,
        ticker: Optional[str] = None,
        layer_code: Optional[str] = None,
        fiscal_year: Optional[str] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Retrieve list of transcripts with preview summaries."""
        query = """
            SELECT c.id, c.entity_id, c.fiscal_year, c.fiscal_quarter, c.call_date, c.call_time_et,
                   c.source_url, c.status, c.created_at,
                   e.ticker, e.name_ko, e.name_en, e.layer_code,
                   SUBSTR(c.transcript_text, 1, 350) as excerpt,
                   LENGTH(c.transcript_text) as total_chars
            FROM earning_call c
            JOIN entity e ON c.entity_id = e.id
            WHERE 1=1
        """
        params = []
        if ticker:
            query += " AND e.ticker = ?"
            params.append(ticker)
        if layer_code:
            query += " AND e.layer_code = ?"
            params.append(layer_code)
        if fiscal_year:
            query += " AND c.fiscal_year = ?"
            params.append(str(fiscal_year))

        query += " ORDER BY c.call_date DESC, c.fiscal_year DESC, c.fiscal_quarter DESC LIMIT ?"
        params.append(limit)

        rows = query_db(query, tuple(params))
        return rows

    def get_transcript_detail(self, call_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve full transcript text, sections, and metadata by call ID."""
        row = query_db(
            """
            SELECT c.*, e.ticker, e.name_ko, e.name_en, e.layer_code
            FROM earning_call c
            JOIN entity e ON c.entity_id = e.id
            WHERE c.id = ?
            """,
            (call_id,),
            one=True
        )
        if not row:
            return None

        data = dict(row)
        text = data.get("transcript_text") or ""
        data["sections"] = self._parse_transcript_sections(text)
        return data

    def get_transcript_by_quarter(self, ticker: str, fiscal_year: str, fiscal_quarter: str) -> Optional[Dict[str, Any]]:
        """Retrieve transcript by ticker and quarter."""
        row = query_db(
            """
            SELECT c.*, e.ticker, e.name_ko, e.name_en, e.layer_code
            FROM earning_call c
            JOIN entity e ON c.entity_id = e.id
            WHERE e.ticker = ? AND c.fiscal_year = ? AND c.fiscal_quarter = ?
            """,
            (ticker, str(fiscal_year), fiscal_quarter.upper()),
            one=True
        )
        if not row:
            return None

        data = dict(row)
        data["sections"] = self._parse_transcript_sections(data.get("transcript_text") or "")
        return data

    def _parse_transcript_sections(self, text: str) -> Dict[str, Any]:
        """Split transcript into Executive Remarks and Q&A session if present."""
        qa_markers = [
            "QUESTION AND ANSWER",
            "QUESTION-AND-ANSWER",
            "Q&A SESSION",
            "질의응답",
            "QUESTIONS AND ANSWERS"
        ]
        upper_text = text.upper()
        split_idx = -1
        for marker in qa_markers:
            idx = upper_text.find(marker)
            if idx != -1:
                split_idx = idx
                break

        if split_idx != -1:
            prepared = text[:split_idx].strip()
            qa_session = text[split_idx:].strip()
        else:
            prepared = text.strip()
            qa_session = None

        return {
            "has_qa": qa_session is not None,
            "prepared_remarks": prepared,
            "qa_session": qa_session
        }

    def seed_sample_transcripts(self) -> int:
        """Seed authentic, high-value conference call transcripts for AI leaders."""
        from app.services.transcripts_dataset import FULL_TRANSCRIPTS_SEED

        seeded_count = 0
        for s in FULL_TRANSCRIPTS_SEED:
            res = self.save_transcript(
                ticker=s["ticker"],
                fiscal_year=s["fiscal_year"],
                fiscal_quarter=s["fiscal_quarter"],
                call_date=s["call_date"],
                call_time_et=s["call_time_et"],
                source_url=s["source_url"],
                transcript_text=s["text"]
            )
            if res.get("status") == "success":
                seeded_count += 1

        return seeded_count
