"""Bring your own AI: the person's agent answers the bees' prompts with its own model (no model call on our side)."""

from starlette.testclient import TestClient

from src.api import server
from tests.test_gemini_ingest import FLOWS

client = TestClient(server.app)
H = {"X-Board": "agent-test-board"}


def test_agent_engine_hands_over_the_prompt_then_draws_the_board(monkeypatch):
    """First call: 409 with the prompt and schema. After the agent posts its JSON, the same call draws the board."""
    monkeypatch.setattr(server.tavily, "research", lambda text: [])  # no web search in tests
    body = {"prd_markdown": "A tiny shop that sells handmade soap", "mode": "solo"}

    first = client.post("/api/ingest-prd?engine=agent", json=body, headers=H)
    assert first.status_code == 409
    task = first.json()["detail"]
    assert task["needs_agent"] and task["kind"] == "flows"
    assert "handmade soap" in task["prompt"] and "properties" in task["schema"]

    bad = client.post("/api/agent/answer", json={"kind": "flows", "answer": {"oops": 1}}, headers=H)
    assert bad.status_code == 422  # a wrong shape fails early, with the reason

    ok = client.post("/api/agent/answer", json={"kind": "flows", "answer": FLOWS.model_dump()}, headers=H)
    assert ok.status_code == 200

    done = client.post("/api/ingest-prd?engine=agent", json=body, headers=H)
    assert done.status_code == 200
    assert any(n["layer"] == "FLOW" for n in done.json()["nodes"])

    # the answer is used once: the next call asks again instead of reusing a stale board
    assert client.post("/api/ingest-prd?engine=agent", json=body, headers=H).status_code == 409


def test_agent_answers_stay_on_their_own_board(monkeypatch):
    """An answer stored for one board is never used by another."""
    monkeypatch.setattr(server.tavily, "research", lambda text: [])
    client.post("/api/agent/answer", json={"kind": "flows", "answer": FLOWS.model_dump()}, headers={"X-Board": "board-a"})
    other = client.post("/api/ingest-prd?engine=agent", json={"prd_markdown": "x", "mode": "solo"}, headers={"X-Board": "board-b"})
    assert other.status_code == 409


def test_mcp_bring_your_own_ai_remembers_the_task_and_repeats_it(monkeypatch):
    """start_board hands the agent a task; submit_answer posts the JSON and repeats the same request, which draws."""
    from scripts import mcp_server
    calls = []

    def fake_call(path, board, body=None):
        calls.append(path)
        if path == "/api/agent/answer":
            return {"stored": body["kind"]}
        if len(calls) == 1:
            return {"needs_agent": True, "kind": "flows", "prompt": "P", "schema": {}}
        return {"nodes": [{"layer": "FLOW"}, {"layer": "QUESTION", "question_status": "OPEN"}]}

    monkeypatch.setattr(mcp_server, "_call", fake_call)
    task = mcp_server.run_tool("start_board", {"idea": "soap shop"})
    board = task.split()[1]
    assert "TASK (flows)" in task and board in mcp_server.PENDING
    done = mcp_server.run_tool("submit_answer", {"board": board, "answer": {"any": "json"}})
    assert calls == ["/api/ingest-prd?engine=agent", "/api/agent/answer", "/api/ingest-prd?engine=agent"]
    assert "1 flows" in done and "1 open questions" in done and board not in mcp_server.PENDING
