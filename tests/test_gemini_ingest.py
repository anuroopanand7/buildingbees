"""Gemini ingest path, with the model call replaced by a fixed SpecExtract."""

from fastapi.testclient import TestClient

from src.adapters.spec_prompts import (
    FlowsExtract, Reaction, XFieldUpdate, XFlowPlan, XFlowUpdate, SpecExtract, XAPI, XCTA, XFlow, XQuestion, XScreen, XUser,
)
from src.api import server
from src.core.ingest import build_graph_from_extract

EXTRACT = SpecExtract(
    product_name="Tiny Shop",
    users=[XUser(id="U_BUYER", title="Buyer", description="Buys things")],
    flows=[XFlow(id="F_BUY", title="Buy", goal="Purchase", user_id="U_BUYER")],
    screens=[
        XScreen(id="W01_CART", title="Cart", flow_id="F_BUY", description="Cart list",
                loading_state="Skeleton", empty_state="UNSPECIFIED", error_state="Toast"),
        XScreen(id="W02_DONE", title="Done", flow_id="F_BUY", description="Thanks",
                loading_state="Spinner", empty_state="n/a", error_state="Retry"),
    ],
    ctas=[XCTA(id="CTA_PAY", label="Pay", screen_id="W01_CART", api_ids=["API_PAY", "API_GHOST"],
               success_screen_id="W02_DONE", failure_screen_id="W01_CART")],
    apis=[XAPI(id="API_PAY", method="POST", path="/pay", service="payments", vendor="", timeout_ms=0)],
    questions=[
        XQuestion(target_id="API_PAY", category="backend", question="What if the gateway times out?",
                  is_blocking=True, suggested_options=["Retry once", "Fail fast"]),
        XQuestion(target_id="NOPE", category="PM", question="Dropped: unknown target", is_blocking=True,
                  suggested_options=[]),
    ],
)


FLOWS = FlowsExtract(
    product_name="Tiny Shop",
    users=[XUser(id="U_BUYER", title="Buyer", description="Buys things")],
    flows=[XFlowPlan(id="F_BUY", title="Buy", goal="Purchase", user_id="U_BUYER",
                     steps=["Open cart", "Pay", "See confirmation"])],
    questions=[XQuestion(target_id="F_BUY", category="PM", question="Is guest checkout allowed?",
                         is_blocking=True, suggested_options=["Yes", "No, sign-in required"])],
)


def test_extract_builds_connected_graph():
    g = build_graph_from_extract(EXTRACT)
    assert g.product_name == "Tiny Shop"
    assert "API_PAY" in g.forward_edges["CTA_PAY"]
    assert "API_GHOST" not in g.nodes  # dangling reference ignored
    assert len(g.get_questions_for_node("API_PAY")) == 1
    r = g.evaluate_branch_readiness("W01_CART")
    assert r.readiness_score == 0.0 and not r.is_build_ready


class FakeGemini:
    key = "gemini"
    label = "Fake Gemini"
    enabled = True
    model = "fake"

    last_brief = ""

    def extract_flows(self, text="", pdf_bytes=None):
        return FLOWS

    def extract_spec(self, text="", pdf_bytes=None):
        FakeGemini.last_brief = text
        return EXTRACT

    def interrogate(self, node_id, context_json, asked):
        return [XQuestion(target_id=node_id, category="FRONTEND", question="Double tap on Pay?",
                          is_blocking=True, suggested_options=[])]


def test_ingest_interrogate_resolve_flow(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    c = TestClient(server.app)
    try:
        first = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "a shop"}).json()
        assert first["stage"] == "flows" and not any(n["layer"] == "SCREEN" for n in first["nodes"])
        flow_q = next(n for n in first["nodes"] if n["layer"] == "QUESTION")
        c.post(f"/api/questions/{flow_q['id']}/resolve", json={"answer_text": "No, sign-in required"})
        second = c.post("/api/expand?engine=gemini").json()
        assert second["stage"] == "screens"
        assert "Is guest checkout allowed? => No, sign-in required" in FakeGemini.last_brief
        kept = next(n for n in second["nodes"] if n["id"] == flow_q["id"])
        assert kept["answer_text"] == "No, sign-in required"  # the decision travels with the board
        flow = next(n for n in second["nodes"] if n["id"] == "F_BUY")
        assert flow["metadata"]["steps"] == ["Open cart", "Pay", "See confirmation"]
        assert c.post("/api/nodes/CTA_PAY/interrogate?engine=gemini").json()["added"][0]["question_text"] == "Double tap on Pay?"
        screens = {s["screen_id"]: s for s in c.get("/api/screens").json()}
        assert screens["W01_CART"]["is_build_ready"] is False
        for q in screens["W01_CART"]["open_blocking_questions"]:
            assert c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "Retry once"}).status_code == 200
        screens = {s["screen_id"]: s for s in c.get("/api/screens").json()}
        assert screens["W01_CART"]["open_blocking_questions"] == []
    finally:
        c.post("/api/reset")


def test_ingest_without_key_is_refused(monkeypatch):
    class Off(FakeGemini):
        enabled = False
    monkeypatch.setitem(server.engines, "gemini", Off())
    assert TestClient(server.app).post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "x"}).status_code == 503


def test_unknown_engine_rejected():
    assert TestClient(server.app).post("/api/ingest-prd?engine=openai", json={"prd_markdown": "x"}).status_code == 400


def test_nvidia_adapter_parses_json_reply(monkeypatch):
    from src.adapters import nvidia_adapter as nv

    class Resp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": "<think>x</think>Sure: " + EXTRACT.model_dump_json()}}]}

    monkeypatch.setattr(nv.httpx, "post", lambda *a, **k: Resp())
    out = nv.NvidiaNemotronAdapter(api_key="k").extract_spec(text="shop")
    assert out.product_name == "Tiny Shop"


def test_boards_are_per_visitor_and_restorable(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    c = TestClient(server.app)
    a, b = {"X-Board": "judge-a"}, {"X-Board": "judge-b"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=a)
    c.post("/api/expand?engine=gemini", headers=a)
    saved = c.get("/api/graph", headers=a).json()
    assert saved["spec_text"] == "shop"
    assert saved["total_nodes"] > 0 and saved["product_name"] == "Tiny Shop"
    assert c.get("/api/graph", headers=b).json()["total_nodes"] == 0  # B never sees A's board

    server.boards.clear()  # server slept: memory gone
    assert c.get("/api/graph", headers=a).json()["total_nodes"] == 0
    back = c.post("/api/restore", json=saved, headers=a).json()
    assert back["total_nodes"] == saved["total_nodes"] and back["total_edges"] == saved["total_edges"]
    screens = {s["screen_id"]: s for s in c.get("/api/screens", headers=a).json()}
    assert screens["W01_CART"]["is_build_ready"] is False  # questions survived the round trip


def test_gemini_falls_back_when_model_is_overloaded():
    from src.adapters.gemini_adapter import FALLBACK_MODELS, GoogleGeminiAdapter

    calls = []

    class Models:
        def generate_content(self, model, contents, config):
            calls.append(model)
            if len(calls) == 1:
                raise RuntimeError("503 UNAVAILABLE. This model is currently experiencing high demand.")
            return type("R", (), {"parsed": EXTRACT, "text": ""})()

    a = GoogleGeminiAdapter(api_key="k", model="primary")
    a._client = type("C", (), {"models": Models()})()
    assert a.extract_spec(text="shop").product_name == "Tiny Shop"
    assert calls == ["primary", FALLBACK_MODELS[0]]


def test_answer_can_be_changed(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    c = TestClient(server.app)
    h = {"X-Board": "changer"}
    first = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h).json()
    q = next(n for n in first["nodes"] if n["layer"] == "QUESTION")
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "Yes"}, headers=h)
    assert c.post(f"/api/questions/{q['id']}/reopen", headers=h).status_code == 200
    again = next(n for n in c.get("/api/graph", headers=h).json()["nodes"] if n["id"] == q["id"])
    assert again["question_status"] == "OPEN" and again["answer_text"] is None


class Reactor(FakeGemini):
    reaction = None

    def react(self, prompt):
        Reactor.prompt = prompt
        return Reactor.reaction


def _answered_flow_question(c, h, text):
    first = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h).json()
    q = next(n for n in first["nodes"] if n["layer"] == "QUESTION")
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": text}, headers=h)
    return q


def test_clear_answer_updates_the_board(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "reactor-clear"}
    q = _answered_flow_question(c, h, "No, sign-in required")
    Reactor.reaction = Reaction(
        is_vague=False, note="Got it, I added a sign-in step.", follow_up=[], user_updates=[], field_updates=[],
        flow_updates=[XFlowUpdate(flow_id="F_BUY", title="Buy", goal="Purchase",
                                  steps=["Sign in", "Open cart", "Pay", "See confirmation"]),
                      XFlowUpdate(flow_id="F_CANCEL", title="Cancel an order", goal="Undo", user_id="U_BUYER",
                                  steps=["Open orders", "Cancel"])],
    )
    out = c.post(f"/api/questions/{q['id']}/react?engine=gemini", headers=h).json()
    assert out["changed"] == ["F_BUY", "F_CANCEL"] and not out["is_vague"]  # a flow the founder asked for is added
    edges = c.get("/api/graph", headers=h).json()["edges"]
    assert {"source": "U_BUYER", "target": "F_CANCEL"} in edges
    nodes = {n["id"]: n for n in c.get("/api/graph", headers=h).json()["nodes"]}
    assert nodes["F_BUY"]["metadata"]["steps"][0] == "Sign in"
    assert nodes[q["id"]]["metadata"]["note"] == "Got it, I added a sign-in step."
    assert "No, sign-in required" in Reactor.prompt


def test_vague_answer_gets_a_follow_up_and_changes_nothing(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "reactor-vague"}
    q = _answered_flow_question(c, h, "everyone")
    Reactor.reaction = Reaction(
        is_vague=True, note="That is still broad for me, so one more question.", user_updates=[], field_updates=[],
        flow_updates=[XFlowUpdate(flow_id="F_BUY", title="Buy", goal="Purchase", steps=["Should not apply"])],
        follow_up=[XQuestion(target_id="WRONG", category="PM", question="Which one buyer needs this most?",
                             is_blocking=True, suggested_options=["Students", "Parents"])],
    )
    out = c.post(f"/api/questions/{q['id']}/react?engine=gemini", headers=h).json()
    assert out["is_vague"] and out["changed"] == [] and len(out["follow_up"]) == 1
    nodes = {n["id"]: n for n in c.get("/api/graph", headers=h).json()["nodes"]}
    assert nodes["F_BUY"]["metadata"]["steps"] == ["Open cart", "Pay", "See confirmation"]
    assert nodes[out["follow_up"][0]]["target_node_id"] == q["target_node_id"]  # pinned to the same node


def test_screen_stage_answer_edits_only_allowed_fields(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "reactor-fields"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h)
    second = c.post("/api/expand?engine=gemini", headers=h).json()
    q = next(n for n in second["nodes"] if n["layer"] == "QUESTION" and n["target_node_id"] == "API_PAY")
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "5 seconds, retry once"}, headers=h)
    Reactor.reaction = Reaction(
        is_vague=False, note="Set the timeout.", follow_up=[], flow_updates=[], user_updates=[],
        field_updates=[XFieldUpdate(node_id="API_PAY", field="timeout_ms", value="5000"),
                       XFieldUpdate(node_id="API_PAY", field="id", value="HACKED"),
                       XFieldUpdate(node_id="W01_CART", field="states.empty", value="Show an empty cart message")],
    )
    out = c.post(f"/api/questions/{q['id']}/react?engine=gemini", headers=h).json()
    assert out["changed"] == ["API_PAY", "W01_CART"]
    nodes = {n["id"]: n for n in c.get("/api/graph", headers=h).json()["nodes"]}
    assert nodes["API_PAY"]["timeout_ms"] == 5000 and nodes["W01_CART"]["states"]["empty"].startswith("Show")


def test_brief_states_decisions_and_gaps(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    c, h = TestClient(server.app), {"X-Board": "briefer"}
    assert c.get("/api/brief", headers=h).status_code == 404
    first = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h).json()
    q = next(n for n in first["nodes"] if n["layer"] == "QUESTION")
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "No, sign-in required"}, headers=h)
    c.post("/api/expand?engine=gemini", headers=h)
    brief = c.get("/api/brief", headers=h).text
    assert brief.startswith("# Tiny Shop: product brief")
    assert "1. Open cart" in brief and "### Cart" in brief
    assert "**Is guest checkout allowed?** No, sign-in required" in brief and "Queen Bee" in brief
    assert "BLOCKS THE BUILD: What if the gateway times out?" in brief
    assert "timeout: NOT DECIDED ms" in brief and "vendor: none chosen" in brief
    assert "Empty: NOT DECIDED" not in brief  # an empty state is only printed when one was decided
    assert "\u2014" not in brief


def test_changed_answer_tells_the_bee_what_to_undo(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "reactor-change"}
    q = _answered_flow_question(c, h, "Yes, guests can buy")
    Reactor.reaction = Reaction(is_vague=False, note="ok", follow_up=[], flow_updates=[], user_updates=[], field_updates=[])
    c.post(f"/api/questions/{q['id']}/react?engine=gemini", headers=h)
    assert "CHANGED THEIR MIND" not in Reactor.prompt
    c.post(f"/api/questions/{q['id']}/reopen", headers=h)
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "No, sign-in required"}, headers=h)
    c.post(f"/api/questions/{q['id']}/react?engine=gemini", headers=h)
    assert 'FIRST ANSWERED "Yes, guests can buy"' in Reactor.prompt and "No, sign-in required" in Reactor.prompt
    c.post(f"/api/questions/{q['id']}/reopen", headers=h)  # and the marker does not linger
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "Third thought"}, headers=h)
    c.post(f"/api/questions/{q['id']}/react?engine=gemini", headers=h)
    assert 'FIRST ANSWERED "No, sign-in required"' in Reactor.prompt


def test_same_question_is_not_asked_twice():
    from src.core.ingest import add_questions
    g = build_graph_from_extract(EXTRACT)
    before = len(g.get_questions_for_node("API_PAY"))
    dup = XQuestion(target_id="API_PAY", category="TESTER", question="What happens if the gateway times out?",
                    is_blocking=True, suggested_options=[])
    new = XQuestion(target_id="API_PAY", category="BACKEND", question="Which currency do we charge in?",
                    is_blocking=True, suggested_options=[])
    assert len(add_questions(g, [dup, new])) == 1
    assert len(g.get_questions_for_node("API_PAY")) == before + 1


def test_missing_details_mean_not_ready():
    g = build_graph_from_extract(EXTRACT)
    for q in list(g.nodes.values()):
        if getattr(q, "question_status", None):
            q.question_status = "ANSWERED"
    r = g.evaluate_branch_readiness("W01_CART")  # empty state unspecified is fine, but API_PAY has no timeout
    assert not r.is_build_ready and any("timeout" in x for x in r.completeness_reasons)


def test_gap_questions_make_ready_reachable():
    from src.core.ingest import add_gap_questions
    g = build_graph_from_extract(EXTRACT)
    added = add_gap_questions(g)
    targets = {q.target_node_id for q in added}
    assert "API_PAY" not in targets  # a bee already has an open backend question there
    for q in list(g.nodes.values()):
        if getattr(q, "question_status", None):
            q.question_status = "ANSWERED"
    assert {q.target_node_id for q in add_gap_questions(g)} == {"API_PAY"}  # timeout still missing, so it is asked
    g.nodes["API_PAY"].timeout_ms = 3000
    for q in list(g.nodes.values()):
        if getattr(q, "question_status", None):
            q.question_status = "ANSWERED"
    assert g.evaluate_branch_readiness("W01_CART").is_build_ready and add_gap_questions(g) == []


def test_accept_defaults_fills_details_but_never_answers_a_bee(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    c, h = TestClient(server.app), {"X-Board": "defaults"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h)
    c.post("/api/expand?engine=gemini", headers=h)
    g = server.boards["defaults"]
    bee_q = g.get_questions_for_node("API_PAY")[0]
    assert c.post("/api/questions/accept-defaults", headers=h).json()["applied"] == 0  # only a bee question is open
    assert bee_q.question_status == "OPEN"  # and a bee's question is never answered for the founder

    bee_q.question_status = "ANSWERED"  # the founder answers it without giving a timeout
    from src.core.ingest import add_gap_questions
    assert [q.target_node_id for q in add_gap_questions(g)] == ["API_PAY"]
    out = c.post("/api/questions/accept-defaults", headers=h).json()
    assert out == {"applied": 1, "changed": ["API_PAY"]}
    assert g.nodes["API_PAY"].timeout_ms == 3000


def test_values_nobody_stated_are_stripped():
    from src.core.ingest import strip_guesses
    g = build_graph_from_extract(EXTRACT)
    api = g.nodes["API_PAY"]
    api.vendor, api.timeout_ms = "SendGrid", 4000
    assert strip_guesses(g, "we take card payments") == ["API_PAY"]
    assert api.vendor is None and api.timeout_ms == 0
    api.vendor, api.timeout_ms = "Stripe", 5000
    assert strip_guesses(g, "Pay with Stripe. Wait 5 seconds, no retry.") == []
    assert api.vendor == "Stripe" and api.timeout_ms == 5000


def test_vague_answer_without_follow_up_is_asked_again(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "reactor-deadend"}
    q = _answered_flow_question(c, h, "whatever is normal")
    Reactor.reaction = Reaction(is_vague=True, note="One more question.", follow_up=[], flow_updates=[],
                                user_updates=[], field_updates=[])
    c.post(f"/api/questions/{q['id']}/react?engine=gemini", headers=h)
    again = next(n for n in c.get("/api/graph", headers=h).json()["nodes"] if n["id"] == q["id"])
    assert again["question_status"] == "OPEN" and again["answer_text"] is None


def test_answer_can_bring_in_a_new_user_with_their_own_flow(monkeypatch):
    from src.adapters.spec_prompts import XUserUpdate
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "reactor-newuser"}
    q = _answered_flow_question(c, h, "Staff can refund an order")
    Reactor.reaction = Reaction(
        is_vague=False, note="Added staff.", follow_up=[], field_updates=[],
        user_updates=[XUserUpdate(user_id="U_STAFF", title="Shop staff", description="Handles refunds")],
        flow_updates=[XFlowUpdate(flow_id="F_REFUND", title="Refund an order", goal="Refund", user_id="U_STAFF",
                                  steps=["Open the order", "Refund it"])],
    )
    c.post(f"/api/questions/{q['id']}/react?engine=gemini", headers=h)
    g = c.get("/api/graph", headers=h).json()
    assert {"source": "U_STAFF", "target": "F_REFUND"} in g["edges"]
    assert next(n for n in g["nodes"] if n["id"] == "U_STAFF")["flow_ids"] == ["F_REFUND"]


def test_changed_answer_after_screens_asks_for_a_redraw(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "reactor-redraw"}
    q = _answered_flow_question(c, h, "Email")
    c.post("/api/expand?engine=gemini", headers=h)
    assert c.get("/api/graph", headers=h).json()["needs_redraw"] is False
    c.post(f"/api/questions/{q['id']}/reopen", headers=h)
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "SMS only"}, headers=h)
    Reactor.reaction = Reaction(is_vague=False, note="ok", follow_up=[], flow_updates=[], user_updates=[], field_updates=[])
    c.post(f"/api/questions/{q['id']}/react?engine=gemini", headers=h)
    assert c.get("/api/graph", headers=h).json()["needs_redraw"] is True
    c.post("/api/expand?engine=gemini", headers=h)
    assert c.get("/api/graph", headers=h).json()["needs_redraw"] is False
