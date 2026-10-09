"""Gemini ingest path, with the model call replaced by a fixed SpecExtract."""

from fastapi.testclient import TestClient

from src.adapters.spec_prompts import (
    SpecExtract, XAPI, XCTA, XFlow, XQuestion, XScreen, XUser,
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

    def extract_spec(self, text="", pdf_bytes=None):
        return EXTRACT

    def interrogate(self, node_id, context_json, asked):
        return [XQuestion(target_id=node_id, category="FRONTEND", question="Double tap on Pay?",
                          is_blocking=True, suggested_options=[])]


def test_ingest_interrogate_resolve_flow(monkeypatch):
    monkeypatch.setitem(server.engines, "gemini", FakeGemini())
    c = TestClient(server.app)
    try:
        assert c.post("/api/ingest-prd?engine=gemini", json={"prd_markdown": "a shop"}).json()["total_nodes"] > 0
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
