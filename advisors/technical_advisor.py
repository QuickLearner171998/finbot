import logging
from schemas import TechnicalReport
from tools.prices import fetch_history, compute_long_term_indicators

logger = logging.getLogger("finbot.advisors.technical")


def analyze_technical(symbol: str) -> TechnicalReport:
    logger.debug("Technical: fetching history for %s", symbol)
    df = fetch_history(symbol, period="2y")
    if df is None or len(df) < 50:
        logger.debug("Technical: insufficient data for %s (rows=%s)", symbol, 0 if df is None else len(df))
        return TechnicalReport(metrics={}, trend="insufficient_data", pros=["Insufficient price history"], cons=[])
    last, ma50, ma200, dd = compute_long_term_indicators(df)
    metrics = {"last": last, "ma50": ma50, "ma200": ma200, "drawdown_from_52w": dd}
    pros = []
    cons = []
    trend = "neutral"
    if last > ma200 and last > ma50:
        trend = "uptrend"
        pros.append("Price above 50/200 DMA")
    elif last < ma200 and last < ma50:
        trend = "downtrend"
        cons.append("Price below 50/200 DMA")
    else:
        trend = "mixed"
    if dd < -0.15:
        pros.append("Attractive discount vs 52W high")
    report = TechnicalReport(metrics=metrics, trend=trend, pros=pros, cons=cons)
    logger.debug("Technical: trend=%s last=%.2f ma50=%.2f ma200=%.2f dd=%.3f", trend, last, ma50, ma200, dd)
    return report
