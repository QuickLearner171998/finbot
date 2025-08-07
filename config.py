import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REASONING_MODEL = os.getenv("OPENAI_REASONING_MODEL", "gpt-5")
SUMMARY_MODEL = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4.1")
USE_OPENAI_WEB_SEARCH = os.getenv("USE_OPENAI_WEB_SEARCH", "true").lower() == "true"
DEFAULT_HORIZON_YEARS = float(os.getenv("DEFAULT_HORIZON_YEARS", "2.0"))
DEFAULT_RISK_LEVEL = os.getenv("DEFAULT_RISK_LEVEL", "medium")

assert OPENAI_API_KEY, "OPENAI_API_KEY missing. Add it to .env or environment."
