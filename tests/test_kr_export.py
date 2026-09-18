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

if __name__ == "__main__":
    unittest.main()
