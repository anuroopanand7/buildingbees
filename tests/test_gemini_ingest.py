"""Gemini ingest path, with the model call replaced by a fixed SpecExtract."""

from fastapi.testclient import TestClient

from src.adapters.spec_prompts import (
    FlowsExtract, Reaction, XBranch, XFieldUpdate, XFlowPlan, XFlowUpdate, SpecExtract, XAPI, XCTA, XFlow, XQuestion, XScreen, XUser,
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
        XQuestion(target_id="API_PAY", category="backend", question="Which payment gateway do we use?",
                  is_blocking=True, suggested_options=["Retry once", "Fail fast"]),
        XQuestion(target_id="NOPE", category="PM", question="Dropped: unknown target", is_blocking=True,
                  suggested_options=[]),
    ],
)


FLOWS = FlowsExtract(
    product_name="Tiny Shop",
    users=[XUser(id="U_BUYER", title="Buyer", description="Buys things")],
    flows=[XFlowPlan(id="F_BUY", title="Buy", goal="Purchase", user_id="U_BUYER",
                     steps=["Open cart", "Pay", "See confirmation"],
                     branches=[XBranch(at_step=2, decision="Payment went through?", main_label="Yes", label="No"),
                               XBranch(at_step=9, decision="Off the end?", main_label="Yes", label="No")])],
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
        return [XQuestion(target_id=node_id, category="FRONTEND", question="Can buyers pay in instalments?",
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
        assert c.post("/api/nodes/CTA_PAY/interrogate?engine=gemini").json()["added"][0]["question_text"] == "Can buyers pay in instalments?"
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


def test_flow_branches_are_drawn_filled_by_an_answer_and_briefed(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "reactor-branch"}
    q = _answered_flow_question(c, h, "Show the error and let them try another card")
    flow = next(n for n in c.get("/api/graph", headers=h).json()["nodes"] if n["id"] == "F_BUY")
    assert [b["at_step"] for b in flow["metadata"]["branches"]] == [2]  # a split off a missing step is dropped
    assert "**not decided yet**" in c.get("/api/brief", headers=h).text
    asks = [n for n in c.get("/api/graph", headers=h).json()["nodes"] if n["layer"] == "QUESTION" and n["metadata"].get("branch")]
    assert len(asks) == 1 and asks[0]["metadata"]["step"] == 2  # the empty path is asked about, once
    Reactor.reaction = Reaction(
        is_vague=False, note="Got it, a failed payment goes back to the card.", follow_up=[], user_updates=[],
        field_updates=[], flow_updates=[XFlowUpdate(
            flow_id="F_BUY", title="Buy", goal="Purchase", steps=["Open cart", "Pay", "See confirmation"],
            branches=[XBranch(at_step=2, decision="Payment went through?", main_label="Yes", label="No",
                              steps=["Payment failed: The buyer sees why and keeps the cart."], rejoin_step=2)])],
    )
    c.post(f"/api/questions/{q['id']}/react?engine=gemini", headers=h)
    assert '"branches"' in Reactor.prompt  # the bee sees the splits it may fill
    flow = next(n for n in c.get("/api/graph", headers=h).json()["nodes"] if n["id"] == "F_BUY")
    assert flow["metadata"]["branches"][0]["steps"] == ["Payment failed: The buyer sees why and keeps the cart."]
    assert "(back to step 2)" in c.get("/api/brief", headers=h).text


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
    assert "1. Open cart" in brief and "Cart (" in brief and "### S1 " in brief  # screens carry their short id
    assert "**Is guest checkout allowed?** No, sign-in required" in brief and "Queen Bee" in brief
    assert "BLOCKS THE BUILD: Which payment gateway do we use?" in brief
    assert "timeout: NOT DECIDED" in brief and "vendor: none chosen" in brief
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
    dup = XQuestion(target_id="API_PAY", category="TESTER", question="Which payment gateway should we use?",
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


class FakeStore:
    """Stands in for the Firestore collection: one dict of documents."""
    def __init__(self):
        self.docs = {}

    def document(self, key):
        store = self

        class Doc:
            exists = key in store.docs
            def set(self, data): store.docs[key] = data
            def get(self, field=None): return store.docs[key][field] if field else Doc()
        return Doc()


def test_board_survives_the_server_sleeping(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    monkeypatch.setattr(server, "_store", FakeStore())
    c, h = TestClient(server.app), {"X-Board": "sleeper/../odd id"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h)
    c.post("/api/expand?engine=gemini", headers=h)
    before = c.get("/api/graph", headers=h).json()

    server.boards.clear()  # server slept: memory gone
    after = c.get("/api/graph", headers=h).json()
    assert after["total_nodes"] == before["total_nodes"] > 0 and after["total_edges"] == before["total_edges"]
    assert after["product_name"] == "Tiny Shop" and after["stage"] == "screens"
    assert "Tiny Shop" in c.get("/api/brief?board=sleeper/../odd id").text  # the agent link still works
    assert c.get("/api/graph", headers={"X-Board": "someone-else"}).json()["total_nodes"] == 0


def test_scout_bee_sources_are_cited_and_never_become_decisions(monkeypatch):
    pages = [{"title": "Salon booking rules", "url": "https://example.com/rules", "snippet": "Use StripeX. Deposits are common."}]
    monkeypatch.setattr(server.tavily, "research", lambda idea: pages)
    seen = {}

    class Scouted(FakeGemini):
        def extract_flows(self, text="", pdf_bytes=None):
            seen["prompt"] = text
            x = super().extract_flows(text=text, pdf_bytes=pdf_bytes)
            x.questions[0].source = 1  # came from page 1
            x.questions.append(x.questions[0].model_copy(update={"question": "Something else entirely?", "source": 9}))  # no such page: dropped
            return x

    monkeypatch.setitem(server.engines, "gemini", Scouted())
    c, h = TestClient(server.app), {"X-Board": "scouted"}
    g = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h).json()
    assert "RESEARCH" in seen["prompt"] and "https://example.com/rules" in seen["prompt"]
    assert g["spec_text"] == "shop"  # research is not what the founder said
    assert g["sources"] == [{"title": "Salon booking rules", "url": "https://example.com/rules"}]
    cites = [n["metadata"].get("cite") for n in g["nodes"] if n["layer"] == "QUESTION"]
    assert cites.count(g["sources"][0]) == 1 and all(c in (None, g["sources"][0]) for c in cites)
    assert "https://example.com/rules" in c.get("/api/brief", headers=h).text
    assert c.post("/api/expand?engine=gemini", headers=h).json()["sources"] == g["sources"]


def test_no_tavily_key_means_no_research(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert server.tavily.research("book a haircut") == [] and server.tavily.as_prompt([]) == ""


def test_nemotron_has_a_daily_ceiling(monkeypatch):
    class FakeNemotron(FakeGemini):
        key, label = "nvidia", "NVIDIA Nemotron"

    monkeypatch.setitem(server.engines, "nvidia", FakeNemotron())
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    monkeypatch.setattr(server, "NVIDIA_DAILY_CALLS", 2)
    monkeypatch.setattr(server, "_nvidia_day", {})
    c, h = TestClient(server.app), {"X-Board": "capped"}
    post = lambda: c.post("/api/ingest-prd?engine=nvidia", json={"prd_markdown": "shop"}, headers=h).status_code  # noqa: E731
    assert [post(), post(), post()] == [200, 200, 429]
    assert c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h).status_code != 429


def test_unused_research_does_not_cost_a_second_call(monkeypatch):
    monkeypatch.setattr(server.tavily, "research", lambda idea: [{"title": "T", "url": "https://example.com/t", "snippet": "s"}])
    calls = []

    class Forgetful(FakeGemini):
        def extract_flows(self, text="", pdf_bytes=None):
            calls.append(1)
            x = super().extract_flows(text=text, pdf_bytes=pdf_bytes)
            for q in x.questions:  # never cites a page (the fake's extract is shared between tests)
                q.source = 0
            return x

    monkeypatch.setitem(server.engines, "gemini", Forgetful())
    r = TestClient(server.app).post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers={"X-Board": "forgetful"})
    assert r.status_code == 200 and len(calls) == 1  # one call only: a retry for citations doubled the wait


def test_signed_in_people_get_a_list_of_their_boards(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    monkeypatch.setattr(server, "_uid", lambda auth: {"Bearer ann": "ann", "Bearer bob": "bob"}.get(auth))
    monkeypatch.setattr(server, "_user_boards", {})
    c = TestClient(server.app)
    ann = lambda board: {"X-Board": board, "Authorization": "Bearer ann"}  # noqa: E731
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=ann("ann-1"))
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=ann("ann-2"))
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers={"X-Board": "nobody"})  # not signed in

    mine = c.post("/api/me/boards", headers=ann("ann-empty")).json()["boards"]
    assert [b["id"] for b in mine] == ["ann-2", "ann-1"] and mine[0]["name"] == "Tiny Shop"  # newest first, empty board not listed
    assert c.post("/api/me/boards", headers={"X-Board": "x", "Authorization": "Bearer bob"}).json()["boards"] == []
    assert c.post("/api/me/boards", headers={"X-Board": "x"}).status_code == 401
    assert c.post("/api/me/boards", headers={"X-Board": "x", "Authorization": "Bearer forged"}).status_code == 401


def test_a_bad_token_is_nobody(monkeypatch):
    monkeypatch.setattr(server, "FIREBASE", {"projectId": "p"})
    assert server._uid("Bearer not-a-real-token") is None and server._uid("") is None


def test_standard_details_become_defaults_and_answers_name_who_gave_them(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    c, h = TestClient(server.app), {"X-Board": "team-defaults"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h)
    c.post("/api/expand?engine=gemini", headers=h)
    g = server.boards["team-defaults"]
    bee_q = g.get_questions_for_node("API_PAY")[0]
    c.post(f"/api/questions/{bee_q.id}/resolve", json={"answer_text": "Retry once", "by": "Backend: Ravi"}, headers=h)
    from src.core.ingest import add_gap_defaults
    filled = add_gap_defaults(g)  # the timeout is still missing: it takes the standard instead of being asked
    assert [q.target_node_id for q in filled] == ["API_PAY"] and filled[0].question_status == "ANSWERED"
    assert g.nodes["API_PAY"].timeout_ms == 3000
    brief = c.get("/api/brief", headers=h).text
    assert "answered by Backend: Ravi" in brief and "## Assumption log" in brief


def test_sign_off_is_recorded_and_flags_a_later_change(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    c, h = TestClient(server.app), {"X-Board": "signoff"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h)
    assert "Not signed off yet" in c.get("/api/brief", headers=h).text
    assert c.post("/api/signoff", json={"by": " "}, headers=h).status_code == 400
    c.post("/api/signoff", json={"by": "Client: Priya"}, headers=h)
    brief = c.get("/api/brief", headers=h).text
    assert "Signed off by **Client: Priya**" in brief and "has changed since" not in brief
    q = next(n for n in c.get("/api/graph", headers=h).json()["nodes"] if n["layer"] == "QUESTION")
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "Yes"}, headers=h)
    assert "has changed since: 0 decisions then, 1 now" in c.get("/api/brief", headers=h).text


def test_solo_and_team_boards_are_asked_differently(monkeypatch):
    seen = []

    class Listening(FakeGemini):
        def extract_flows(self, text="", pdf_bytes=None):
            seen.append(text)
            return super().extract_flows(text=text, pdf_bytes=pdf_bytes)

    monkeypatch.setitem(server.engines, "gemini", Listening())
    c = TestClient(server.app)
    solo = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers={"X-Board": "mode-solo"}).json()
    team = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop", "mode": "team"}, headers={"X-Board": "mode-team"}).json()
    assert "ONE PERSON" in seen[0] and "A PRODUCT TEAM" in seen[1]
    assert solo["mode"] == "solo" and team["mode"] == "team"
    assert server.boards["mode-solo"].spec_text == "shop"  # the instruction never becomes part of the founder's spec
    assert c.post("/api/mode", json={"mode": "team"}, headers={"X-Board": "mode-solo"}).json() == {"mode": "team"}
    assert c.post("/api/mode", json={"mode": "crowd"}, headers={"X-Board": "mode-solo"}).status_code == 400


def test_feedback_board_works_the_airs_way(monkeypatch):
    from src.api import feedback
    monkeypatch.setattr(feedback, "_mem", {})
    monkeypatch.setattr(server, "_uid", lambda auth: {"Bearer roger": "ROGER"}.get(auth))
    monkeypatch.setenv("ADMIN_UIDS", "ROGER")
    c = TestClient(server.app)
    t = lambda n: {"X-Tester": n}  # noqa: E731
    assert c.post("/api/feedback", json={"description": "x"}, headers=t("a")).status_code == 400
    r = c.post("/api/feedback", json={"section": "Bee questions", "description": "Too many questions"}, headers=t("a")).json()
    assert r["votes"] == 1 and r["mine"] and r["status"] == "new"  # the reporter's own vote counts
    fid = r["id"]
    assert c.post(f"/api/feedback/{fid}/vote", headers=t("b")).json()["votes"] == 2
    assert c.post(f"/api/feedback/{fid}/status", json={"status": "fix_deployed"}, headers=t("b")).status_code == 403
    c.post(f"/api/feedback/{fid}/comment", json={"text": "Fixed in 92cb8e6"}, headers={"Authorization": "Bearer roger"})
    out = c.post(f"/api/feedback/{fid}/status", json={"status": "fix_deployed"}, headers={"Authorization": "Bearer roger"}).json()
    assert out["comments"][0]["official"] and out["status"] == "fix_deployed"
    for n in ("a", "b"):
        assert c.post(f"/api/feedback/{fid}/confirm", headers=t(n)).json()["status"] == "fix_deployed"
    assert c.post(f"/api/feedback/{fid}/confirm", headers=t("c")).json()["status"] == "resolved"  # third confirmation
    listed = c.get("/api/feedback", headers=t("a")).json()
    assert listed["reports"][0]["id"] == fid and "voters" not in listed["reports"][0] and not listed["team"]


def test_my_reports_include_the_ones_filed_before_signing_in(monkeypatch):
    from src.api import feedback
    monkeypatch.setattr(feedback, "_mem", {})
    monkeypatch.setattr(server, "_uid", lambda auth: {"Bearer sravani": "SRAVANI"}.get(auth))
    c = TestClient(server.app)
    c.post("/api/feedback", json={"description": "Filed while signed out"}, headers={"X-Tester": "phone1"})
    c.post("/api/feedback", json={"description": "Someone else's"}, headers={"X-Tester": "phone2"})
    signed_in = {"X-Tester": "phone1", "Authorization": "Bearer sravani"}
    c.post("/api/feedback", json={"description": "Filed after signing in"}, headers=signed_in)
    mine = [r["description"] for r in c.get("/api/feedback", headers=signed_in).json()["reports"] if r["mine"]]
    assert sorted(mine) == ["Filed after signing in", "Filed while signed out"]


def test_flow_steps_can_be_edited_after_screens_and_ask_for_a_redraw(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    c, h = TestClient(server.app), {"X-Board": "edit-steps"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h)
    out = c.post("/api/flows/F_BUY/steps", json={"steps": ["Open cart", " ", "Pay"]}, headers=h).json()
    flow = next(n for n in out["nodes"] if n["id"] == "F_BUY")
    assert flow["metadata"]["steps"] == ["Open cart", "Pay"] and not out["needs_redraw"]  # no screens yet
    assert flow["metadata"]["branches"][0]["at_step"] == 2  # a split off a step that still exists stays
    c.post("/api/expand?engine=gemini", headers=h)
    out = c.post("/api/flows/F_BUY/steps", json={"steps": ["Open cart", "Pay", "Rate the order"]}, headers=h).json()
    assert out["needs_redraw"]
    assert c.post("/api/flows/F_BUY/steps", json={"steps": [""]}, headers=h).status_code == 400
    assert c.post("/api/flows/NOPE/steps", json={"steps": ["x"]}, headers=h).status_code == 404


def test_out_of_scope_decide_for_me_one_question_and_engine_trace(monkeypatch):
    from src.core.ingest import _one_question
    assert _one_question("Do we take deposits? How much?") == "Do we take deposits?"
    assert _one_question("Who is it for?") == "Who is it for?"
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    c, h = TestClient(server.app), {"X-Board": "scope-shield"}
    state = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h).json()
    assert state["last_call"]["engine"] == "Fake Gemini" and state["last_call"]["schema"] == "validated"
    qs = [n for n in state["nodes"] if n["layer"] == "QUESTION"]
    c.post(f"/api/questions/{qs[0]['id']}/resolve", json={"answer_text": "No, sign-in required"}, headers=h)  # "Is guest checkout allowed?"
    c.post(f"/api/questions/{qs[1]['id']}/resolve", json={"answer_text": "Let them try again", "bees_decided": True}, headers=h)
    brief = c.get("/api/brief", headers=h).text
    scope = brief.split("## Out of scope for v1 (agreed)")[1].split("\n## ")[0]
    assert "Is guest checkout allowed?" in scope
    assert "Let them try again" in brief.split("## Assumption log")[1]  # decided by the bees, still changeable


def test_a_photo_of_a_sketch_goes_to_the_engine_as_an_image(monkeypatch):
    got = {}

    class Seeing(FakeGemini):
        def extract_flows(self, text="", pdf_bytes=None, image=None):
            got["image"] = image
            return super().extract_flows(text=text, pdf_bytes=pdf_bytes)

    monkeypatch.setitem(server.engines, "gemini", Seeing())
    r = TestClient(server.app).post("/api/ingest-file?engine=gemini", headers={"X-Board": "sketch"},
                                    files={"file": ("napkin.png", b"\x89PNG fake", "image/png")})
    assert r.status_code == 200 and got["image"] == (b"\x89PNG fake", "image/png")
    assert server.boards["sketch"].spec_text == "A photo of the founder's sketch"


def test_people_rename_and_delete_their_boards_but_never_a_teammates(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    monkeypatch.setattr(server, "_uid", lambda auth: {"Bearer ann": "ann", "Bearer bob": "bob"}.get(auth))
    monkeypatch.setattr(server, "_user_boards", {})
    c = TestClient(server.app)
    ann, bob = {"Authorization": "Bearer ann"}, {"Authorization": "Bearer bob"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers={**ann, "X-Board": "ann-shop"})
    c.post("/api/me/boards", headers={**bob, "X-Board": "ann-shop"})  # Bob opened Ann's shared link
    out = c.post("/api/me/boards/ann-shop/rename", json={"name": "Corner Shop"}, headers=bob).json()
    assert out["boards"][0]["name"] == "Corner Shop" and server.boards["ann-shop"].product_name == "Corner Shop"
    gone = c.post("/api/me/boards/ann-shop/delete", headers=bob).json()
    assert not gone["deleted"] and gone["boards"] == [] and "ann-shop" in server.boards  # only left Bob's list
    assert c.post("/api/me/boards/ann-shop/delete", headers=ann).json()["deleted"] and "ann-shop" not in server.boards
    assert c.post("/api/me/boards/x/delete").status_code == 401


def test_the_full_plan_adds_stories_features_and_build_order_to_the_brief(monkeypatch):
    from src.adapters.spec_prompts import PlanExtract, XFeature, XSlice, XStory, XTerm
    seen = {}

    class Planner(FakeGemini):
        def write_plan(self, board):
            seen["board"] = board
            return PlanExtract(
                stories=[XStory(flow_id="F_BUY", title="Buy", story="As a buyer, I want to pay, so that I get my order.",
                                criteria=["Given a cart, when I pay, then I see a confirmation."])],
                features=[XFeature(name="Checkout", priority="must"), XFeature(name="Wallet", priority="later")],
                build_order=[XSlice(title="Walking skeleton", builds="Cart to confirmation.", done_when="A test order completes.")],
                glossary=[XTerm(term="Cart", meaning="Items chosen before paying.")])

    monkeypatch.setitem(server.engines, "gemini", Planner())
    c, h = TestClient(server.app), {"X-Board": "full-plan"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h)
    assert "Not written yet" in c.get("/api/brief", headers=h).text
    assert c.post("/api/plan?engine=gemini", headers=h).json()["plan"]["features"][0]["name"] == "Checkout"
    assert "## Flows" in seen["board"] and "## User stories" not in seen["board"]  # written from the Brief, not from itself
    brief = c.get("/api/brief", headers=h).text
    assert "Given a cart, when I pay, then I see a confirmation." in brief
    assert "### Must have for v1" in brief and "### Later" in brief and "Done when: A test order completes." in brief
    q = next(n for n in c.get("/api/graph", headers=h).json()["nodes"] if n["layer"] == "QUESTION")
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "Yes"}, headers=h)
    assert "written before the latest decisions" in c.get("/api/brief", headers=h).text


class FeatureGemini(FakeGemini):
    """Returns the old flow again (must be ignored) plus a new flow for a new user, as Gemini does for a feature."""

    def extract_flows(self, text="", pdf_bytes=None):
        if "THE NEW FEATURE" not in text:
            return FLOWS
        return FlowsExtract(
            product_name="Ignored",
            users=[XUser(id="U_BUYER", title="Renamed", description="x"), XUser(id="U_SELLER", title="Seller", description="Sells")],
            flows=[FLOWS.flows[0].model_copy(update={"steps": ["Changed"]}),
                   XFlowPlan(id="F_LIST", title="List an item", goal="Sell", user_id="U_SELLER",
                             steps=["Add photos: The seller adds pictures.", "Publish: The item goes live."])],
            questions=[XQuestion(target_id="F_LIST", category="PM", question="Can sellers set a reserve price?",
                                 is_blocking=True, suggested_options=["Yes", "No"])],
        )


def test_add_feature_keeps_the_board_and_adds_new_flows(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FeatureGemini())
    c = TestClient(server.app)
    h = {"X-Board": "feature"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h)
    r = c.post("/api/features?engine=gemini", json={"text": "Sellers list items"}, headers=h)
    assert r.status_code == 200 and set(r.json()["added"]) == {"U_SELLER", "F_LIST"}
    nodes = {n["id"]: n for n in r.json()["nodes"]}
    assert nodes["F_BUY"]["metadata"]["steps"] == ["Open cart", "Pay", "See confirmation"]  # agreed flow untouched
    assert nodes["U_BUYER"]["title"] == "Buyer"
    assert any(n.get("question_text") == "Can sellers set a reserve price?" for n in nodes.values())
    assert "Added feature: Sellers list items" in r.json()["spec_text"]
    again = c.post("/api/features?engine=gemini", json={"text": "Sellers list items"}, headers=h)
    assert again.status_code == 422  # nothing new came back: say so instead of pretending
    c.post("/api/expand?engine=gemini", headers=h)  # the fake draws a fixed board, which drops F_LIST again
    after = c.post("/api/features?engine=gemini", json={"text": "Sellers list items"}, headers=h).json()
    assert after["needs_redraw"] is True  # a feature added after screens asks for a redraw
    assert c.post("/api/features?engine=gemini", json={"text": "  "}, headers=h).status_code == 400


def test_a_set_of_answers_is_applied_in_one_call(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "reactor-set"}
    board = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h).json()
    qs = [n for n in board["nodes"] if n["layer"] == "QUESTION"]
    for q in qs:
        c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "No, sign-in required"}, headers=h)
    Reactor.reaction = Reaction(
        is_vague=False, note="Got it, I added sign-in.", follow_up=[], user_updates=[], field_updates=[],
        flow_updates=[XFlowUpdate(flow_id="F_BUY", title="Buy", goal="Purchase",
                                  steps=["Sign in", "Open cart", "Pay", "See confirmation"])])
    r = c.post("/api/questions/react-batch?engine=gemini", json={"question_ids": [q["id"] for q in qs]}, headers=h)
    assert r.status_code == 200 and r.json()["changed"] == ["F_BUY"]
    assert "ANSWERED A SET OF QUESTIONS AT ONCE" in Reactor.prompt  # one prompt carries every answer
    assert all(q["question_text"] in Reactor.prompt for q in qs)
    flow = next(n for n in c.get("/api/graph", headers=h).json()["nodes"] if n["id"] == "F_BUY")
    assert flow["metadata"]["steps"][0] == "Sign in"
    assert c.post("/api/questions/react-batch?engine=gemini", json={"question_ids": ["nope"]}, headers=h).status_code == 404


def test_notes_and_saved_answers_wait_until_the_board_is_updated(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "notes"}
    board = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h).json()
    q = next(n for n in board["nodes"] if n["layer"] == "QUESTION")
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "No, sign-in required", "later": True}, headers=h)
    g = c.post("/api/comments", json={"target": "F_BUY", "step": 2, "text": "Also take bank transfer here"}, headers=h).json()
    note = g["comments"][0]
    assert note["status"] == "open" and note["step"] == 2
    flow = next(n for n in g["nodes"] if n["id"] == "F_BUY")
    assert flow["metadata"]["steps"] == ["Open cart", "Pay", "See confirmation"]  # nothing moved yet
    assert c.post("/api/comments", json={"target": "NOPE", "text": "x"}, headers=h).status_code == 404
    Reactor.reaction = Reaction(
        is_vague=False, note="Added sign-in and bank transfer.", follow_up=[], user_updates=[], field_updates=[],
        flow_updates=[XFlowUpdate(flow_id="F_BUY", title="Buy", goal="Purchase",
                                  steps=["Sign in", "Open cart", "Pay by card or bank transfer", "See confirmation"])])
    r = c.post("/api/questions/react-batch?engine=gemini", json={}, headers=h)
    assert r.status_code == 200 and r.json()["changed"] == ["F_BUY"]
    assert "Also take bank transfer here" in Reactor.prompt and "step 2" in Reactor.prompt
    after = c.get("/api/graph", headers=h).json()
    assert after["comments"][0]["status"] == "applied"
    assert not next(n for n in after["nodes"] if n["id"] == q["id"])["metadata"].get("pending")
    assert c.post("/api/questions/react-batch?engine=gemini", json={}, headers=h).status_code == 404  # nothing left waiting
    assert "## Notes on the board" in c.get("/api/brief", headers=h).text


class RichFlows(FakeGemini):
    """Two flows, a feature list and eight questions, so rounds, features and kept flows can be checked."""

    def extract_flows(self, text="", pdf_bytes=None):
        from src.adapters.spec_prompts import XProductFeature
        return FlowsExtract(
            product_name="Tiny Shop",
            users=[XUser(id="U_BUYER", title="Buyer", description="Buys things")],
            flows=[FLOWS.flows[0], XFlowPlan(id="F_RETURN", title="Return", goal="Send back", user_id="U_BUYER",
                                             steps=["Pick order: The buyer picks an order.", "Send: The buyer ships it back."])],
            questions=[XQuestion(target_id="F_BUY", category="PM", question=t, is_blocking=i < 3, suggested_options=["Yes", "No"])
                       for i, t in enumerate(["Can guests check out?", "Which currencies are accepted?", "Is there a loyalty scheme?",
                                              "Do sellers set shipping prices?", "Are gift wraps offered?", "Can buyers save carts?",
                                              "Is tax shown before payment?", "Do orders need approval?"])],
            features=[XProductFeature(name="Checkout", priority="must", flow_ids=["F_BUY", "F_NOPE"], why="Money"),
                      XProductFeature(name="Returns", priority="soon", flow_ids=["F_RETURN"])],
        )


def test_rounds_budget_features_and_ids(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", RichFlows())
    c, h = TestClient(server.app), {"X-Board": "rounds"}
    g = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h).json()
    assert g["round"] == 1 and len(g["round_questions"]) == 6  # solo budget: 6 of the 9 open questions
    blocking = {n["id"] for n in g["nodes"] if n.get("is_blocking") and n["layer"] == "QUESTION"}
    assert blocking <= set(g["round_questions"])  # blocking questions come first
    assert [f["id"] for f in g["features"]] == ["F1", "F2"]
    assert g["features"][0]["flow_ids"] == ["F_BUY"]  # a flow id that is not on the board is dropped
    assert g["features"][1]["priority"] == "should"  # an unknown priority is not guessed upward
    ids = g["short_ids"]
    assert ids["F_BUY"].startswith("FL") and ids["U_BUYER"] == "U1"
    # Drawing screens: the fake engine returns only F_BUY, but the agreed Return flow must stay on the board.
    after = c.post("/api/expand?engine=gemini", headers=h).json()
    assert "F_RETURN" in {n["id"] for n in after["nodes"]}
    assert after["short_ids"]["F_BUY"] == ids["F_BUY"]  # ids survive the redraw
    assert after["round"] == 1 and after["rounds"][-1]["changed"] == ["Screens drawn"]  # drawing screens stays in the round that agreed the flows
    brief = c.get("/api/brief", headers=h).text
    assert "## Features" in brief and "F1 Checkout" in brief and "## Rounds" in brief


def test_team_rounds_are_processed_by_the_owner(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "team-round"}
    q = _answered_flow_question(c, h, "No, sign-in required")
    c.post("/api/mode", json={"mode": "team"}, headers=h)
    server._board_id.set("team-round")
    server.boards["team-round"].owner = "owner-uid"  # made by someone else, signed in
    blocked = c.post("/api/questions/react-batch?engine=gemini", json={}, headers={**h, "X-Role": "BACKEND"})
    assert blocked.status_code == 403
    assert c.post("/api/flows/F_BUY/steps", json={"steps": ["x"]}, headers={**h, "X-Role": "DESIGN"}).status_code == 403
    Reactor.reaction = Reaction(is_vague=False, note="Done.", follow_up=[], user_updates=[], field_updates=[], flow_updates=[])
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "No, sign-in required", "later": True}, headers=h)
    ok = c.post("/api/questions/react-batch?engine=gemini", json={}, headers={**h, "X-Role": "PM"})
    assert ok.status_code == 200  # the product manager processes the round


def test_states_only_where_they_are_real():
    from src.core.ingest import add_gap_questions
    g = build_graph_from_extract(EXTRACT)
    for n in g.nodes.values():
        if n.layer.value == "SCREEN":
            n.states.loading = n.states.error = ""
            n.metadata["elements"] = [{"kind": "heading", "label": "Thanks"}]
            for c in list(g.forward_edges.get(n.id, [])):
                g.forward_edges[n.id].discard(c)  # no buttons, nothing fetched: a static screen
    asked = add_gap_questions(g)
    assert not any("show" in q.question.lower() and ("load" in q.question.lower() or "wrong" in q.question.lower()) for q in asked)


def test_plan_check_share_page_and_agent_tools(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", RichFlows())
    c, h = TestClient(server.app), {"X-Board": "share"}
    c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h)
    check = c.get("/api/plan-check", headers=h).json()
    assert check["passed"] is False  # blocking questions and an undecided split are open
    assert any("No" in i["text"] and i["level"] == "blocker" for i in check["issues"])
    page = c.get("/api/share", headers=h)
    assert page.status_code == 200 and page.text.startswith("<!doctype html>")
    assert "id='F1'" in page.text and "Plan check" in page.text and "<script" in page.text
    assert "## Plan check" in c.get("/api/brief", headers=h).text
    from scripts import mcp_server
    init = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert init["result"]["serverInfo"]["name"] == "buildingbees"
    names = [t["name"] for t in mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]]
    assert names == ["get_plan", "plan_check", "open_questions", "add_note"]
    assert mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert mcp_server._board("https://x.run.app/?board=abc-1") == "abc-1"


def test_decide_for_me_is_not_asked_again(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "decided"}
    board = c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "shop"}, headers=h).json()
    q = next(n for n in board["nodes"] if n["layer"] == "QUESTION" and n["question_text"] == "Is guest checkout allowed?")
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "Yes", "bees_decided": True, "later": True}, headers=h)
    Reactor.reaction = Reaction(is_vague=False, note="Done.", user_updates=[], field_updates=[], flow_updates=[], follow_up=[
        XQuestion(target_id="F_BUY", category="PM", question="Is guest checkout allowed for buyers?", is_blocking=True,
                  suggested_options=["Yes", "No"]),
        XQuestion(target_id="F_BUY", category="PM", question="Which countries do you ship to?", is_blocking=True,
                  suggested_options=["India", "Worldwide"])])
    r = c.post("/api/questions/react-batch?engine=gemini", json={}, headers=h).json()
    assert "(decided by the bees)" in Reactor.prompt
    texts = [n["question_text"] for n in c.get("/api/graph", headers=h).json()["nodes"] if n["layer"] == "QUESTION"]
    assert "Is guest checkout allowed for buyers?" not in texts  # a rephrase of a settled decision is dropped
    assert "Which countries do you ship to?" in texts and len(r["follow_up"]) == 1


def test_plan_features_do_not_duplicate_the_board_list():
    from src.adapters.spec_prompts import XProductFeature
    from src.core.ingest import add_features
    g = build_graph_from_extract(EXTRACT)
    g.features = []
    add_features(g, [XProductFeature(name="Attendance & Marks View", priority="must")])
    add_features(g, [XProductFeature(name="F1 Attendance View", priority="must"),
                     XProductFeature(name="F2: Monthly Fee Collection", priority="must")])
    assert [f["name"] for f in g.features] == ["Attendance & Marks View", "Monthly Fee Collection"]


def test_misalignments_go_to_the_product_owner(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", Reactor())
    c, h = TestClient(server.app), {"X-Board": "clash"}
    q = _answered_flow_question(c, h, "Cash only")
    c.post(f"/api/questions/{q['id']}/resolve", json={"answer_text": "Cash only", "later": True}, headers=h)
    Reactor.reaction = Reaction(is_vague=False, note="Done.", follow_up=[], user_updates=[], field_updates=[], flow_updates=[],
                                conflicts=["One answer says cash only, an earlier decision says cards: suggest both."])
    g = c.post("/api/questions/react-batch?engine=gemini", json={}, headers=h).json()
    assert g["is_vague"] is False
    board = c.get("/api/graph", headers=h).json()
    assert board["conflicts"][0]["status"] == "open"
    assert any("Misalignment" in i["text"] for i in c.get("/api/plan-check", headers=h).json()["issues"])
    settled = c.post("/api/conflicts/0/settle", json={"decision": "UPI and cash"}, headers=h).json()
    assert settled["conflicts"][0]["status"] == "settled"
    assert any("UPI and cash" in n["text"] and n["status"] == "open" for n in settled["comments"])


def test_nemotron_routing_and_daily_budget(monkeypatch):
    from src.adapters import nvidia_adapter as nv
    calls = []

    class Resp:
        def __init__(self, model): self.model = model
        def raise_for_status(self): pass
        def json(self):
            return {"usage": {"prompt_tokens": 100_000, "completion_tokens": 100_000},
                    "choices": [{"message": {"content": FLOWS.model_dump_json() if "FLOW" in self.model else
                                             Reaction(is_vague=False, note="ok", follow_up=[], flow_updates=[], user_updates=[], field_updates=[]).model_dump_json()}}]}

    def fake_post(url, headers, json, timeout):
        calls.append((json["model"], isinstance(json["messages"][1]["content"], list)))
        return Resp("FLOW" if json["messages"][1]["content"] and "users" in str(json["messages"][1]["content"])[:20000] and "react" not in str(json["messages"][1]["content"])[:40] else "x")

    monkeypatch.setattr(nv.httpx, "post", fake_post)
    a = nv.NvidiaNemotronAdapter(api_key="k")
    a.extract_flows(text="idea")
    assert calls[-1] == (nv.FLOWS_MODEL, False)  # flows: Super VL won the A/B (same quality, 5x cheaper)
    a.extract_flows(text="", image=(b"img", "image/png"))
    assert calls[-1] == (nv.VISION_MODEL, True)  # a sketch photo goes to the vision model with an image part
    spent = a.spent_today
    assert spent > 0  # 100k in and 100k out on Ultra is about $0.40
    a.spent_today = nv.DAILY_BUDGET_USD
    try:
        a.react("THE FOUNDER'S ANSWER: yes")
        assert False, "the budget guard should stop the call"
    except RuntimeError as e:
        assert "budget" in str(e)


def test_bees_never_ask_standard_details():
    from src.core.ingest import add_questions
    g = build_graph_from_extract(EXTRACT)
    added = add_questions(g, [XQuestion(target_id="F_BUY", category="FRONTEND", question="What is the maximum file size for uploads?",
                                        is_blocking=False, suggested_options=["5 MB"]),
                              XQuestion(target_id="F_BUY", category="PM", question="Can guests check out?", is_blocking=True,
                                        suggested_options=["Yes", "No"])], "Google Gemini")
    assert [q.question_text for q in added] == ["Can guests check out?"]


def test_nemotron_falls_back_to_the_other_model(monkeypatch):
    from src.adapters import nvidia_adapter as nv
    seen = []

    def flaky(url, headers, json, timeout):
        seen.append(json["model"])
        class R:
            def raise_for_status(self):
                if json["model"] == nv.DEFAULT_HEAVY_MODEL:
                    raise nv.httpx.HTTPStatusError("503", request=None, response=None)
            def json(self):
                return {"usage": {}, "choices": [{"message": {"content": FLOWS.model_dump_json()}}]}
        return R()

    monkeypatch.setattr(nv.httpx, "post", flaky)
    a = nv.NvidiaNemotronAdapter(api_key="k")
    out = a._generate("prompt", FlowsExtract, model=nv.DEFAULT_HEAVY_MODEL)
    assert out.product_name == "Tiny Shop" and seen == [nv.DEFAULT_HEAVY_MODEL, nv.VISION_MODEL]
