import unittest
from app.services.consensus_service import ConsensusService

class TestConsensusService(unittest.TestCase):
    def test_beat_miss_revenue(self):
        # Revenue: threshold is 1.0%
        surprise, status = ConsensusService.calculate_beat_miss("revenue", 1000.0, 1020.0)
        self.assertEqual(surprise, 2.0)
        self.assertEqual(status, "BEAT")

        surprise, status = ConsensusService.calculate_beat_miss("revenue", 1000.0, 980.0)
        self.assertEqual(surprise, -2.0)
        self.assertEqual(status, "MISS")

        surprise, status = ConsensusService.calculate_beat_miss("revenue", 1000.0, 1005.0)
        self.assertEqual(surprise, 0.5)
        self.assertEqual(status, "INLINE")

    def test_beat_miss_eps(self):
        # EPS: threshold is 2.0%
        surprise, status = ConsensusService.calculate_beat_miss("eps", 1.00, 1.03)
        self.assertEqual(surprise, 3.0)
        self.assertEqual(status, "BEAT")

        surprise, status = ConsensusService.calculate_beat_miss("eps", 1.00, 0.97)
        self.assertEqual(surprise, -3.0)
        self.assertEqual(status, "MISS")

        surprise, status = ConsensusService.calculate_beat_miss("eps", 1.00, 1.01)
        self.assertEqual(surprise, 1.0)
        self.assertEqual(status, "INLINE")

    def test_consensus_service_seed(self):
        service = ConsensusService()
        count = service.seed_sample_consensus()
        self.assertGreater(count, 0)

        matrix = service.get_matrix_view()
        self.assertIn("quarters", matrix)
        self.assertGreater(len(matrix["companies"]), 0)

        tickers = [c["ticker"] for c in matrix["companies"]]
        self.assertIn("NVDA", tickers)

if __name__ == "__main__":
    unittest.main()
