import logging
from typing import List
from duckduckgo_search import DDGS

from llm import llm
from schemas import NewsItem, NewsReport
from prompts import NEWS_SUMMARY_PROMPT_TEMPLATE, NEWS_SUMMARY_SYSTEM_MESSAGE

logger = logging.getLogger("finbot.tools.news")


def search_news_ddg(query: str, max_results: int = 10) -> List[NewsItem]:
    items: List[NewsItem] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news(keywords=query, region="in-en", max_results=max_results):
                items.append(
                    NewsItem(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        published_at=r.get("date"),
                        source=r.get("source"),
                        snippet=r.get("body"),
                    )
                )
    except Exception as e:
        logger.warning("DDG news search failed: %s", e)
    return items


def fetch_news_report(company: str) -> NewsReport:
    # Try OpenAI web search summarization first
    logger.debug("NewsTool: attempting web_search_summary for %s", company)
    summary = llm.web_search_summary(f"{company} India latest news earnings regulation risks opportunities")
    items: List[NewsItem] = []

    if not summary:
        # Fallback to DDG search and LLM summarization of snippets
        logger.debug("NewsTool: web summary unavailable; falling back to DDG for %s", company)
        items = search_news_ddg(f"{company} latest stock news")
        snippets = "\n".join([f"- {n.title}: {n.snippet or ''} ({n.url})" for n in items[:10]])
        prompt = NEWS_SUMMARY_PROMPT_TEMPLATE.format(
            snippets=snippets
        )
        summary = llm.summarize(prompt, system=NEWS_SUMMARY_SYSTEM_MESSAGE)

    if not items:
        # If OpenAI web summary provided links embedded, we still return an empty items list; summary holds the value
        items = []
    logger.debug("NewsTool: items=%d summary_len=%d", len(items), len(summary or ""))
    return NewsReport(items=items, summary=summary or "No recent news found.")
