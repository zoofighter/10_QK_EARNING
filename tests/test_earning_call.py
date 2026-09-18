import unittest
from app.services.transcript_collector import TranscriptCollector

class TestTranscriptCollector(unittest.TestCase):

    def test_seed_and_query_transcripts(self):
        collector = TranscriptCollector()
        cnt = collector.seed_sample_transcripts()
        self.assertGreaterEqual(cnt, 4)

        calls = collector.get_transcripts_list(limit=10)
        self.assertGreaterEqual(len(calls), 4)

        nvda_call = collector.get_transcript_by_quarter("NVDA", "2026", "Q2")
        self.assertIsNotNone(nvda_call)
        self.assertEqual(nvda_call["ticker"], "NVDA")
        self.assertIn("sections", nvda_call)
        self.assertTrue(nvda_call["sections"]["has_qa"])
        self.assertIn("Jensen Huang", nvda_call["transcript_text"])

    def test_save_transcript(self):
        collector = TranscriptCollector()
        res = collector.save_transcript(
            ticker="NVDA",
            fiscal_year="2025",
            fiscal_quarter="Q4",
            call_date="2025-02-26",
            transcript_text="Test prepared remarks.\nQUESTION AND ANSWER SESSION\nQ: Question?\nA: Answer."
        )
        self.assertEqual(res["status"], "success")

        detail = collector.get_transcript_by_quarter("NVDA", "2025", "Q4")
        self.assertIsNotNone(detail)
        self.assertTrue(detail["sections"]["has_qa"])

if __name__ == "__main__":
    unittest.main()
