import logging
from typing import List
from duckduckgo_search import DDGS

from llm import llm
from schemas import NewsItem, NewsReport

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
    summary = llm.web_search_summary(f"{company} India latest news earnings regulation risks opportunities")
    items: List[NewsItem] = []

    if not summary:
        # Fallback to DDG search and LLM summarization of snippets
        items = search_news_ddg(f"{company} India stock news")
        snippets = "\n".join([f"- {n.title}: {n.snippet or ''} ({n.url})" for n in items[:10]])
        prompt = (
            "Summarize the latest India-relevant news for a non-finance reader. "
            "Be concise, list key themes, risks, and opportunities.\n" + snippets
        )
        summary = llm.summarize(prompt, system="You are a senior financial editor summarizing news in simple English.")

    if not items:
        # If OpenAI web summary provided links embedded, we still return an empty items list; summary holds the value
        items = []

    return NewsReport(items=items, summary=summary or "No recent news found.")
