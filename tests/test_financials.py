import unittest
from app.services.financial_service import FinancialService
from app.services.filing_section_extractor import FilingSectionExtractor

class TestFinancialsAndSectionExtractor(unittest.TestCase):

    def test_seed_and_get_financials(self):
        service = FinancialService()
        cnt = service.seed_historical_financials_from_2020()
        self.assertGreater(cnt, 0)

        # Query NVDA
        res = service.get_quarterly_financials("NVDA", start_year=2020)
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["count"], 15)  # At least 15+ quarters from 2020 to 2026

        # Check most recent quarter has high revenue and datacenter ratio
        latest = res["series"][0]
        self.assertIn("period", latest)
        self.assertEqual(latest["period"], "2026-Q2")
        self.assertIn("report_date", latest)
        self.assertEqual(latest["report_date"], "2026-08-26")
        self.assertGreater(latest["revenue"], 30000)
        self.assertGreater(latest["segment_datacenter"], 25000)
        self.assertIsNotNone(latest["op_margin_pct"])

        # All quarters should have a valid report_date (실적발표일)
        for q in res["series"]:
            self.assertIsNotNone(q["report_date"])
            self.assertNotEqual(q["report_date"], "")

    def test_section_extractor(self):
        sample_text = """
        Table of Contents
        Item 1. Financial Statements
        Item 2. Management's Discussion and Analysis of Financial Condition
        Item 1A. Risk Factors

        PART I. FINANCIAL INFORMATION
        Item 1. Financial Statements
        Consolidated Balance Sheets and Statements of Operations.
        Total Revenue for the quarter was $30,040 million.

        Item 2. Management's Discussion and Analysis of Financial Condition and Results of Operations
        Our Data Center revenue increased by 154% due to strong demand for our Hopper and Blackwell architectures.
        Revenue for the next quarter is expected to be $32.5 billion.

        PART II. OTHER INFORMATION
        Item 1A. Risk Factors
        We face significant risks related to global semiconductor supply chains and packaging capacity.
        """

        sections = FilingSectionExtractor.extract_sections(sample_text, form_type="10-Q")
        self.assertIn("mda", sections)
        self.assertIn("financial_statements", sections)
        self.assertIn("risk_factors", sections)

        mda_text = sections["mda"]["text"]
        self.assertIn("Hopper and Blackwell", mda_text)

        risk_text = sections["risk_factors"]["text"]
        self.assertIn("supply chains and packaging capacity", risk_text)

    def test_avgo_financials_and_dates(self):
        service = FinancialService()
        res = service.get_quarterly_financials("AVGO")
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["count"], 0)

        # Check latest quarters for AVGO (October fiscal year-end)
        periods = {s["period"]: s for s in res["series"]}
        self.assertIn("2026-Q3", periods)
        self.assertEqual(periods["2026-Q3"]["report_date"], "2026-09-10")
        self.assertEqual(periods["2026-Q3"]["filing_type"], "10-Q")

        self.assertIn("2026-Q2", periods)
        self.assertEqual(periods["2026-Q2"]["report_date"], "2026-06-09")
        self.assertEqual(periods["2026-Q2"]["filing_type"], "10-Q")

        self.assertIn("2025-Q4", periods)
        self.assertEqual(periods["2025-Q4"]["report_date"], "2025-12-18")
        self.assertEqual(periods["2025-Q4"]["filing_type"], "10-K")

    def test_continuous_quarters_and_apple_fiscal_calendar(self):
        service = FinancialService()

        # 1. AAPL Check: 27 continuous quarters from 2020-Q1 to 2026-Q3
        aapl = service.get_quarterly_financials("AAPL")
        self.assertEqual(aapl["status"], "success")
        self.assertGreaterEqual(aapl["count"], 26)
        aapl_periods = [s["period"] for s in aapl["series"]]
        # Ensure consecutive quarters exist without gaps
        self.assertEqual(aapl_periods[0], "2026-Q3")
        self.assertEqual(aapl_periods[1], "2026-Q2")
        self.assertEqual(aapl_periods[2], "2026-Q1")
        self.assertEqual(aapl_periods[3], "2025-Q4")
        self.assertEqual(aapl_periods[4], "2025-Q3")
        # Apple Q1 (Holiday iPhone quarter) has peak revenue
        q1_metric = next(s for s in aapl["series"] if s["period"] == "2026-Q1")
        q2_metric = next(s for s in aapl["series"] if s["period"] == "2026-Q2")
        self.assertGreater(q1_metric["revenue"], q2_metric["revenue"])

        # 2. MSFT Check: 28 continuous quarters from 2020-Q1 to 2026-Q4
        msft = service.get_quarterly_financials("MSFT")
        self.assertEqual(msft["status"], "success")
        self.assertGreaterEqual(msft["count"], 26)
        msft_periods = [s["period"] for s in msft["series"]]
        self.assertEqual(msft_periods[0], "2026-Q4")
        self.assertEqual(msft_periods[1], "2026-Q3")
        self.assertEqual(msft_periods[2], "2026-Q2")
        self.assertEqual(msft_periods[3], "2026-Q1")

        # 3. GOOGL Check: 26 continuous quarters from 2020-Q1 to 2026-Q2
        googl = service.get_quarterly_financials("GOOGL")
        self.assertEqual(googl["status"], "success")
        self.assertGreaterEqual(googl["count"], 26)
        googl_periods = [s["period"] for s in googl["series"]]
        self.assertEqual(googl_periods[0], "2026-Q2")
        self.assertEqual(googl_periods[1], "2026-Q1")
        self.assertEqual(googl_periods[2], "2025-Q4")
        self.assertEqual(googl_periods[3], "2025-Q3")



if __name__ == "__main__":
    unittest.main()
