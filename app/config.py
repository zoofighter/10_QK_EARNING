import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "qk_earning.db"
FILINGS_DIR = DATA_DIR / "filings"

# SEC EDGAR Requirements
# SEC requires a user-agent in the format: 'Sample Company Name AdminContact@<sample company domain>.com'
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "QKEarningResearchApp researcher@qkearning.io")
SEC_RATE_LIMIT_DELAY = 0.2  # seconds between requests to guarantee < 10 req/sec

# App Settings
PORT = int(os.environ.get("PORT", 5001))
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
SECRET_KEY = os.environ.get("SECRET_KEY", "qk-earning-secret-key-ai-value-chain-2026")
