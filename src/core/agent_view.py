"""What a coding agent reads, in small pieces, with a hard gate (moats 1 and 3 of the 21 Oct 2026 moat research).

Instead of the whole Brief, an agent asks for one part by its short id (S2, B3, A1, FL1, F1) or for the next set of
screens that are safe to build. Nothing blocked is ever handed out: a screen with an open blocking question, on itself
or on its flow, comes back under "blocked" with the questions a person still has to answer. The decision log says who
decided what, when, and which options they turned down, so the agent (and an auditor) can see why the plan is the
way it is. No model call anywhere in this file.
"""

from typing import Any, Dict, List

from src.core.brief import short_ids
from src.core.graph import BuildingBeesEngine
from src.core.schema import QuestionNode, QuestionStatus


def _by_short(g: BuildingBeesEngine) -> Dict[str, str]:
    """Short id (S2) to node id, plus feature ids (F1) to themselves."""
    return {v.upper(): k for k, v in short_ids(g).items()}


def decision_log(g: BuildingBeesEngine) -> List[Dict[str, Any]]:
    """Every decision on the board, oldest first: the question, the answer, who and when, and what was turned down."""
    ids = short_ids(g)
    out = []
    for q in g.nodes.values():
        if not isinstance(q, QuestionNode) or q.question_status != QuestionStatus.ANSWERED:
            continue
        answer = (q.answer_text or "").strip()
        out.append({
            "about": ids.get(q.target_node_id, q.target_node_id),
            "bee": q.category.value,
            "question": q.question_text,
            "decision": answer,
            "decided_by": "the bees (recommended default, can be changed)" if q.metadata.get("default")
                          else (q.metadata.get("answered_by") or "the founder"),
            "decided_at": q.answered_at or "",
            "turned_down": [o for o in (q.suggested_options or []) if o.strip().lower() != answer.lower()],
        })
    return sorted(out, key=lambda d: d["decided_at"])


def _open_on(g: BuildingBeesEngine, node_ids) -> List[Dict[str, Any]]:
    """Open questions about any of these nodes, blocking first."""
    qs = [q for q in g.nodes.values() if isinstance(q, QuestionNode) and q.question_status == QuestionStatus.OPEN
          and q.target_node_id in node_ids]
    return [{"id": q.id, "question": q.question_text, "blocking": q.is_blocking, "options": q.suggested_options}
            for q in sorted(qs, key=lambda q: not q.is_blocking)]


def item(g: BuildingBeesEngine, short: str) -> Dict[str, Any]:
    """One part of the plan by its short id: what it is, what it connects to, its decisions and its open questions."""
    key = short.strip().upper()
    for f in getattr(g, "features", []) or []:
        if str(f.get("id", "")).upper() == key:
            return {"id": key, "kind": "feature", **f}
    node_id = _by_short(g).get(key)
    node = g.nodes.get(node_id) if node_id else None
    if node is None:
        raise KeyError(f"No part of this board is called {short}. Ids look like F1, FL1, S2, B3, A1.")
    ids = short_ids(g)
    sid = lambda i: ids.get(i, i)
    layer = node.layer.value
    data: Dict[str, Any] = {"id": key, "kind": layer.lower(), "title": node.title, "description": node.description}
    if layer == "FLOW":
        data.update(goal=node.goal, steps=node.metadata.get("steps", []), branches=node.metadata.get("branches", []),
                    screens=[sid(s) for s in node.screen_ids])
    elif layer == "SCREEN":
        data.update(flow=sid(node.flow_id), states=node.states, buttons=[sid(c) for c in node.cta_ids],
                    elements=node.metadata.get("elements", []), acceptance=node.acceptance_criteria)
    elif layer == "CTA":
        data.update(screen=sid(node.parent_screen_id), label=node.label, calls=[sid(a) for a in node.apis_called],
                    on_success=sid(node.target_screen_on_success or ""), on_failure=sid(node.target_screen_on_failure or ""))
    elif layer == "API":
        data.update(method=node.method, path=node.path, inputs=node.inputs_schema, outputs=node.outputs_schema,
                    errors=node.error_codes, timeout_ms=node.timeout_ms, idempotent=node.idempotency_required)
    data["decisions"] = [d for d in decision_log(g) if d["about"] == key]
    data["open_questions"] = _open_on(g, {node_id})
    if layer == "SCREEN":
        r = g.evaluate_branch_readiness(node_id)
        data["ready_to_build"] = r.is_build_ready
    return data


def ready_wave(g: BuildingBeesEngine) -> Dict[str, Any]:
    """The hard gate: screens safe to build now (in flow order) and the blocked ones with what blocks them."""
    ids = short_ids(g)
    ready, blocked = [], []
    flows = [n for n in g.nodes.values() if n.layer.value == "FLOW"]
    order = [s for f in flows for s in f.screen_ids if s in g.nodes]
    order += [n.id for n in g.nodes.values() if n.layer.value == "SCREEN" and n.id not in order]
    for sid in order:
        r = g.evaluate_branch_readiness(sid)
        entry = {"id": ids.get(sid, sid), "title": g.nodes[sid].title}
        if r.is_build_ready:
            ready.append(entry)
        else:
            entry["blocked_by"] = [q.question_text for q in r.open_blocking_questions]
            blocked.append(entry)
    plan = getattr(g, "plan", None) or {}
    return {"ready": ready, "blocked": blocked,
            "build_order": [s.get("title") for s in plan.get("build_order", [])],
            "rule": "Build only the ready screens. Do not build or guess around a blocked one: ask the person, or add a note."}


def _plain(v) -> Dict[str, Any]:
    """A Pydantic model (ScreenStates) or a dict, as a dict."""
    return v.model_dump() if hasattr(v, "model_dump") else (v or {})


def build_prompt(g: BuildingBeesEngine, short: str) -> str:
    """A paste-ready prompt for a coding agent to build one screen: its parts, buttons, the APIs they call, the decisions
    about any of them and what is still open. Built from the board, so it never says more than the team decided."""
    s = item(g, short)
    if s["kind"] != "screen":
        raise KeyError(f"{short} is not a screen. Build prompts are per screen (S1, S2...).")
    buttons = [item(g, b) for b in s["buttons"] if b]
    apis = [item(g, a) for b in buttons for a in b.get("calls", []) if a]
    parts = [s, *buttons, *apis]
    lines = [f"Build the screen {s['id']}: {s['title']}.", s.get("description") or "",
             "", "What is on it: " + (", ".join(f"{e.get('kind', 'text')} \"{e.get('label', '')}\"" + (f" ({e['detail']})" if e.get("detail") else "") for e in s["elements"]) or "not drawn yet"),
             "States: " + "; ".join(f"{k}: {v}" for k, v in _plain(s.get("states")).items() if v)]
    for b in buttons:
        to = "; ".join(x for x in (b["on_success"] and f"on success go to {b['on_success']}",
                                        b["on_failure"] and f"on failure go to {b['on_failure']}") if x)
        lines.append(f"Button {b['id']} \"{b['label'] or b['title']}\"" + (f" calls {', '.join(b['calls'])}" if b["calls"] else "")
                     + (f"; {to}" if to else ""))
    for a in apis:
        lines.append(f"API {a['id']}: {a['method']} {a['path']}; sends {', '.join(a['inputs'].get('fields', [])) or 'nothing'};"
                     f" returns {', '.join(a['outputs'].get('fields', [])) or 'nothing'}"
                     + (f"; timeout {a['timeout_ms']} ms" if a.get("timeout_ms") else "")
                     + ("; must be idempotent" if a.get("idempotent") else ""))
    decided = [f"- {d['about']}: {d['question']} Answer: {d['decision']}" for p in parts for d in p["decisions"]]
    open_qs = [f"- {p['id']}: {q['question']}" for p in parts for q in p["open_questions"]]
    if decided:
        lines += ["", "Decided by the team (do not change):", *decided]
    if open_qs:
        lines += ["", "Not decided yet (do not guess; leave a TODO and ask):", *open_qs]
    lines += ["", "Use the project's existing stack and conventions. Build only this screen and the calls listed."]
    return "\n".join(x for x in lines if x is not None).strip() + "\n"
