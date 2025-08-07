import logging
from typing import Dict
import yfinance as yf

logger = logging.getLogger("finbot.tools.fundamentals")


def get_basic_fundamentals(symbol: str) -> Dict[str, float]:
    info: Dict[str, float] = {}
    try:
        t = yf.Ticker(symbol)
        i = t.info or {}
        # Not all fields are available for Indian tickers; fill what we can.
        for key in [
            "trailingPE",
            "forwardPE",
            "priceToBook",
            "returnOnEquity",
            "profitMargins",
            "debtToEquity",
            "grossMargins",
            "operatingMargins",
        ]:
            val = i.get(key)
            if isinstance(val, (int, float)):
                info[key] = float(val)
        # Growth hints from financials if present
        try:
            fin = t.financials
            if fin is not None and not fin.empty:
                # using revenue growth proxy
                rev = fin.loc["Total Revenue"].dropna()
                if len(rev) >= 2:
                    growth = (rev.iloc[0] - rev.iloc[1]) / abs(rev.iloc[1])
                    info["revenue_growth_yoy"] = float(growth)
        except Exception:
            pass
    except Exception as e:
        logger.warning("Failed to load fundamentals for %s: %s", symbol, e)
    return info
