import logging
from schemas import NewsReport
from tools.news import fetch_news_report

logger = logging.getLogger("finbot.advisors.news")


def analyze_news(company_name: str) -> NewsReport:
    logger.debug("News: fetching for %s", company_name)
    report = fetch_news_report(company_name)
    logger.debug("News: items=%d summary_len=%d", len(report.items or []), len(report.summary or ""))
    return report
