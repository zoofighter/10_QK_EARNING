import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "qk_earning.db"
FILINGS_DIR = DATA_DIR / "filings"
REPORTS_DIR = DATA_DIR / "reports"
KR_REPORTS_DIR = REPORTS_DIR / "kr"
GLOBAL_REPORTS_DIR = REPORTS_DIR / "global"

# SEC EDGAR Requirements
# SEC requires a user-agent in the format: 'Sample Company Name AdminContact@<sample company domain>.com'
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "QKEarningResearchApp researcher@qkearning.io")
SEC_RATE_LIMIT_DELAY = 0.2  # seconds between requests to guarantee < 10 req/sec

# Korea Customs Service (관세청) Open API
CUSTOMS_API_KEY = os.environ.get(
    "CUSTOMS_API_KEY",
    "3fa055dbb8ba9d142fdc07528a42b372741932fc8f7bc9fed33b8be8bdb7a55a"
)
CUSTOMS_API_URL = os.environ.get(
    "CUSTOMS_API_URL",
    "http://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"
)

# App Settings
PORT = int(os.environ.get("PORT", 5001))
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
SECRET_KEY = os.environ.get("SECRET_KEY", "qk-earning-secret-key-ai-value-chain-2026")

# Global Investment Bank (IB) Tier Structure
GLOBAL_IB_TIERS = {
    "TIER_1": [
        "Goldman Sachs",
        "Citigroup",
        "JPMorgan",
        "Morgan Stanley",
        "Bank of America"
    ],
    "TIER_2": [
        "Nomura",           # 일본/아시아 최대 IB & 글로벌 반도체 분석
        "Barclays",
        "UBS",
        "Bernstein",
        "Jefferies",
        "Wells Fargo"
    ],
    "TIER_3": [
        "Mizuho",
        "Evercore ISI",
        "Piper Sandler",
        "Rosenblatt",
        "Needham",
        "Stifel",
        "Deutsche Bank",
        "HSBC",
        "Macquarie",
        "Cantor Fitzgerald"
    ]
}

# Alias mapping to canonical names
GLOBAL_IB_ALIASES = {
    "Goldman Sachs": ["Goldman Sachs", "Goldman", "GS"],
    "Citigroup": ["Citigroup", "Citi", "Citi Research"],
    "JPMorgan": ["JPMorgan", "J.P. Morgan", "JP Morgan", "JPMorgan Chase"],
    "Morgan Stanley": ["Morgan Stanley", "MS"],
    "Bank of America": ["BofA Securities", "Bank of America", "Merrill Lynch", "BofA"],
    "Nomura": ["Nomura", "Nomura Securities", "Nomura Instinet"],
    "Barclays": ["Barclays", "Barclays Capital"],
    "UBS": ["UBS", "UBS Securities"],
    "Bernstein": ["Bernstein", "Sanford C. Bernstein", "AllianceBernstein"],
    "Jefferies": ["Jefferies", "Jefferies LLC"],
    "Wells Fargo": ["Wells Fargo", "Wells Fargo Securities"],
    "Mizuho": ["Mizuho", "Mizuho Securities"],
    "Evercore ISI": ["Evercore ISI", "Evercore"],
    "Piper Sandler": ["Piper Sandler", "Piper Jaffray"],
    "Rosenblatt": ["Rosenblatt", "Rosenblatt Securities"],
    "Needham": ["Needham", "Needham & Company"],
    "Stifel": ["Stifel", "Stifel Nicolaus"],
    "Deutsche Bank": ["Deutsche Bank", "DB"],
    "HSBC": ["HSBC", "HSBC Securities"],
    "Macquarie": ["Macquarie", "Macquarie Research"],
    "Cantor Fitzgerald": ["Cantor Fitzgerald", "Cantor"]
}
