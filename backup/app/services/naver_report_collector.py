"""
Naver Securities Research Report Collector & PDF Downloader
Collects analyst reports, target prices, ratings, and downloads original PDFs for Korean companies.
"""
import os
import re
import time
import json
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.config import KR_REPORTS_DIR
from app.models.database import query_db, execute_db

logger = logging.getLogger(__name__)

NAVER_RESEARCH_LIST_URL = "https://m.stock.naver.com/api/research/company?page={page}&pageSize=50"
NAVER_RESEARCH_DETAIL_URL = "https://m.stock.naver.com/api/research/company/{research_id}"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class NaverReportCollector:
    def __init__(self, delay_sec: float = 1.0):
        self.delay_sec = delay_sec
        self.headers = {"User-Agent": USER_AGENT}

    def _http_get_json(self, url: str) -> Optional[Any]:
        """Fetch URL and parse JSON with error handling."""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
        return None

    def _download_pdf(self, pdf_url: str, local_path: Path) -> bool:
        """Download PDF file to local storage if not already present."""
        if not pdf_url:
            return False
        
        # If already downloaded, skip
        if local_path.exists() and local_path.stat().st_size > 1000:
            return True

        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            req = urllib.request.Request(pdf_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status == 200:
                    content = resp.read()
                    if content.startswith(b"%PDF"):
                        with open(local_path, "wb") as f:
                            f.write(content)
                        return True
                    else:
                        logger.warning(f"Downloaded content from {pdf_url} is not a valid PDF")
        except Exception as e:
            logger.warning(f"Failed to download PDF {pdf_url}: {e}")
        return False

    def collect_reports_for_ticker(
        self,
        ticker: str,
        download_pdf: bool = True,
        max_scan_pages: int = 10,
        max_reports: int = 25
    ) -> Dict[str, Any]:
        """
        Collect analyst reports for a specific Korean ticker (e.g. '000660.KS' or '000660').
        Finds reports, extracts target prices and ratings, and downloads PDFs.
        """
        # 1. Normalize item code
        clean_code = ticker.replace(".KS", "").replace(".KQ", "").strip()
        
        # Look up entity in database
        entity = query_db(
            "SELECT id, ticker, name_ko, name_en FROM entity WHERE ticker = ? OR ticker LIKE ?",
            (ticker, f"{clean_code}%"),
            one=True
        )
        entity_id = entity["id"] if entity else None
        if not entity_id:
            # If not in entity table, fallback to first matching or skip
            logger.warning(f"Entity not found in DB for ticker {ticker}")

        # Get latest stock price for upside calculation
        current_stock_price = None
        if entity_id:
            latest_price_row = query_db(
                "SELECT close FROM stock_price WHERE entity_id = ? ORDER BY date DESC LIMIT 1",
                (entity_id,),
                one=True
            )
            if latest_price_row and latest_price_row["close"]:
                current_stock_price = float(latest_price_row["close"])

        logger.info(f"Starting Naver report collection for {ticker} (Code: {clean_code})")

        # 2. Find research IDs for the target item code
        target_research_ids = set()
        scanned_pages = 0

        for page in range(1, max_scan_pages + 1):
            scanned_pages += 1
            url = NAVER_RESEARCH_LIST_URL.format(page=page)
            items = self._http_get_json(url)
            if not items or not isinstance(items, list):
                break

            for item in items:
                item_code = str(item.get("itemCode", "")).strip()
                if item_code == clean_code:
                    rid = item.get("researchId")
                    if rid:
                        target_research_ids.add(int(rid))

            # Respect rate limit
            time.sleep(self.delay_sec)
            
            # If we found at least 2 reports, we can proceed to fetch detail & discover older summaries
            if len(target_research_ids) >= 2:
                break

        # 3. Fetch details for each research ID and discover additional summaries
        processed_ids = set()
        collected_reports = []
        newly_saved_count = 0
        pdf_downloaded_count = 0

        # Queue of research IDs to process
        queue = list(target_research_ids)

        while queue and len(processed_ids) < max_reports:
            rid = queue.pop(0)
            if rid in processed_ids:
                continue
            processed_ids.add(rid)

            detail_url = NAVER_RESEARCH_DETAIL_URL.format(research_id=rid)
            detail_data = self._http_get_json(detail_url)
            time.sleep(self.delay_sec)

            if not detail_data or not isinstance(detail_data, dict):
                continue

            rc = detail_data.get("researchContent", {})
            if not rc:
                continue

            # Check if this report belongs to target ticker
            if str(rc.get("itemCode", "")).strip() != clean_code:
                continue

            # Queue additional historical summaries for the same stock if any
            for s in detail_data.get("researchSummaries", []):
                s_id = s.get("researchId")
                if s_id and int(s_id) not in processed_ids and int(s_id) not in queue:
                    queue.append(int(s_id))

            # Extract fields
            title = rc.get("title", "").strip()
            broker_name = rc.get("brokerName", "").strip() or "증권사미상"
            report_date = rc.get("writeDate", "").strip()
            opinion = rc.get("opinion", "").strip()  # e.g. 'Buy', '매수'
            attach_url = rc.get("attachUrl", "")

            # Parse target price
            goal_price_raw = rc.get("goalPrice")
            target_price = None
            if goal_price_raw:
                try:
                    target_price = float(str(goal_price_raw).replace(",", "").strip())
                    # Naver API sometimes returns won with zeros e.g. 3100000 or 310000
                    # Sanity check: if target price is unreasonably high (> 10,000,000 for regular stock), check priceAtWriteDate
                    price_at_write = rc.get("priceAtWriteDate")
                    if price_at_write:
                        paw = float(str(price_at_write).replace(",", "").strip())
                        if paw > 0 and target_price > paw * 15:
                            # Likely extra 0 in API (e.g. 3,100,000 vs 310,000)
                            target_price = target_price / 10.0
                except (ValueError, TypeError):
                    target_price = None

            # Price at report date
            price_at_report = None
            if rc.get("priceAtWriteDate"):
                try:
                    price_at_report = float(str(rc.get("priceAtWriteDate")).replace(",", "").strip())
                except (ValueError, TypeError):
                    pass

            # Calculate upside %
            upside_pct = None
            base_price = current_stock_price or price_at_report
            if target_price and base_price and base_price > 0:
                upside_pct = round(((target_price - base_price) / base_price) * 100.0, 2)

            # Standardize action type
            action_type = "Maintain"
            prev_goal_raw = rc.get("prevGoalPrice")
            if prev_goal_raw and target_price:
                try:
                    prev_goal = float(str(prev_goal_raw).replace(",", "").strip())
                    if target_price > prev_goal:
                        action_type = "Upgrade"
                    elif target_price < prev_goal:
                        action_type = "Downgrade"
                except Exception:
                    pass

            # Download PDF if requested
            local_pdf_rel_path = None
            if download_pdf and attach_url:
                safe_title = re.sub(r'[^\w\-_\. ]', '_', title)[:30].strip()
                pdf_filename = f"{report_date}_{broker_name}_{rid}_{safe_title}.pdf"
                local_full_path = KR_REPORTS_DIR / ticker / pdf_filename
                
                downloaded = self._download_pdf(attach_url, local_full_path)
                if downloaded:
                    pdf_downloaded_count += 1
                    local_pdf_rel_path = str(local_full_path.relative_to(KR_REPORTS_DIR.parent))

            # Summary snippet from content
            content_html = rc.get("content", "")
            summary_snippet = re.sub(r'<[^>]+>', ' ', content_html).strip()[:300] if content_html else None

            # Save to Database if entity exists
            if entity_id:
                try:
                    execute_db(
                        """
                        INSERT INTO analyst_report (
                            entity_id, ticker, source_type, broker_name, analyst_name,
                            report_date, title, rating, action_type, target_price,
                            current_price_at_report, upside_pct, currency, pdf_url,
                            local_pdf_path, summary_text
                        ) VALUES (?, ?, 'NAVER_RESEARCH', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'KRW', ?, ?, ?)
                        ON CONFLICT(entity_id, broker_name, report_date, title) DO UPDATE SET
                            target_price = excluded.target_price,
                            rating = excluded.rating,
                            upside_pct = excluded.upside_pct,
                            pdf_url = excluded.pdf_url,
                            local_pdf_path = COALESCE(excluded.local_pdf_path, analyst_report.local_pdf_path),
                            summary_text = COALESCE(excluded.summary_text, analyst_report.summary_text)
                        """,
                        (
                            entity_id, ticker, broker_name, None,
                            report_date, title, opinion, action_type, target_price,
                            price_at_report, upside_pct, attach_url,
                            local_pdf_rel_path, summary_snippet
                        )
                    )
                    newly_saved_count += 1
                except Exception as e:
                    logger.warning(f"Failed to save analyst_report {title}: {e}")

            collected_reports.append({
                "research_id": rid,
                "broker_name": broker_name,
                "report_date": report_date,
                "title": title,
                "rating": opinion,
                "action_type": action_type,
                "target_price": target_price,
                "upside_pct": upside_pct,
                "pdf_url": attach_url,
                "has_pdf": bool(local_pdf_rel_path)
            })

        logger.info(
            f"Naver report collection complete for {ticker}: "
            f"{len(collected_reports)} reports processed, {newly_saved_count} saved to DB, {pdf_downloaded_count} PDFs downloaded."
        )

        return {
            "ticker": ticker,
            "entity_id": entity_id,
            "scanned_pages": scanned_pages,
            "total_processed": len(collected_reports),
            "saved_count": newly_saved_count,
            "pdf_downloaded_count": pdf_downloaded_count,
            "reports": collected_reports
        }
