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
        self.last_price_run: Optional[str] = None
        self.last_gpu_run: Optional[str] = None
        self.last_customs_run: Optional[str] = None
        self.last_filings_run: Optional[str] = None
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
            self._log("SCHEDULER_START", "정기 백그라운드 자동 수집 스케줄러가 활성화되었습니다. (주가/리포트/GPU/관세청/공시/IB)")

    def stop(self):
        """Stop the background scheduler thread."""
        with self._lock:
            if not self.is_running:
                return
            self.is_running = False
            self._stop_event.set()
            self._log("SCHEDULER_STOP", "정기 백그라운드 자동 수집 스케줄러가 일시 중지되었습니다.")

    def _log(self, event_type: str, message: str):
        now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        entry = {"time": now_str, "type": event_type, "message": message}
        self.history_logs.insert(0, entry)
        if len(self.history_logs) > 60:
            self.history_logs = self.history_logs[:60]
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

                # 1. 06:30 KST - US Post-Market 34 Ticker Daily Price Sync (yfinance)
                if current_hour == 6 and current_minute == 30:
                    self.execute_price_sync_job()

                # 2. 08:00 KST - KR Morning Naver Research & PDFs
                elif current_hour == 8 and current_minute == 0:
                    self.execute_kr_morning_job()

                # 3. 08:30 KST - AI Accelerator GPU Rental Spot Price Sync
                elif current_hour == 8 and current_minute == 30:
                    self.execute_gpu_sync_job()

                # 4. 09:30 KST (1st, 11th, 21st) - Korea Customs 10-Day Export Stats
                elif current_hour == 9 and current_minute == 30 and now_kst.day in (1, 11, 21):
                    self.execute_customs_10day_job()

                # 5. 18:00 KST - SEC EDGAR Top AI Hyperscalers Filings Check
                elif current_hour == 18 and current_minute == 0:
                    self.execute_edgar_filings_job()

                # 6. 21:00 KST - US Pre-market Global IB & FinTwit
                elif current_hour == 21 and current_minute == 0:
                    self.execute_us_evening_job()

            # Sleep 15 seconds
            self._stop_event.wait(15)

    def execute_price_sync_job(self) -> Dict[str, Any]:
        """Collect latest stock prices for all 34 companies via yfinance."""
        from app.services.price_collector import PriceCollector
        self._log("PRICE_SYNC_RUN", "오전 06:30 미국 증시 마감 후 전체 기업 주가(yfinance) 자동 동기화 시작")
        try:
            collector = PriceCollector()
            res = collector.collect_all_entities(period="1mo")
            now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
            self.last_price_run = now_str
            self._log("PRICE_SYNC_DONE", f"전체 주가 동기화 완료: {len(res)}개 기업 최신 시세 반영")
            return {"status": "success", "count": len(res), "run_at": now_str}
        except Exception as e:
            self._log("PRICE_SYNC_ERR", f"주가 동기화 실패: {e}")
            return {"status": "error", "message": str(e)}

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

    def execute_gpu_sync_job(self) -> Dict[str, Any]:
        """Synchronize latest GPU cloud rental spot prices (H100, H200, B200, A100)."""
        from app.services.gpu_price_collector import GpuPriceCollector
        self._log("GPU_SYNC_RUN", "오전 08:30 AI 가속기 GPU 클라우드 렌탈 스팟 가격 자동 동기화 시작")
        try:
            collector = GpuPriceCollector()
            res = collector.sync_latest_spot_prices()
            now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
            self.last_gpu_run = now_str
            self._log("GPU_SYNC_DONE", f"GPU 렌탈 스팟 동기화 완료: {res.get('sync_date')} 기준 {res.get('count')}개 모델")
            return {"status": "success", "data": res, "run_at": now_str}
        except Exception as e:
            self._log("GPU_SYNC_ERR", f"GPU 시세 동기화 실패: {e}")
            return {"status": "error", "message": str(e)}

    def execute_customs_10day_job(self) -> Dict[str, Any]:
        """Collect Korea Customs Service 10-day semiconductor export statistics."""
        from app.services.kr_export_collector import KrExportCollector
        self._log("CUSTOMS_SYNC_RUN", "오전 09:30 관세청 10일 주기 반도체 수출 속보치 자동 수집 시작")
        try:
            collector = KrExportCollector()
            now_kst = datetime.now(KST)
            res = collector.fetch_10day_customs_api(year=now_kst.year, month=now_kst.month)
            now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
            self.last_customs_run = now_str
            self._log("CUSTOMS_SYNC_DONE", f"관세청 10일 수출 속보치 수집 완료: {res.get('status')}")
            return {"status": "success", "data": res, "run_at": now_str}
        except Exception as e:
            self._log("CUSTOMS_SYNC_ERR", f"관세청 통계 수집 실패: {e}")
            return {"status": "error", "message": str(e)}

    def execute_edgar_filings_job(self) -> Dict[str, Any]:
        """Batch collect latest SEC Filings for major tech hyperscalers."""
        from app.services.edgar_collector import EdgarCollector
        self._log("EDGAR_SYNC_RUN", "오후 18:00 SEC EDGAR 주요 AI 하이퍼스케일러 신규 공시 배치 수집 시작")
        try:
            collector = EdgarCollector()
            sample_tickers = ["NVDA", "GOOGL", "MSFT", "AMZN", "META", "AMD", "TSM", "MU"]
            results = []
            for t in sample_tickers:
                try:
                    r = collector.collect_for_entity(t, form_types=["10-Q", "10-K", "8-K"], limit=3, download_docs=True)
                    results.append({"ticker": t, "count": r.get("filings_saved", 0)})
                except Exception as e:
                    results.append({"ticker": t, "error": str(e)})

            now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
            self.last_filings_run = now_str
            self._log("EDGAR_SYNC_DONE", f"SEC 공시 배치 수집 완료: {len(results)}개 기업")
            return {"status": "success", "results": results, "run_at": now_str}
        except Exception as e:
            self._log("EDGAR_SYNC_ERR", f"SEC 공시 수집 실패: {e}")
            return {"status": "error", "message": str(e)}

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
        if job_type in ("PRICE", "ALL"):
            out["price_sync"] = self.execute_price_sync_job()
        if job_type in ("KR_MORNING", "ALL"):
            out["kr_morning"] = self.execute_kr_morning_job()
        if job_type in ("GPU", "ALL"):
            out["gpu_sync"] = self.execute_gpu_sync_job()
        if job_type in ("CUSTOMS", "ALL"):
            out["customs_10day"] = self.execute_customs_10day_job()
        if job_type in ("EDGAR", "ALL"):
            out["edgar_filings"] = self.execute_edgar_filings_job()
        if job_type in ("US_EVENING", "ALL"):
            out["us_evening"] = self.execute_us_evening_job()
        return out

    def get_status(self) -> Dict[str, Any]:
        """Return scheduler status, full schedule, and execution history."""
        now_kst = datetime.now(KST)

        def calc_next(hour: int, minute: int) -> str:
            target = now_kst.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if now_kst >= target:
                target += timedelta(days=1)
            return target.strftime("%Y-%m-%d %H:%M:%S")

        schedule_items = [
            {
                "id": "price_sync",
                "time": "06:30 KST (매일)",
                "name": "미국 증시 34개사 일일 주가(yfinance) 동기화",
                "next_run": calc_next(6, 30),
                "last_run": self.last_price_run or "대기 중"
            },
            {
                "id": "kr_morning",
                "time": "08:00 KST (매일)",
                "name": "국내 증권사 네이버 리포트 & 원문 PDF 수집/색인",
                "next_run": calc_next(8, 0),
                "last_run": self.last_kr_run or "대기 중"
            },
            {
                "id": "gpu_sync",
                "time": "08:30 KST (매일)",
                "name": "AI 가속기 GPU 클라우드 렌탈 스팟 가격 동기화",
                "next_run": calc_next(8, 30),
                "last_run": self.last_gpu_run or "대기 중"
            },
            {
                "id": "customs_10day",
                "time": "09:30 KST (매월 1/11/21일)",
                "name": "관세청 10일 주기 반도체 수출입 속보치 자동 수집",
                "next_run": "매월 1일/11일/21일 09:30 KST",
                "last_run": self.last_customs_run or "대기 중"
            },
            {
                "id": "edgar_filings",
                "time": "18:00 KST (매일)",
                "name": "SEC EDGAR 주요 AI 하이퍼스케일러 신규 공시 배치 체크",
                "next_run": calc_next(18, 0),
                "last_run": self.last_filings_run or "대기 중"
            },
            {
                "id": "us_evening",
                "time": "21:00 KST (매일)",
                "name": "글로벌 IB 목표주가 리비전 & FinTwit 속보 피드 수집",
                "next_run": calc_next(21, 0),
                "last_run": self.last_us_run or "대기 중"
            }
        ]

        return {
            "is_running": self.is_running,
            "current_time_kst": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
            "next_kr_morning_run": calc_next(8, 0),
            "next_us_evening_run": calc_next(21, 0),
            "last_kr_run": self.last_kr_run,
            "last_us_run": self.last_us_run,
            "last_price_run": self.last_price_run,
            "last_gpu_run": self.last_gpu_run,
            "last_customs_run": self.last_customs_run,
            "last_filings_run": self.last_filings_run,
            "schedules": schedule_items,
            "recent_logs": self.history_logs[:15]
        }

