import logging
from typing import Optional, Tuple
import pandas as pd
import yfinance as yf

logger = logging.getLogger("finbot.tools.prices")


def fetch_history(symbol: str, period: str = "2y") -> Optional[pd.DataFrame]:
    try:
        logger.debug("Prices: fetching history for %s period=%s", symbol, period)
        df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        if df is not None and len(df) > 0:
            logger.debug("Prices: rows=%d cols=%d for %s", len(df), len(df.columns), symbol)
            return df
    except Exception as e:
        logger.warning("Failed to fetch history for %s: %s", symbol, e)
    return None


def compute_long_term_indicators(df: pd.DataFrame) -> Tuple[float, float, float, float]:
    close = df["Close"].dropna()
    ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else float("nan")
    ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else float("nan")
    last = float(close.iloc[-1])
    high_52w = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
    drawdown_from_high = (last - high_52w) / high_52w if high_52w else float("nan")
    logger.debug(
        "Prices: indicators computed last=%.2f ma50=%.2f ma200=%.2f dd=%.3f",
        last,
        ma50,
        ma200,
        drawdown_from_high,
    )
    return last, ma50, ma200, drawdown_from_high
