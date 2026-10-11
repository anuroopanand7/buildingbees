import pytest


@pytest.fixture(autouse=True)
def no_web_research(monkeypatch):
    """Tests never call Tavily: a key in the local .env must not cost credits or slow the suite."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
