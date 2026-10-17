"""Plan check: a quality gate a plan passes before it goes to people or a coding agent (idea from Archify's
validate step, Roger, 18 Oct 2026). Built from the graph with no model call, so it is instant and free.
Every issue names the part of the board it is about, by its short id, so it can be found and fixed."""

from typing import Any, Dict, List

from src.core.brief import short_ids
from src.core.graph import BuildingBeesEngine
from src.core.schema import QuestionNode, QuestionStatus


def plan_check(g: BuildingBeesEngine) -> Dict[str, Any]:
    """Returns {"passed": bool, "issues": [{"level": "blocker" | "gap", "text", "id"}]}. A blocker stops a
    builder (a question that must be answered, a must-have feature with nowhere to live); a gap is worth fixing."""
    ids = short_ids(g)
    name = lambda i: f"{ids.get(i, '')} {getattr(g.nodes.get(i), 'title', i)}".strip()  # noqa: E731
    issues: List[Dict[str, str]] = []
    add = lambda level, text, node="": issues.append({"level": level, "text": text, "id": ids.get(node, "")})  # noqa: E731
    flows = [n for n in g.nodes.values() if n.layer.value == "FLOW"]
    screens = [n for n in g.nodes.values() if n.layer.value == "SCREEN"]
    questions = [n for n in g.nodes.values() if isinstance(n, QuestionNode)]

    for q in questions:
        if q.question_status == QuestionStatus.OPEN and q.is_blocking:
            add("blocker", f"Needs an answer before building: \"{q.question_text}\" (about {name(q.target_node_id)})", q.target_node_id)
    for f in flows:
        for b in f.metadata.get("branches", []):
            if not b.get("steps"):
                add("blocker", f"{name(f.id)}: nobody has said what happens on the \"{b['label']}\" path after \"{b['decision'].rstrip('?')}\"", f.id)
        if screens and not any(s.flow_id == f.id for s in screens):
            add("gap", f"{name(f.id)} has no screens yet: press Redraw the screens", f.id)
    for feat in getattr(g, "features", []):
        if not feat.get("flow_ids"):
            add("blocker" if feat.get("priority") == "must" else "gap", f"{feat['id']} {feat['name']} is not part of any flow yet")
    for s in screens:
        need_loading, need_error = g.screen_needs_states(s.id)
        if need_loading and not s.states.loading:
            add("gap", f"{name(s.id)}: what it shows while loading is not decided", s.id)
        if need_error and not s.states.error:
            add("gap", f"{name(s.id)}: what it shows when something fails is not decided", s.id)
    for n in g.nodes.values():
        if n.layer.value == "CTA" and n.apis_called and not n.target_screen_on_failure:
            add("gap", f"{name(n.id)}: where the person goes when it fails is not decided", n.id)
        if n.layer.value == "API" and n.timeout_ms <= 0:
            add("gap", f"{name(n.id)}: how long to wait for a reply is not set", n.id)
    for c in getattr(g, "conflicts", []):
        if c.get("status") == "open":
            add("blocker", f"Misalignment for the product owner: {c['text']}")
    waiting = [c for c in getattr(g, "comments", []) if c.get("status") == "open"]
    if waiting:
        add("gap", f"{len(waiting)} note{'s' if len(waiting) > 1 else ''} on the board not applied yet: press Update the board")
    if getattr(g, "needs_redraw", False):
        add("gap", "Some screens no longer match the decisions: press Redraw the screens")
    return {"passed": not any(i["level"] == "blocker" for i in issues), "issues": issues}
