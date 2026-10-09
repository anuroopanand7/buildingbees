"""Turns a Gemini SpecExtract into a BuildingBeesEngine graph, and attaches generated questions."""

from typing import Iterable

from src.adapters.gemini_adapter import SpecExtract, XQuestion
from src.core.graph import BuildingBeesEngine
from src.core.schema import (
    APINode, BeeType, CTANode, FlowNode, QuestionCategory, QuestionNode,
    QuestionStatus, ScreenNode, ScreenStates, UserNode,
)

BEE_FOR_CATEGORY = {
    QuestionCategory.FRONTEND: BeeType.FRONTEND_BEE,
    QuestionCategory.BACKEND: BeeType.BACKEND_BEE,
    QuestionCategory.DESIGN: BeeType.DESIGNER_BEE,
    QuestionCategory.TESTER: BeeType.TESTER_BEE,
    QuestionCategory.PM: BeeType.QUEEN_PM,
    QuestionCategory.COMPLIANCE: BeeType.QUEEN_PM,
}


def _state(value: str) -> str:
    # An unspecified state is treated as missing so readiness flags it.
    return "" if not value or value.strip().upper() == "UNSPECIFIED" else value


def add_questions(engine: BuildingBeesEngine, questions: Iterable[XQuestion]) -> list:
    added = []
    for q in questions:
        if q.target_id not in engine.nodes:
            continue
        try:
            cat = QuestionCategory(q.category.upper())
        except ValueError:
            cat = QuestionCategory.BACKEND
        node = QuestionNode(
            title=f"Spec gap on {q.target_id}",
            target_node_id=q.target_id,
            category=cat,
            question_text=q.question,
            is_blocking=q.is_blocking,
            assigned_to=f"{cat.value}_LEAD",
            question_status=QuestionStatus.OPEN,
            author_bee=BEE_FOR_CATEGORY[cat],
            suggested_options=q.suggested_options,
            metadata={"source": "gemini"},
        )
        engine.add_node(node)
        engine.add_edge(q.target_id, node.id)
        added.append(node)
    return added


def build_graph_from_extract(x: SpecExtract) -> BuildingBeesEngine:
    g = BuildingBeesEngine()
    g.product_name = x.product_name

    for u in x.users:
        g.add_node(UserNode(id=u.id, title=u.title, description=u.description,
                            flow_ids=[f.id for f in x.flows if f.user_id == u.id]))
    for f in x.flows:
        g.add_node(FlowNode(id=f.id, title=f.title, goal=f.goal,
                            screen_ids=[s.id for s in x.screens if s.flow_id == f.id]))
        if f.user_id in g.nodes:
            g.add_edge(f.user_id, f.id)
    for s in x.screens:
        g.add_node(ScreenNode(
            id=s.id, title=s.title, flow_id=s.flow_id, description=s.description,
            states=ScreenStates(default=s.description, loading=_state(s.loading_state),
                                empty=_state(s.empty_state), error=_state(s.error_state)),
            cta_ids=[c.id for c in x.ctas if c.screen_id == s.id],
        ))
        if s.flow_id in g.nodes:
            g.add_edge(s.flow_id, s.id)
    for a in x.apis:
        g.add_node(APINode(id=a.id, title=f"{a.method} {a.path}", method=a.method, path=a.path,
                           service=a.service, vendor=a.vendor or None, timeout_ms=a.timeout_ms,
                           calling_screen_ids=[c.screen_id for c in x.ctas if a.id in c.api_ids]))
    for c in x.ctas:
        g.add_node(CTANode(id=c.id, title=c.label, label=c.label, parent_screen_id=c.screen_id,
                           apis_called=[i for i in c.api_ids if i in g.nodes],
                           target_screen_on_success=c.success_screen_id,
                           target_screen_on_failure=c.failure_screen_id))
        if c.screen_id in g.nodes:
            g.add_edge(c.screen_id, c.id)
        for api_id in c.api_ids:
            if api_id in g.nodes:
                g.add_edge(c.id, api_id)

    add_questions(g, x.questions)
    return g
