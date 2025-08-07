from __future__ import annotations
import json
import os
from typing import Optional, List

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config import OPENAI_API_KEY, REASONING_MODEL, SUMMARY_MODEL, USE_OPENAI_WEB_SEARCH


class LLM:
    def __init__(self, timeout_seconds: Optional[float] = None):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        # Default timeout for API calls
        env_timeout = os.getenv("OPENAI_TIMEOUT_SECONDS")
        self.timeout_s: Optional[float] = (
            float(env_timeout) if env_timeout is not None else 20.0
        )
        if timeout_seconds is not None:
            self.timeout_s = timeout_seconds

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def summarize(self, prompt: str, system: Optional[str] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self.client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=messages,
            temperature=0.3,
            timeout=self.timeout_s,
        )
        return resp.choices[0].message.content or ""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def reason(self, prompt: str, system: Optional[str] = None, response_format: Optional[dict] = None) -> str:
        # Use reasoning-capable model for synthesis
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs = {}
        if response_format:
            kwargs["response_format"] = response_format
        resp = self.client.chat.completions.create(
            model=REASONING_MODEL,
            messages=messages,
            **kwargs,
            timeout=self.timeout_s,
        )
        return resp.choices[0].message.content or ""

    def web_search_summary(self, query: str) -> Optional[str]:
        # Best-effort attempt at OpenAI Web Search tool. Falls back to None on failure; caller should handle.
        if not USE_OPENAI_WEB_SEARCH:
            return None
        try:
            # Responses API with web_search tool (subject to availability)
            resp = self.client.responses.create(
                model=REASONING_MODEL,
                input=[{"role": "user", "content": f"Search the web and summarize latest Indian market news about: {query}. Provide links."}],
                tools=[{"type": "web_search"}],
                timeout=self.timeout_s,
            )
            # The structure may vary; try to extract text
            if hasattr(resp, "output") and resp.output:
                # Concatenate text parts
                parts = []
                for item in resp.output:
                    if getattr(item, "type", None) == "message" and item.content:
                        for c in item.content:
                            if getattr(c, "type", None) == "output_text":
                                parts.append(c.text)
                return "\n".join(parts) if parts else None
            if hasattr(resp, "content") and resp.content:
                return str(resp.content)
        except Exception:
            return None
        return None


llm = LLM()
