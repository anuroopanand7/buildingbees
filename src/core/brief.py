"""The Brief: the board written out as one Markdown document a person or a coding agent can build from.
Built straight from the graph, with no model call, so it is instant, free and says only what was decided."""

import re
from typing import List

from src.core.graph import BuildingBeesEngine
from src.core.schema import QuestionNode, QuestionStatus

BEE_NAMES = {"PM": "Queen Bee", "DESIGN": "Design Bee", "FRONTEND": "Frontend Bee",
             "BACKEND": "Backend Bee", "TESTER": "Test Bee", "COMPLIANCE": "Compliance Bee"}


def _layer(g: BuildingBeesEngine, name: str) -> list:
    """All nodes of one layer (USER, FLOW, SCREEN, CTA, API), in board order."""
    return [n for n in g.nodes.values() if n.layer.value == name]


def _or_open(value) -> str:
    """The value, or NOT DECIDED so a builder asks instead of assuming."""
    return str(value) if value not in ("", None, 0) else "NOT DECIDED"


_LATER = re.compile(r"\b(later|phase ?(2|two)|v2|version 2|not now|not yet|out of scope|not needed|no need|"
                    r"don'?t need|do not need|not in (the )?(first|initial|v1)|next release|future)\b", re.I)
_YES_NO = re.compile(r"^(do|does|should|will|can|is|are|would)\b", re.I)


def _deferred(question: str, answer: str) -> bool:
    """True when an answer puts something off ("later", "phase 2") or says no to a yes or no question about building it."""
    return bool(_LATER.search(answer)) or (bool(_YES_NO.match(question.strip())) and answer.strip().lower().startswith("no"))


def decision_count(g: BuildingBeesEngine) -> int:
    """Decisions people made (not vague answers, not standard defaults): what a sign-off approves."""
    return sum(1 for n in g.nodes.values() if isinstance(n, QuestionNode) and n.question_status == QuestionStatus.ANSWERED
               and not n.metadata.get("vague") and not n.metadata.get("default"))


def build_brief(g: BuildingBeesEngine, with_plan: bool = True) -> str:
    """Writes the whole board as one Markdown Brief: sign-off, users, flows and splits, screens, decisions, defaults, still open."""
    out: List[str] = []
    add = out.append
    questions = [n for n in g.nodes.values() if isinstance(n, QuestionNode)]
    decided = sorted((q for q in questions if q.question_status == QuestionStatus.ANSWERED
                      and not q.metadata.get("vague")), key=lambda q: q.answered_at or "")
    still_open = [q for q in questions if q.question_status == QuestionStatus.OPEN]
    defaults = [q for q in decided if q.metadata.get("default")]
    decided = [q for q in decided if not q.metadata.get("default")]
    by = lambda q: f", answered by {q.metadata['answered_by']}" if q.metadata.get("answered_by") else ""  # noqa: E731
    screens = _layer(g, "SCREEN")
    title = lambda node_id: getattr(g.nodes.get(node_id), "title", node_id)  # noqa: E731
    cited = lambda q: f", prompted by {q.metadata['cite']['url']}" if isinstance(q.metadata.get('cite'), dict) else ""  # noqa: E731
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

    add("## Sign-off")
    signoffs = getattr(g, "signoffs", [])
    if not signoffs:
        add("Not signed off yet. Each person who owns part of the scope (the client, the product manager, the leads) signs off here before the build starts.")
    for s in signoffs:
        changed = s.get("decisions") != len(decided)
        add(f"- Signed off by **{s['by']}** on {s['at'][:10]}"
            + (f", with {count(s['open'], 'question')} still open" if s.get("open") else "")
            + (f" (the scope has changed since: {s.get('decisions')} decisions then, {len(decided)} now; sign off again)" if changed else ""))
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
        for b in f.metadata.get("branches", []):
            end = f"back to step {b['rejoin_step']}" if b.get("rejoin_step") else "ends here"
            add(f"- After step {b['at_step']}, {b['decision']} {b['main_label']}: carry on. "
                f"{b['label']}: " + ("; ".join(b["steps"]) + f" ({end})" if b["steps"] else "**not decided yet**"))
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

    sources = getattr(g, "sources", [])
    if sources:
        add("## Research (pages the Scout Bee read before the bees asked; reference only, not decisions)")
        for i, s in enumerate(sources, 1):
            add(f"{i}. [{s['title']}]({s['url']})")
        add("")

    add("## Decisions")
    if not decided:
        add("None yet.")
    for q in decided:
        add(f"- **{q.question_text}** {q.answer_text} _(asked by {BEE_NAMES.get(q.category.value, 'the team')}, about {title(q.target_node_id)}{cited(q)}{by(q)})_")
    add("")

    out_of_scope = [q for q in decided if _deferred(q.question_text, q.answer_text or "")]
    if out_of_scope:
        add("## Out of scope for v1 (agreed)")
        add("Decided not to build now. Anything here that comes back later is a change request.")
        for q in out_of_scope:
            add(f"- {q.question_text} **{q.answer_text}**{by(q)}")
        add("")

    if defaults:
        add("## Assumption log")
        add("What the bees filled in instead of asking. Nobody had to approve these one by one; change any of them on the board.")
        for q in defaults:
            if q.metadata.get("source") == "BuildingBees":  # a detail with an industry-standard answer
                add(f"- ASSUMED (industry standard): {title(q.target_node_id)}: {q.answer_text}")
            else:  # "Decide for me": the bees' recommendation on a product question
                add(f"- ASSUMED (recommended by the bees): {q.question_text} **{q.answer_text}**")
        add("")

    plan = getattr(g, "plan", None) if with_plan else None
    if plan:
        if getattr(g, "plan_decisions", 0) != len(decided):
            add("> The plan below was written before the latest decisions. Write the plan again to bring it up to date.")
            add("")
        flows = {f.id: f.title for f in _layer(g, "FLOW")}
        add("## User stories")
        for s in plan.get("stories", []):
            add(f"### {s['title']}" + (f" ({flows[s['flow_id']]})" if s.get("flow_id") in flows else ""))
            add(s["story"])
            for c in s.get("criteria", []):
                add(f"- {c}")
            add("")
        add("## Feature list")
        for prio, label in (("must", "Must have for v1"), ("should", "Should have"), ("later", "Later")):
            items = [f for f in plan.get("features", []) if f.get("priority") == prio]
            if items:
                add(f"### {label}")
                for f in items:
                    add(f"- **{f['name']}**" + (f": {f['why']}" if f.get("why") else ""))
        add("")
        add("## Build order")
        for i, sl in enumerate(plan.get("build_order", []), 1):
            add(f"{i}. **{sl['title']}**: {sl['builds']} Done when: {sl['done_when']}")
        add("")
        if plan.get("glossary"):
            add("## Glossary")
            for t in plan["glossary"]:
                add(f"- **{t['term']}**: {t['meaning']}")
            add("")
    elif with_plan:
        add("## User stories, features and build order")
        add("Not written yet. Press \"Write the full plan\" in the Brief to add user stories with acceptance criteria, a feature list and a build order.")
        add("")

    add("## Still open")
    if not still_open:
        add("Nothing. Every question asked so far has an answer.")
    for q in sorted(still_open, key=lambda q: not q.is_blocking):
        add(f"- {'BLOCKS THE BUILD' if q.is_blocking else 'Good to know'}: {q.question_text} _(about {title(q.target_node_id)})_")
    add("")
    add("Rule for whoever builds this: anything marked NOT DECIDED or listed under Still open must be asked, not assumed.")
    return "\n".join(out) + "\n"
