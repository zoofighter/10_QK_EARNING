import unittest
from app.services.kr_export_collector import KoreaExportCollector

class TestKoreaExportCollector(unittest.TestCase):
    def test_kr_export_seeding_and_history(self):
        collector = KoreaExportCollector()
        cnt = collector.seed_sample_export_data()
        self.assertGreater(cnt, 0)

        history = collector.get_export_history(indicator_type="KR_SEMI_EXPORT_AMT", limit=10)
        self.assertGreater(len(history), 0)
        self.assertGreater(history[-1]["value"], 0)

        # Test individual 10day report add
        res = collector.add_10day_report(
            year=2026,
            month=9,
            period="중순",
            semi_export_amt=4250,
            semi_yoy_pct=44.1,
            total_export_amt=18900
        )
        self.assertEqual(res["status"], "success")

    def test_fetch_customs_api(self):
        collector = KoreaExportCollector()
        res = collector.fetch_customs_api(start_year=2026, end_year=2026)
        if res.get("status") == "success":
            self.assertGreater(res["synced_count"], 0)
            self.assertIn("latest", res)
            history = collector.get_export_history(indicator_type="KR_SEMI_EXPORT_MONTHLY_AMT", limit=5)
            self.assertGreater(len(history), 0)

    def test_fetch_10day_customs_api(self):
        collector = KoreaExportCollector()
        res = collector.fetch_10day_customs_api(strt_yymm="202608", end_yymm="202609")
        if res.get("status") == "success":
            self.assertGreater(res["count"], 0)
            self.assertIn("latest", res)
            history = collector.get_export_history(indicator_type="KR_TOTAL_EXPORT_AMT", limit=5)
            self.assertGreater(len(history), 0)

if __name__ == "__main__":
    unittest.main()
