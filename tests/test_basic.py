import unittest
import json
from app import create_app
from app.models.database import query_db

class TestQKEarningPhase1(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_database_entities(self):
        """Verify all 34 entities are seeded across 7 layers."""
        cnt = query_db("SELECT COUNT(*) as count FROM entity", one=True)["count"]
        self.assertEqual(cnt, 34)

    def test_database_layers(self):
        """Verify 7 layers are seeded."""
        cnt = query_db("SELECT COUNT(*) as count FROM layer", one=True)["count"]
        self.assertEqual(cnt, 7)

    def test_api_stats(self):
        """Verify /api/stats endpoint response."""
        res = self.client.get("/api/stats")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["company_count"], 34)

    def test_api_entities_filter(self):
        """Verify filtering by layer."""
        res = self.client.get("/api/entities?layer=L3_COMPUTE")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["count"], 5)
        tickers = [e["ticker"] for e in data["data"]]
        self.assertIn("NVDA", tickers)
        self.assertIn("AMD", tickers)

    def test_api_calendar(self):
        """Verify calendar endpoint with D-Day calculation."""
        res = self.client.get("/api/calendar")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertGreater(data["count"], 0)
        self.assertIn("d_day", data["data"][0])

if __name__ == "__main__":
    unittest.main()
