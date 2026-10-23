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


def test_prompt_tuning_checks_score_a_draft():
    """The optimizer's yes/no checks: a tidy draft passes the structural ones, a broken one fails them."""
    from scripts.optimize_prompt import checks
    good = checks(FLOWS)
    assert good["no standard-detail questions"] and good["questions point at real users or flows"]
    broken = FLOWS.model_copy(deep=True)
    broken.questions[0].target_id = "NOPE"
    broken.features = []
    bad = checks(broken)
    assert not bad["questions point at real users or flows"] and not bad["features listed and linked to flows"]


def test_agent_view_item_ready_gate_decisions_and_ratings(monkeypatch):
    """One part by short id, the ready/blocked gate, the decision log, and question ratings."""
    from tests.test_gemini_ingest import FakeGemini
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    monkeypatch.setattr(server.tavily, "research", lambda text: [])
    h = {"X-Board": "agent-view-test"}
    server.boards.pop(h["X-Board"], None)
    client.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "a shop"}, headers=h)
    g = client.post("/api/expand?engine=gemini", headers=h).json()
    ids = g["short_ids"]
    screen = next(ids[n["id"]] for n in g["nodes"] if n["layer"] == "SCREEN")

    one = client.get(f"/api/item/{screen.lower()}", headers=h).json()  # ids are case-insensitive
    assert one["id"] == screen and one["kind"] == "screen" and "ready_to_build" in one
    assert client.get("/api/item/ZZ9", headers=h).status_code == 404

    wave = client.get("/api/ready", headers=h).json()
    assert {x["id"] for x in wave["ready"]} | {x["id"] for x in wave["blocked"]} >= {screen}
    assert all(x["blocked_by"] for x in wave["blocked"])  # nothing blocked is handed out without its reason

    q = next(n for n in g["nodes"] if n["layer"] == "QUESTION" and n["question_status"] == "OPEN")
    client.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "Yes", "by": "Founder"}, headers=h)
    log = client.get("/api/decisions", headers=h).json()["decisions"]
    assert any(d["decision"] == "Yes" and d["decided_by"] == "Founder" for d in log)

    r = client.post(f"/api/questions/{q['id']}/rate", json={"rating": "crucial", "by": "Founder"}, headers=h).json()
    client.post(f"/api/questions/{q['id']}/rate", json={"rating": "obvious", "by": "Founder"}, headers=h)
    again = client.post(f"/api/questions/{q['id']}/rate", json={"rating": "reword", "by": "Dev"}, headers=h).json()
    assert [x["rating"] for x in again["ratings"]] == ["obvious", "reword"]  # one rating per person, latest wins
    assert client.post(f"/api/questions/{q['id']}/rate", json={"rating": "meh"}, headers=h).status_code == 400


class _BrokenStore:
    """A Firestore stand-in whose reads fail, like a timeout or a short outage."""
    def document(self, bid):
        raise RuntimeError("firestore timeout")


def test_a_failed_board_read_never_turns_into_an_empty_board(monkeypatch):
    """Audit fix 1: a read error is a 503, and nothing is saved, so the real board is never overwritten."""
    saved = []
    monkeypatch.setattr(server, "_store", _BrokenStore())
    monkeypatch.setattr(server, "_doc", lambda bid: _BrokenStore().document(bid))
    monkeypatch.setattr(server, "_save_board", lambda bid, g=None: saved.append(bid) or True)
    h = {"X-Board": "flaky-store-board"}
    server.boards.pop(h["X-Board"], None)
    r = client.post("/api/questions/x/rate", json={"rating": "crucial"}, headers=h)
    assert r.status_code == 503 and saved == []
    assert "flaky-store-board" not in server.boards


def test_restore_never_overwrites_a_board_with_content(monkeypatch):
    """Audit fix 2: /api/restore only refills an empty board."""
    monkeypatch.setattr(server.tavily, "research", lambda text: [])
    h = {"X-Board": "restore-guard"}
    server.boards.pop(h["X-Board"], None)
    client.post("/api/agent/answer", json={"kind": "flows", "answer": FLOWS.model_dump()}, headers=h)
    real = client.post("/api/ingest-prd?engine=agent", json={"prd_markdown": "soap"}, headers=h).json()
    junk = {"nodes": [], "edges": [], "product_name": "VANDAL"}
    after = client.post("/api/restore", json=junk, headers=h).json()
    assert after["product_name"] == real["product_name"] and len(after["nodes"]) == len(real["nodes"])


def test_a_failed_save_is_reported_not_hidden(monkeypatch):
    """Audit fix 3: when the save fails the person gets a 503, not a silent OK."""
    monkeypatch.setattr(server, "_save_board", lambda bid, g=None: False)
    r = client.post("/api/agent/answer", json={"kind": "flows", "answer": FLOWS.model_dump()}, headers={"X-Board": "save-fails"})
    assert r.status_code == 503 and "not saved" in r.json()["detail"]
