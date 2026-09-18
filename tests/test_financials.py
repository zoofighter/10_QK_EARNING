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
        self.assertGreater(latest["revenue"], 30000)
        self.assertGreater(latest["segment_datacenter"], 25000)
        self.assertIsNotNone(latest["op_margin_pct"])

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

if __name__ == "__main__":
    unittest.main()
