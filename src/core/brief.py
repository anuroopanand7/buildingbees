"""The Brief: the board written out as one Markdown document a person or a coding agent can build from.
Built straight from the graph, with no model call, so it is instant, free and says only what was decided."""

from typing import List

from src.core.graph import BuildingBeesEngine
from src.core.schema import QuestionNode, QuestionStatus

BEE_NAMES = {"PM": "Queen Bee", "DESIGN": "Design Bee", "FRONTEND": "Frontend Bee",
             "BACKEND": "Backend Bee", "TESTER": "Test Bee", "COMPLIANCE": "Compliance Bee"}


def _layer(g: BuildingBeesEngine, name: str) -> list:
    return [n for n in g.nodes.values() if n.layer.value == name]


def _or_open(value) -> str:
    return str(value) if value not in ("", None, 0) else "NOT DECIDED"


def build_brief(g: BuildingBeesEngine) -> str:
    out: List[str] = []
    add = out.append
    questions = [n for n in g.nodes.values() if isinstance(n, QuestionNode)]
    decided = sorted((q for q in questions if q.question_status == QuestionStatus.ANSWERED
                      and not q.metadata.get("vague")), key=lambda q: q.answered_at or "")
    still_open = [q for q in questions if q.question_status == QuestionStatus.OPEN]
    screens = _layer(g, "SCREEN")
    title = lambda node_id: getattr(g.nodes.get(node_id), "title", node_id)  # noqa: E731
    count = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"  # noqa: E731

    add(f"# {getattr(g, 'product_name', '') or 'Product'}: product brief")
    add("")
    if screens:
        ready = [s for s in screens if g.evaluate_branch_readiness(s.id).is_build_ready]
        add(f"**Status:** {len(ready)} of {len(screens)} screens are ready to build. "
            f"{count(len(decided), 'decision')} made, {count(len([q for q in still_open if q.is_blocking]), 'blocking question')} open.")
    else:
        add(f"**Status:** flows are being agreed, no screens drawn yet. {count(len(decided), 'decision')} made, "
            f"{count(len(still_open), 'question')} open.")
    add("")
    add(f"A tool that draws from one prompt would have guessed {count(len(questions), 'thing')} here. "
        f"BuildingBees asked instead: {len(decided)} decided, {len(still_open)} still open.")
    add("")

    add("## Who it is for")
    for u in _layer(g, "USER"):
        add(f"- **{u.title}**: {u.description}".rstrip(": "))
    add("")

    add("## Flows")
    for f in _layer(g, "FLOW"):
        add(f"### {f.title}")
        if f.goal:
            add(f"Goal: {f.goal}")
        for i, step in enumerate(f.metadata.get("steps", []), 1):
            add(f"{i}. {step}")
        add("")

    if screens:
        add("## Screens")
        for s in screens:
            r = g.evaluate_branch_readiness(s.id)
            add(f"### {s.title} ({'ready to build' if r.is_build_ready else 'not ready'})")
            if s.description:
                add(s.description)
            elements = s.metadata.get("elements", [])
            if elements:
                add("- On screen, top to bottom: " + "; ".join(f"{e['kind']} \"{e['label']}\"" for e in elements))
            add(f"- Loading: {_or_open(s.states.loading)}")
            if s.states.empty:
                add(f"- Empty: {s.states.empty}")
            add(f"- Error: {_or_open(s.states.error)}")
            for cta_id in sorted(g.forward_edges.get(s.id, [])):
                c = g.nodes.get(cta_id)
                if not c or c.layer.value != "CTA":
                    continue
                calls_api = any(getattr(g.nodes.get(i), "layer", None) and g.nodes[i].layer.value == "API"
                                for i in g.forward_edges.get(c.id, []))
                line = f"- Button **{c.label}**"
                if c.target_screen_on_success:
                    line += f": goes to {title(c.target_screen_on_success)}"
                if calls_api:  # only a button that calls something can fail
                    line += f"; on failure {_or_open(title(c.target_screen_on_failure) if c.target_screen_on_failure else '')}"
                add(line)
                for api_id in sorted(g.forward_edges.get(c.id, [])):
                    a = g.nodes.get(api_id)
                    if a and a.layer.value == "API":
                        add(f"  - calls `{a.method} {a.path}` (service: {a.service or 'not named'}, "
                            f"vendor: {a.vendor or 'none chosen'}, timeout: {_or_open(a.timeout_ms)} ms)")
                        sends, returns = a.inputs_schema.get("fields"), a.outputs_schema.get("fields")
                        if sends or returns:
                            add(f"    sends: {', '.join(sends or []) or 'nothing'}; returns: {', '.join(returns or []) or 'nothing'}")
            add("")

    entities = getattr(g, "entities", [])
    if entities:
        add("## Data (proposed from the flows and decisions; confirm before building)")
        for e in entities:
            add(f"- **{e['name']}**: {', '.join(e.get('fields', []))}")
        add("")

    add("## Decisions")
    if not decided:
        add("None yet.")
    for q in decided:
        add(f"- **{q.question_text}** {q.answer_text} _(asked by {BEE_NAMES.get(q.category.value, 'the team')}, about {title(q.target_node_id)})_")
    add("")

    add("## Still open")
    if not still_open:
        add("Nothing. Every question asked so far has an answer.")
    for q in sorted(still_open, key=lambda q: not q.is_blocking):
        add(f"- {'BLOCKS THE BUILD' if q.is_blocking else 'Good to know'}: {q.question_text} _(about {title(q.target_node_id)})_")
    add("")
    add("Rule for whoever builds this: anything marked NOT DECIDED or listed under Still open must be asked, not assumed.")
    return "\n".join(out) + "\n"
