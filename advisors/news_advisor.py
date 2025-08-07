import logging
from schemas import NewsReport
from tools.news import fetch_news_report

logger = logging.getLogger("finbot.advisors.news")


def analyze_news(company_name: str) -> NewsReport:
    return fetch_news_report(company_name)
