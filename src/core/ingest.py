"""Turns an engine SpecExtract into a BuildingBeesEngine graph, and attaches generated questions."""

from typing import Iterable

from src.adapters.spec_prompts import FlowsExtract, SpecExtract, XQuestion
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


_FILLER = {"the", "a", "an", "is", "are", "do", "does", "should", "what", "how", "if", "to", "of", "for", "in",
           "on", "we", "it", "this", "that", "and", "or", "when", "while", "happens", "happen", "be", "can", "their"}


def _words(text: str) -> set:
    return {w for w in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if w not in _FILLER}


def _already_asked(engine: BuildingBeesEngine, text: str) -> bool:
    """True when the board already holds a question that says nearly the same thing."""
    new = _words(text)
    for n in engine.nodes.values():
        if isinstance(n, QuestionNode):
            old = _words(n.question_text)
            if new and old and len(new & old) / len(new | old) >= 0.6:
                return True
    return False


def add_questions(engine: BuildingBeesEngine, questions: Iterable[XQuestion], source: str = "ai",
                  dedupe: bool = True) -> list:
    added = []
    for q in questions:
        if q.target_id not in engine.nodes or (dedupe and _already_asked(engine, q.question)):
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
            metadata={"source": source, "step": q.step},
        )
        engine.add_node(node)
        engine.add_edge(q.target_id, node.id)
        added.append(node)
    return added


def build_graph_from_extract(x: SpecExtract, source: str = "ai") -> BuildingBeesEngine:
    g = BuildingBeesEngine()
    g.product_name = clean_name(x.product_name)
    g.entities = [e.model_dump() for e in x.entities]

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
            metadata={"elements": [e.model_dump() for e in s.elements]},
        ))
        if s.flow_id in g.nodes:
            g.add_edge(s.flow_id, s.id)
    for a in x.apis:
        g.add_node(APINode(id=a.id, title=f"{a.method} {a.path}", method=a.method, path=a.path,
                           service=a.service, vendor=a.vendor or None, timeout_ms=a.timeout_ms,
                           inputs_schema={"fields": a.request_fields}, outputs_schema={"fields": a.response_fields},
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

    add_questions(g, x.questions, source)
    return g


def clean_name(name: str) -> str:
    """The product is the founder's, not ours: the engine sometimes prefixes our own name."""
    return name.replace("BuildingBees", "").strip(" :-") or "Untitled product"


def strip_guesses(g: BuildingBeesEngine, said: str) -> list:
    """Removes values the engine filled in that nobody stated: a vendor or a timeout is kept only if it can be
    found in what the founder wrote or answered. Blanking them lets the gap questions ask instead."""
    said = said.lower()
    blanked = []
    for n in g.nodes.values():
        if n.layer.value != "API":
            continue
        if n.vendor and n.vendor.lower() not in said:
            n.vendor = None
            blanked.append(n.id)
        seconds = n.timeout_ms / 1000
        stated = {str(n.timeout_ms), f"{seconds:g} second", f"{seconds:g}s", f"{seconds:g} s "}
        if n.timeout_ms and not any(t in said for t in stated):
            n.timeout_ms = 0
            blanked.append(n.id)
    return list(dict.fromkeys(blanked))


def build_flows_graph(x: FlowsExtract, source: str = "ai") -> BuildingBeesEngine:
    """Stage one: users and flows only, with the questions to settle before any screen is drawn."""
    g = BuildingBeesEngine()
    g.product_name = clean_name(x.product_name)
    for u in x.users:
        g.add_node(UserNode(id=u.id, title=u.title, description=u.description,
                            flow_ids=[f.id for f in x.flows if f.user_id == u.id]))
    for f in x.flows:
        g.add_node(FlowNode(id=f.id, title=f.title, goal=f.goal, metadata={"steps": f.steps}))
        if f.user_id in g.nodes:
            g.add_edge(f.user_id, f.id)
    add_questions(g, x.questions, source)
    return g


def add_gap_questions(g: BuildingBeesEngine) -> list:
    """Asks about details the board still lacks, so "ready to build" can actually be reached.
    One bundled question per screen or API, written here (no model call), skipped if a bee already asked."""
    asks = []
    for n in list(g.nodes.values()):
        if n.layer.value == "SCREEN":
            missing = [name for name, v in (("loading", n.states.loading), ("error", n.states.error)) if not v]
            if missing:
                asks.append(XQuestion(
                    target_id=n.id, category="FRONTEND", is_blocking=False,
                    question=f"What should \"{n.title}\" show while it is {' and when there is an '.join(missing)}?"
                    if missing == ["loading"] else
                    f"What should \"{n.title}\" show {'while it loads and ' if 'loading' in missing else ''}when something goes wrong?",
                    suggested_options=["A skeleton while loading, and an inline message with a retry button on error",
                                       "A spinner while loading, and a full-page error with a way back",
                                       "Keep what the person typed and show the problem next to the field"]))
        elif n.layer.value == "CTA" and n.apis_called and not n.target_screen_on_failure:
            asks.append(XQuestion(
                target_id=n.id, category="FRONTEND", is_blocking=False,
                question=f"If \"{n.label}\" fails, where does the person end up?",
                suggested_options=["Stay on the same screen and show what went wrong",
                                   "Go back one screen", "Show a separate error screen"]))
        elif n.layer.value == "API" and n.timeout_ms <= 0:
            asks.append(XQuestion(
                target_id=n.id, category="BACKEND", is_blocking=False,
                question=f"How long do we wait for \"{n.method} {n.path}\" before giving up, and do we retry?",
                suggested_options=["3 seconds, retry once", "5 seconds, no retry", "10 seconds, retry twice with a pause"]))
    asks = [q for q in asks if not any(o.question_status == QuestionStatus.OPEN for o in g.get_questions_for_node(q.target_id)
                                       if o.category.value == q.category)]
    return add_questions(g, asks, "BuildingBees")


def apply_gap_default(g: BuildingBeesEngine, q: QuestionNode) -> bool:
    """Answers one gap question with its first suggestion and writes it onto the board. No model call.
    Only for the detail questions written by add_gap_questions; the bees' own questions always need the founder."""
    n = g.nodes.get(q.target_node_id)
    if not n or q.metadata.get("source") != "BuildingBees" or not q.suggested_options:
        return False
    choice = q.suggested_options[0]
    if n.layer.value == "SCREEN":
        loading, _, error = choice.partition(", and ")
        error = error or choice
        n.states.loading = n.states.loading or loading
        n.states.error = n.states.error or (error[:1].upper() + error[1:])
    elif n.layer.value == "API":
        n.timeout_ms = int("".join(ch for ch in choice.split(" ")[0] if ch.isdigit()) or 3) * 1000
    elif n.layer.value == "CTA":
        n.target_screen_on_failure = n.parent_screen_id
    else:
        return False
    q.question_status, q.answer_text = QuestionStatus.ANSWERED, choice
    q.metadata["note"] = "Applied as the default for this detail."
    return True
