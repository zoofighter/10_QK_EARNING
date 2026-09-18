import unittest
from app.services.memory_spot_collector import MemorySpotCollector, MEMORY_SPOT_TYPES

class TestMemorySpotCollector(unittest.TestCase):
    def test_add_and_get_spot_entry(self):
        collector = MemorySpotCollector()
        res = collector.add_spot_entry(
            indicator_type="SPOT_DRAM_DDR5_16GB",
            date_str="2026-09-18",
            value=5.90,
            note="Test Spot Price"
        )
        self.assertEqual(res["status"], "success")

        history = collector.get_spot_history("SPOT_DRAM_DDR5_16GB", limit=50)
        self.assertGreater(len(history), 0)
        self.assertEqual(history[-1]["value"], 5.90)

    def test_seed_and_summary(self):
        collector = MemorySpotCollector()
        cnt = collector.seed_sample_spot_data()
        self.assertGreater(cnt, 0)

        summary = collector.get_latest_summary()
        self.assertIn("SPOT_DRAM_DDR5_16GB", summary)
        self.assertIn("SPOT_DRAM_DDR4_8GB", summary)
        self.assertIn("SPOT_NAND_TLC_512GB", summary)
        self.assertIn("INDEX_DXI", summary)

        ddr5 = summary["SPOT_DRAM_DDR5_16GB"]
        self.assertIsNotNone(ddr5["latest_price"])
        self.assertGreater(ddr5["latest_price"], 0)

if __name__ == "__main__":
    unittest.main()
