import pytest


@pytest.fixture(autouse=True)
def no_web_research(monkeypatch):
    """Tests never call Tavily: a key in the local .env must not cost credits or slow the suite."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def fresh_call_limit():
    """Each test starts with an empty per-minute model-call window, so the suite size never trips it."""
    from src.api import server
    server._recent_calls.clear()
