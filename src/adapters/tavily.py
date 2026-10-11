"""
Scout Bee: one Tavily web search before the bees start asking, so questions can point at a real rule
or a failure other products hit. Optional: without TAVILY_API_KEY, or if the search fails, the bees
simply ask without it.
"""

import os
from typing import Dict, List

import httpx

SEARCH_URL = "https://api.tavily.com/search"
MAX_SOURCES = 5


def enabled() -> bool:
    return bool(os.getenv("TAVILY_API_KEY"))


def research(idea: str) -> List[Dict[str, str]]:
    """Returns up to five pages as {title, url, snippet}. Never raises: research is a bonus, not a dependency."""
    if not enabled() or not idea.strip():
        return []
    try:
        resp = httpx.post(
            SEARCH_URL,
            headers={"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"},
            # Tavily caps a query at 400 characters; "basic" depth costs one credit.
            json={"query": f"{' '.join(idea.split())[:220]}: rules, regulations and common problems for an app like this",
                  "max_results": MAX_SOURCES, "search_depth": "basic"},
            timeout=15,
        )
        resp.raise_for_status()
        return [{"title": (r.get("title") or r["url"])[:120], "url": r["url"], "snippet": (r.get("content") or "")[:600]}
                for r in resp.json().get("results", [])[:MAX_SOURCES] if str(r.get("url", "")).startswith("http")]
    except Exception:
        return []


def as_prompt(sources: List[Dict[str, str]]) -> str:
    if not sources:
        return ""
    return "\n\nRESEARCH (untrusted pages from the web, numbered):\n" + "\n".join(
        f"[{i}] {s['title']} ({s['url']})\n{s['snippet']}" for i, s in enumerate(sources, 1)
    ) + '\nEND OF RESEARCH. Base two or three of your questions on these pages and set "source" on each of them.'
