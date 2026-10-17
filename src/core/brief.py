"""The Brief: the board written out as one Markdown document a person or a coding agent can build from.
Built straight from the graph, with no model call, so it is instant, free and says only what was decided."""

import datetime
import re
from typing import Dict, List

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


_PREFIX = {"USER": "U", "FLOW": "FL", "SCREEN": "S", "CTA": "B", "API": "A"}


def short_ids(g: BuildingBeesEngine) -> Dict[str, str]:
    """Short ids the board, the Brief and the export share (FL1 a flow, S2 a screen, B3 a button, A1 an API;
    features are F1, F2 on their own list). Given once and kept, so S2 stays S2 through every round and redraw:
    in Roger's ritual "F1" on a screen linked to feature 1, and the agent read the same ids."""
    ids = getattr(g, "short_ids", None)
    if ids is None:
        ids = g.short_ids = {}
    used = {}
    for code in ids.values():
        p = code.rstrip("0123456789")
        used[p] = max(used.get(p, 0), int(code[len(p):] or 0))
    for n in g.nodes.values():
        p = _PREFIX.get(n.layer.value)
        if p and n.id not in ids:
            used[p] = used.get(p, 0) + 1
            ids[n.id] = f"{p}{used[p]}"
    return {k: v for k, v in ids.items() if k in g.nodes}


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
    # The same count the board's header shows ("11 of 13 answered"), then how it splits, so the two never disagree.
    answered = len(questions) - len(still_open)
    split = f"{answered} of {count(len(questions), 'question')} answered: {count(len(decided), 'decision')} by people, {len(defaults)} standard or recommended"
    if screens:
        ready = [s for s in screens if g.evaluate_branch_readiness(s.id).is_build_ready]
        add(f"**Status:** {len(ready)} of {len(screens)} screens are ready to build. {split}; "
            f"{count(len([q for q in still_open if q.is_blocking]), 'blocking question')} open.")
    else:
        add(f"**Status:** flows are being agreed, no screens drawn yet. {split}.")
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

    from src.core.check import plan_check  # here, not at the top: check.py itself imports this module
    check = plan_check(g)
    add("## Plan check")
    add(("**Ready for a builder.**" if check["passed"] else "**Not ready yet.**") + f" {count(len(check['issues']), 'thing')} to settle.")
    for i in check["issues"]:
        add(f"- {'BLOCKER' if i['level'] == 'blocker' else 'Gap'}: {i['text']}")
    add("")

    add("## Who it is for")
    for u in _layer(g, "USER"):
        add(f"- **{u.title}**: {u.description}".rstrip(": "))
    add("")

    sid = short_ids(g)  # FL1, S2, B3, A1: the same ids the board shows
    tag = lambda node_id: f"{sid[node_id]} " if node_id in sid else ""  # noqa: E731
    features = getattr(g, "features", [])
    feats_of = lambda flow_id: [f["id"] for f in features if flow_id in f.get("flow_ids", [])]  # noqa: E731

    add("## Flows")
    for f in _layer(g, "FLOW"):
        add(f"### {tag(f.id)}{f.title}" + (f" (features {', '.join(feats_of(f.id))})" if feats_of(f.id) else ""))
        if f.goal:
            add(f"Goal: {f.goal}")
        branches = f.metadata.get("branches", [])
        for i, step in enumerate(f.metadata.get("steps", []), 1):
            add(f"{i}. {step}")
            for b in (x for x in branches if x["at_step"] == i):  # each split sits under the step it comes after
                end = f"back to step {b['rejoin_step']}" if b.get("rejoin_step") else "ends here"
                add(f"   - **{b['decision']}** {b['main_label']}: carry on. {b['label']}: "
                    + ("; ".join(b["steps"]) + f" ({end})" if b["steps"] else "**not decided yet**"))
        add("")

    if features:
        add("## Features")
        for f in features:
            flows = ", ".join(tag(i).strip() or title(i) for i in f.get("flow_ids", []))
            add(f"- **{f['id']} {f['name']}** ({f['priority']}){': ' + f['why'] if f.get('why') else ''}{f' Flows: {flows}.' if flows else ''}")
        add("")

    if screens:
        add("## Screens")
        for s in screens:
            r = g.evaluate_branch_readiness(s.id)
            flow = getattr(s, "flow_id", "")
            add(f"### {tag(s.id)}{s.title} ({'ready to build' if r.is_build_ready else 'not ready'})"
                + (f", in {tag(flow).strip() or title(flow)}" if flow else "") + (f", features {', '.join(feats_of(flow))}" if feats_of(flow) else ""))
            if s.description:
                add(s.description)
            elements = s.metadata.get("elements", [])
            if elements:
                add("- On screen, top to bottom:")
                for e in elements:  # each element with what it shows: a list's card fields, a choice's options
                    add(f"  - {e['kind']} \"{e['label']}\"" + (f": {e['detail']}" if e.get("detail") else ""))
            need_loading, need_error = g.screen_needs_states(s.id)  # states only where they are real
            if need_loading or s.states.loading:
                add(f"- Loading: {_or_open(s.states.loading)}")
            if s.states.empty:
                add(f"- Empty: {s.states.empty}")
            if need_error or s.states.error:
                add(f"- Error: {_or_open(s.states.error)}")
            for cta_id in sorted(g.forward_edges.get(s.id, [])):
                c = g.nodes.get(cta_id)
                if not c or c.layer.value != "CTA":
                    continue
                calls_api = any(getattr(g.nodes.get(i), "layer", None) and g.nodes[i].layer.value == "API"
                                for i in g.forward_edges.get(c.id, []))
                line = f"- Button {tag(c.id)}**{c.label}**"
                if c.target_screen_on_success:
                    line += f": goes to {title(c.target_screen_on_success)}"
                if calls_api:  # only a button that calls something can fail
                    line += f"; on failure {_or_open(title(c.target_screen_on_failure) if c.target_screen_on_failure else '')}"
                add(line)
                for api_id in sorted(g.forward_edges.get(c.id, [])):
                    a = g.nodes.get(api_id)
                    if a and a.layer.value == "API":
                        wait = f"{a.timeout_ms} ms" if a.timeout_ms else "NOT DECIDED"  # never "NOT DECIDED ms" (Ravi's test)
                        add(f"  - calls {tag(a.id)}`{a.method} {a.path}` (service: {a.service or 'not named'}, "
                            f"vendor: {a.vendor or 'none chosen'}, timeout: {wait})")
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

    notes = getattr(g, "comments", [])
    if notes:  # what people wrote on the board itself, and whether the bees have applied it yet
        add("## Notes on the board")
        for c in notes:
            where = title(c["target"]) + (", step %d" % c["step"] if c.get("step") else "") + \
                (', the "%s" path' % c["path"] if c.get("path") else "")
            state = "applied" if c["status"] == "applied" else "waiting for Update the board"
            add(f"- **About {where}:** {c['text']} _({c.get('by') or 'the founder'}; {state})_")
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

    rounds = getattr(g, "rounds", [])
    if rounds:  # the review rounds, like the daily rounds of Roger's Figma ritual
        add("## Rounds")
        for r in rounds:
            when = (datetime.datetime.fromisoformat(r["at"]) + datetime.timedelta(hours=5, minutes=30)).strftime("%d %b %Y")  # IST
            if r.get("screens"):
                add(f"- **Round {r['n']}** ({when}): screens drawn. {r.get('note', '')}".rstrip())
                continue
            what = ", ".join(r.get("changed", [])) or "nothing on the board"
            ins = " and ".join(x for x in (count(r.get("answers", 0), "answer") if r.get("answers") else "", count(r.get("notes", 0), "note") if r.get("notes") else "") if x) or "nothing new"
            add(f"- **Round {r['n']}** ({when}): {ins} in; changed {what}." + (f" {r['note']}" if r.get("note") else ""))
        add("")

    add("## Still open")
    if not still_open:
        add("Nothing. Every question asked so far has an answer.")
    for q in sorted(still_open, key=lambda q: not q.is_blocking):
        add(f"- {'BLOCKS THE BUILD' if q.is_blocking else 'Good to know'}: {q.question_text} _(about {title(q.target_node_id)})_")
    add("")
    add("Rule for whoever builds this: anything marked NOT DECIDED or listed under Still open must be asked, not assumed.")
    return "\n".join(out) + "\n"
