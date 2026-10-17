"""Turns an engine SpecExtract into a BuildingBeesEngine graph, and attaches generated questions."""

import datetime
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
    """Maps an engine's screen-state text to the board value; UNSPECIFIED becomes empty so it gets decided."""
    # An unspecified state is treated as missing so readiness flags it.
    return "" if not value or value.strip().upper() == "UNSPECIFIED" else value


_FILLER = {"the", "a", "an", "is", "are", "do", "does", "should", "what", "how", "if", "to", "of", "for", "in",
           "on", "we", "it", "this", "that", "and", "or", "when", "while", "happens", "happen", "be", "can", "their"}


def _words(text: str) -> set:
    """The meaningful words of a question, for spotting near-duplicates."""
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


def _one_question(text: str) -> str:
    """Keeps only the first question when a bee asks two at once ("Do we take deposits? How much?")."""
    i = text.find("?")
    return text[:i + 1] if 0 <= i < len(text.rstrip()) - 1 and "?" in text[i + 1:] else text


def add_questions(engine: BuildingBeesEngine, questions: Iterable[XQuestion], source: str = "ai",
                  dedupe: bool = True) -> list:
    """Pins the engine's questions to their nodes, skipping unknown targets and near-duplicates; returns the ones added."""
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
            # One question at a time (research 04: prompts alone let ~29% double questions through); no em dashes.
            question_text=_one_question(q.question).replace("\u2014", ", ").replace(" ,", ","),
            is_blocking=q.is_blocking,
            assigned_to=f"{cat.value}_LEAD",
            question_status=QuestionStatus.OPEN,
            author_bee=BEE_FOR_CATEGORY[cat],
            suggested_options=q.suggested_options,
            metadata={"source": source, "step": q.step, "cite": q.source, "why": q.why[:240]},
        )
        engine.add_node(node)
        engine.add_edge(q.target_id, node.id)
        added.append(node)
    return added


def build_graph_from_extract(x: SpecExtract, source: str = "ai") -> BuildingBeesEngine:
    """Stage two: builds the full board (users, flows, screens, buttons, APIs, entities, questions) from the engine's output."""
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


def clean_branches(branches, n_steps: int) -> list:
    """Branches that split off a step that exists; anything pointing elsewhere is dropped, never guessed."""
    out = []
    for b in branches:
        if 1 <= b.at_step <= n_steps and b.decision:
            d = b.model_dump()
            d["rejoin_step"] = d["rejoin_step"] if 0 < d["rejoin_step"] <= n_steps else 0
            out.append(d)
    return out


def ask_open_branches(g: BuildingBeesEngine, source: str = "ai") -> list:
    """Every path nobody has decided gets one Testing Bee question, so an empty branch on the board is always asked about."""
    added = []
    for f in [n for n in g.nodes.values() if n.layer.value == "FLOW"]:
        asked = {q.metadata.get("branch") for q in g.get_questions_for_node(f.id)}
        for b in f.metadata.get("branches", []):
            key = f"{b['at_step']}|{b['label']}"
            if b["steps"] or key in asked:
                continue
            q = XQuestion(target_id=f.id, category="TESTER", is_blocking=True, step=b["at_step"],
                          question=f'What happens on the "{b["label"]}" path after "{b["decision"].rstrip("?")}"?',  # a "?" inside quotes cut the question short
                          suggested_options=["Let them try again", "Show a message and stop", "Someone follows up"])
            for node in add_questions(g, [q], source, dedupe=False):
                node.metadata["branch"] = key
                added.append(node)
    return added


def build_flows_graph(x: FlowsExtract, source: str = "ai") -> BuildingBeesEngine:
    """Stage one: users and flows only, with the questions to settle before any screen is drawn."""
    g = BuildingBeesEngine()
    g.product_name = clean_name(x.product_name)
    for u in x.users:
        g.add_node(UserNode(id=u.id, title=u.title, description=u.description,
                            flow_ids=[f.id for f in x.flows if f.user_id == u.id]))
    for f in x.flows:
        g.add_node(FlowNode(id=f.id, title=f.title, goal=f.goal,
                            metadata={"steps": f.steps, "branches": clean_branches(f.branches, len(f.steps))}))
        if f.user_id in g.nodes:
            g.add_edge(f.user_id, f.id)
    g.features = []
    add_features(g, x.features)
    add_questions(g, x.questions, source)
    ask_open_branches(g, source)
    return g


def add_features(g: BuildingBeesEngine, features) -> list:
    """Adds features to the board's feature list as F1, F2...; a name already listed is skipped and flow ids
    that are not on the board are dropped, never guessed. Returns the features added."""
    have = {f["name"].strip().lower() for f in getattr(g, "features", [])}
    flows = {n.id for n in g.nodes.values() if n.layer.value == "FLOW"}
    added = []
    for x in features:
        name = (x.name or "").strip()[:80]
        if not name or name.lower() in have:
            continue
        n = len(getattr(g, "features", [])) + 1
        item = {"id": f"F{n}", "name": name, "priority": x.priority if x.priority in ("must", "should", "later") else "should",
                "flow_ids": [i for i in x.flow_ids if i in flows], "why": (x.why or "")[:200]}
        g.features = getattr(g, "features", []) + [item]
        have.add(name.lower())
        added.append(item)
    return added


def merge_feature(g: BuildingBeesEngine, new: BuildingBeesEngine) -> list:
    """Adds a new feature's users, flows and questions to an existing board; returns the ids added.
    Anything already on the board (same id) is kept as it is: a new feature never rewrites agreed flows."""
    added = []
    for n in new.nodes.values():
        if n.layer.value in ("USER", "FLOW") and n.id not in g.nodes:
            g.add_node(n.model_copy(update={"flow_ids": []}) if n.layer.value == "USER" else n)
            added.append(n.id)
    for fid in [i for i in added if g.nodes[i].layer.value == "FLOW"]:
        owner = next(iter(new.reverse_edges.get(fid, [])), None)  # the user the engine gave the flow to
        if owner in g.nodes and g.nodes[owner].layer.value == "USER":
            g.add_edge(owner, fid)
            g.nodes[owner].flow_ids.append(fid)
    from src.adapters.spec_prompts import XProductFeature  # the new board holds plain dicts; re-check them here
    add_features(g, [XProductFeature(**{k: v for k, v in f.items() if k != "id"}) for f in getattr(new, "features", [])])
    for q in new.nodes.values():  # the bees' questions about the feature, minus ones already asked
        if isinstance(q, QuestionNode) and q.target_node_id in g.nodes and not _already_asked(g, q.question_text):
            g.add_node(q)
            g.add_edge(q.target_node_id, q.id)
    return added


def add_gap_questions(g: BuildingBeesEngine) -> list:
    """Asks about details the board still lacks, so "ready to build" can actually be reached.
    One bundled question per screen or API, written here (no model call), skipped if a bee already asked."""
    asks = []
    for n in list(g.nodes.values()):
        if n.layer.value == "SCREEN":
            need_loading, need_error = g.screen_needs_states(n.id)  # a static screen has no loading or error to settle
            missing = [name for name, v, need in (("loading", n.states.loading, need_loading), ("error", n.states.error, need_error))
                       if need and not v]
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
    return add_questions(g, asks, "BuildingBees", dedupe=False)  # one per node: similar wording is not a repeat here


def add_gap_defaults(g: BuildingBeesEngine) -> list:
    """Details with an industry-standard answer are filled in, not asked: the team sees them as defaults it can change."""
    added = add_gap_questions(g)
    now = datetime.datetime.utcnow().isoformat()
    for q in added:
        if apply_gap_default(g, q):
            q.answered_at = now
    return added


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
    q.metadata["note"] = "Standard default applied. Change it if your team wants something else."
    q.metadata["default"] = True
    return True
