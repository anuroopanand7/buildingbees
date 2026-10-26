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


def test_six_docs_from_the_board_and_the_docs_call(monkeypatch):
    """Stage three: PRD, app flow and plan come from the board; TRD, design brief and schema from one engine call,
    whose open team choices become questions; everything zips for a repo."""
    import io
    import zipfile
    from src.adapters.spec_prompts import DocsExtract, XQuestion, XTable, XColumn, XTech, XToken
    from tests.test_gemini_ingest import FakeGemini
    fake = FakeGemini()
    flow_id = FLOWS.flows[0].id
    fake.write_docs = lambda text: DocsExtract(
        problem="Buyers cannot order soap online.", success_metric="20 orders in the first month",
        stack=[XTech(area="Payments", choice="NOT DECIDED (open question: which provider?)"),
               XTech(area="Database", choice="PostgreSQL")],
        design_tokens=[XToken(name="primary", value="#FFC800", use="buttons")],
        tables=[XTable(name="orders", columns=[XColumn(name="id", type="uuid")], access="buyer reads own")],
        questions=[XQuestion(target_id=flow_id, category="DESIGN", question="Which brand colours should the shop use?",
                             is_blocking=True, suggested_options=["Warm yellow", "Calm green"])])
    monkeypatch.setitem(server.engines, "gemini", fake)
    monkeypatch.setattr(server.tavily, "research", lambda text: [])
    h = {"X-Board": "six-docs"}
    server.boards.pop(h["X-Board"], None)
    client.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "a soap shop"}, headers=h)
    assert client.post("/api/docs?engine=gemini", headers=h).status_code == 400  # screens come first
    client.post("/api/expand?engine=gemini", headers=h)
    before = {d["name"]: d for d in client.get("/api/docs", headers=h).json()["docs"]}
    assert before["trd"]["ready"] == 0 and "Not written yet" in before["trd"]["markdown"]
    g = client.post("/api/docs?engine=gemini", headers=h).json()
    assert any(n.get("question_text") == "Which brand colours should the shop use?" for n in g["nodes"])  # asked, not guessed
    docs = {d["name"]: d for d in client.get("/api/docs", headers=h).json()["docs"]}
    assert set(docs) == {"prd", "trd", "flow", "design", "schema", "plan", "agents"}
    assert "20 orders" in docs["prd"]["markdown"] and "#FFC800" in docs["design"]["markdown"]
    assert "PostgreSQL (recommended)" in docs["trd"]["markdown"]  # a pick nobody made is labelled, never passed off as decided
    assert "buyer reads own" in docs["schema"]["markdown"] and "NOT DECIDED" in docs["agents"]["markdown"]
    names = zipfile.ZipFile(io.BytesIO(client.get("/api/docs.zip", headers=h).content)).namelist()
    assert "AGENTS.md" in names and "docs/SCHEMA.md" in names


def test_risky_steps_always_get_a_failure_exit_and_a_test_bee_question():
    """Talent research fix (23 Oct): a pay, book or upload step with no split gets an empty "No" path, which the Test
    Bee asks about; steps that cannot fail (viewing a list) are left alone, and a model's own split is kept."""
    from src.adapters.spec_prompts import XBranch, XFlowPlan
    from src.core.ingest import build_flows_graph, clean_branches
    steps = ["Browse: the buyer sees the soaps", "Pay: the buyer pays by UPI", "Upload: the seller adds a photo"]
    kept = clean_branches([XBranch(at_step=3, decision="Photo accepted?", main_label="Yes", label="No")], 3, steps)
    assert [b["at_step"] for b in kept] == [3]  # the model drew a split: nothing added
    out = clean_branches([], 3, steps)
    assert len(out) == 1 and out[0]["decision"] == "Pay went through?" and out[0]["steps"] == []  # one exit, first risky step
    x = FLOWS.model_copy(deep=True)
    x.flows = [XFlowPlan(id="F_BUY", title="Buy", goal="Buy soap", user_id=x.users[0].id, steps=steps)]
    g = build_flows_graph(x)
    asked = [q.question_text for q in g.nodes.values() if getattr(q, "category", None) and q.category.value == "TESTER"]
    assert any("Pay went through" in t for t in asked) and not any("Browse" in t for t in asked)


def test_every_skill_has_its_header_and_stays_in_its_token_cap():
    """Lint for talents/: a skill needs the agreed header keys, and its body must fit max_tokens (about 4 characters each)."""
    import glob
    import os
    keys = ["name", "description", "owner_bee", "talent", "version", "source", "license", "max_tokens"]
    root = os.path.join(os.path.dirname(__file__), "..", "talents")
    files = glob.glob(os.path.join(root, "**", "SKILL.md"), recursive=True)
    assert files
    for path in files:
        head, body = open(path).read().split("\n---\n", 1)
        found = [ln.split(":")[0] for ln in head.splitlines()[1:] if ":" in ln]
        assert found == keys, path
        cap = int([ln for ln in head.splitlines() if ln.startswith("max_tokens")][0].split(":")[1])
        assert len(body) / 4 <= cap * 1.1, f"{path} is about {len(body) // 4} tokens, cap {cap}"
        assert "\u2014" not in body


def test_the_india_pack_is_added_only_for_indian_products():
    """Shield's India skill joins the prompt for an Indian idea (on every later call too), never for others."""
    from src.core.skills import local_rules
    from scripts.eval_questions import IDEAS
    assert "GSTIN" in local_rules("A tuition centre app in Pune: parents pay monthly fees by UPI")
    assert not any(local_rules(i) for i in IDEAS)  # the four standard test ideas are untouched
    assert server.audience("solo") == server.audience("solo")
    g = server.BuildingBeesEngine()
    g.spec_text = "fees in rupees for a school in Delhi"
    assert "LOCAL RULES" in server.audience(g) and "LOCAL RULES" not in server.audience(server.BuildingBeesEngine())


def test_build_prompt_for_one_screen(monkeypatch):
    """Raju's idea: a paste-ready prompt per screen, with its buttons and APIs, decisions kept and open questions not guessed."""
    from tests.test_gemini_ingest import FakeGemini
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    monkeypatch.setattr(server.tavily, "research", lambda text: [])
    h = {"X-Board": "build-prompt-test"}
    server.boards.pop(h["X-Board"], None)
    client.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "a shop"}, headers=h)
    g = client.post("/api/expand?engine=gemini", headers=h).json()
    ids = g["short_ids"]
    screen = next(ids[n["id"]] for n in g["nodes"] if n["layer"] == "SCREEN")
    r = client.get(f"/api/prompt/{screen}", headers=h)
    assert r.status_code == 200 and r.text.startswith(f"Build the screen {screen}")
    assert "do not guess" in r.text or "Decided by the team" in r.text or "Use the project's existing stack" in r.text
    flow = next(ids[n["id"]] for n in g["nodes"] if n["layer"] == "FLOW")
    assert client.get(f"/api/prompt/{flow}", headers=h).status_code == 404  # prompts are per screen


def _drawn_board(monkeypatch, bid):
    """A board with flows and screens from the fake Gemini engine."""
    from tests.test_gemini_ingest import FakeGemini
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    monkeypatch.setattr(server.tavily, "research", lambda text: [])
    h = {"X-Board": bid}
    server.boards.pop(bid, None)
    server._mem_hist.pop(bid, None)
    client.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "a shop"}, headers=h)
    return h, client.post("/api/expand?engine=gemini", headers=h).json()


def test_a_suggested_field_change_waits_for_approval(monkeypatch):
    """Raju's idea, our way: a developer's field edit is a Backend question; only "Approve the change" applies it."""
    h, g = _drawn_board(monkeypatch, "field-change")
    api_id = next(n["id"] for n in g["nodes"] if n["layer"] == "API")
    before = server.boards["field-change"].nodes[api_id].outputs_schema.get("fields", [])
    r = client.post(f"/api/nodes/{api_id}/suggest-fields", json={"side": "response", "add": ["eta_minutes"], "why": "home shows it"}, headers=h).json()
    assert server.boards["field-change"].nodes[api_id].outputs_schema.get("fields", []) == before  # nothing yet
    q = server.boards["field-change"].nodes[r["question_id"]]
    assert q.category.value == "BACKEND" and "eta_minutes" in q.question_text
    client.post(f"/api/questions/{q.id}/resolve", json={"answer_text": "Approve the change", "by": "Bolt"}, headers=h)
    assert "eta_minutes" in server.boards["field-change"].nodes[api_id].outputs_schema["fields"]
    assert client.post(f"/api/nodes/{api_id}/suggest-fields", json={"side": "response"}, headers=h).status_code == 400


def test_go_back_to_before_the_screens_and_undo_it(monkeypatch):
    """Raju's undo: drawing screens keeps a snapshot; going back restores it and is itself undoable."""
    h, g = _drawn_board(monkeypatch, "history-test")
    screens = sum(n["layer"] == "SCREEN" for n in g["nodes"])
    pts = client.get("/api/history", headers=h).json()["points"]
    assert pts and pts[0]["why"] == "Before the screens were drawn"
    back = client.post("/api/history/restore", json={"at": pts[0]["at"]}, headers=h).json()
    assert screens and not any(n["layer"] == "SCREEN" for n in back["nodes"])
    again = client.get("/api/history", headers=h).json()["points"][0]
    assert again["why"] == "Before going back"
    redo = client.post("/api/history/restore", json={"at": again["at"]}, headers=h).json()
    assert sum(n["layer"] == "SCREEN" for n in redo["nodes"]) == screens
    assert client.post("/api/history/restore", json={"at": "nope"}, headers=h).status_code == 404


def test_mock_api_answers_with_placeholders(monkeypatch):
    """Raju's live mock: each API answers at /mock/<board>/<path> with example JSON from its response fields."""
    from src.core import mock
    h, g = _drawn_board(monkeypatch, "mock-test")
    api = next(n for n in server.boards["mock-test"].nodes.values() if isinstance(n, server.APINode))
    api.path, api.method = "/orders/{order_id}", "GET"
    api.outputs_schema["fields"] = ["order_id", "total_amount", "is_paid", "items", "created_at"]
    r = client.get("/mock/mock-test/orders/abc")
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "*"
    assert r.json() == {"order_id": "order_123", "total_amount": 0, "is_paid": True, "items": [], "created_at": "2026-11-01T10:30:00Z"}
    assert client.post("/mock/mock-test/orders/abc").status_code == 405
    assert client.get("/mock/mock-test/nothing/here").status_code == 404
    assert mock.sample_json(["email: string", "phone"]) == {"email": "name@example.com", "phone": "+91 90000 00000"}
