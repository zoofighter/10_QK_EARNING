"""
Automated Background Scheduler for Analyst Reports & Global IB Targets.
Runs pre-market data collection tasks:
- 08:00 AM KST: Naver Securities KR Reports & PDF Downloads
- 21:00 PM KST: US Pre-Market Global IB Target Price Revisions & FinTwit Feeds
"""
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

KST = timezone(timedelta(hours=9))


class ReportScheduler:
    """Manages scheduled background jobs for intelligence feeds."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.last_kr_run: Optional[str] = None
        self.last_us_run: Optional[str] = None
        self.history_logs: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "ReportScheduler":
        with cls._lock:
            if cls._instance is None:
                cls._instance = ReportScheduler()
            return cls._instance

    def start(self):
        """Start the background scheduler thread."""
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            self._log("SCHEDULER_START", "정기 백그라운드 수집 스케줄러가 시작되었습니다. (08:00 KST / 21:00 KST)")

    def stop(self):
        """Stop the background scheduler thread."""
        with self._lock:
            if not self.is_running:
                return
            self.is_running = False
            self._stop_event.set()
            self._log("SCHEDULER_STOP", "정기 백그라운드 수집 스케줄러가 중지되었습니다.")

    def _log(self, event_type: str, message: str):
        now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        entry = {"time": now_str, "type": event_type, "message": message}
        self.history_logs.insert(0, entry)
        if len(self.history_logs) > 50:
            self.history_logs = self.history_logs[:50]
        print(f"[Scheduler] [{now_str}] {event_type}: {message}")

    def _run_loop(self):
        """Main check loop running once per 30 seconds."""
        last_checked_minute = -1

        while not self._stop_event.is_set():
            now_kst = datetime.now(KST)
            current_minute = now_kst.minute
            current_hour = now_kst.hour

            if current_minute != last_checked_minute:
                last_checked_minute = current_minute

                # 1. 08:00 KST - KR Morning Naver Research & PDFs
                if current_hour == 8 and current_minute == 0:
                    self.execute_kr_morning_job()

                # 2. 21:00 KST - US Pre-market Global IB & FinTwit
                elif current_hour == 21 and current_minute == 0:
                    self.execute_us_evening_job()

            # Sleep 15 seconds
            self._stop_event.wait(15)

    def execute_kr_morning_job(self) -> Dict[str, Any]:
        """Collect latest Naver reports and PDFs for KR semiconductor leaders."""
        from app.services.naver_report_collector import NaverReportCollector
        from app.services.pdf_indexer import PdfReportIndexer

        self._log("KR_MORNING_RUN", "오전 08:00 국내 장전 네이버 증권 리포트 및 원문 PDF 수집 시작")
        results = {}
        kr_tickers = ["000660.KS", "005930.KS"]

        for ticker in kr_tickers:
            try:
                collector = NaverReportCollector(ticker=ticker)
                reports = collector.collect_and_save(pages=1, download_pdfs=True)
                results[ticker] = len(reports)
            except Exception as e:
                results[ticker] = f"error: {e}"

        # Trigger auto-indexing of newly downloaded PDFs
        try:
            PdfReportIndexer.index_all_reports_background()
        except Exception as e:
            print(f"[Scheduler] Indexing error: {e}")

        now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        self.last_kr_run = now_str
        self._log("KR_MORNING_DONE", f"국내 리포트 수집 완료: {results}")
        return {"status": "success", "results": results, "run_at": now_str}

    def execute_us_evening_job(self) -> Dict[str, Any]:
        """Collect latest Global IB targets and FinTwit feeds for US tech giants."""
        from app.services.ib_target_collector import IbTargetCollector
        from app.services.fintwit_qa_agent import FinTwitQAAgent

        self._log("US_EVENING_RUN", "오후 21:00 미국 장전 글로벌 IB 목표가 리비전 및 FinTwit 속보 수집 시작")
        results = {}
        us_tickers = ["NVDA", "TSM", "MSFT", "AAPL", "AVGO", "AMD"]

        ib_collector = IbTargetCollector()
        fintwit_agent = FinTwitQAAgent()

        for ticker in us_tickers:
            try:
                res = ib_collector.collect_and_save_all(ticker)
                fintwit_posts = fintwit_agent.fetch_live_fintwit_stream(ticker, limit=10)
                results[ticker] = {
                    "actions": res.get("actions_saved", 0),
                    "fintwit": len(fintwit_posts)
                }
            except Exception as e:
                results[ticker] = f"error: {e}"

        now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        self.last_us_run = now_str
        self._log("US_EVENING_DONE", f"글로벌 IB & FinTwit 수집 완료: {results}")
        return {"status": "success", "results": results, "run_at": now_str}

    def run_now(self, job_type: str = "ALL") -> Dict[str, Any]:
        """Trigger immediate execution of jobs."""
        out = {}
        if job_type in ("KR_MORNING", "ALL"):
            out["kr_morning"] = self.execute_kr_morning_job()
        if job_type in ("US_EVENING", "ALL"):
            out["us_evening"] = self.execute_us_evening_job()
        return out

    def get_status(self) -> Dict[str, Any]:
        """Return scheduler status and execution history."""
        now_kst = datetime.now(KST)
        next_kr = now_kst.replace(hour=8, minute=0, second=0, microsecond=0)
        if now_kst >= next_kr:
            next_kr += timedelta(days=1)

        next_us = now_kst.replace(hour=21, minute=0, second=0, microsecond=0)
        if now_kst >= next_us:
            next_us += timedelta(days=1)

        return {
            "is_running": self.is_running,
            "current_time_kst": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
            "next_kr_morning_run": next_kr.strftime("%Y-%m-%d %H:%M:%S"),
            "next_us_evening_run": next_us.strftime("%Y-%m-%d %H:%M:%S"),
            "last_kr_run": self.last_kr_run,
            "last_us_run": self.last_us_run,
            "recent_logs": self.history_logs[:10]
        }
