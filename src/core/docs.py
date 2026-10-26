"""The 6 documents a team needs before an agent writes code (Roger, 23 Oct 2026): PRD, TRD, app flow, UI/UX design
brief, backend schema and implementation plan, plus AGENTS.md, the build prompt a coding agent starts from.

The PRD, app flow and plan are cut from the Brief the board already writes (no model call). The TRD, design brief
and schema come from one engine call (`/api/docs`, stored on `g.docs`); until it runs they say so. Each doc carries
a "ready" percentage: decided questions out of all questions in the bees that own it.
"""

import re
from typing import Any, Dict, List

from src.core.agent_view import ready_wave
from src.core.brief import build_brief
from src.core.contract import test_plan
from src.core.graph import BuildingBeesEngine
from src.core.schema import QuestionNode, QuestionStatus

# name, file, title, the Brief sections it takes, the bees whose questions decide how ready it is
DOCS = [
    ("prd", "PRD.md", "Product requirements (PRD)",
     ["Who it is for", "Features", "Feature list", "User stories", "Out of scope", "Decisions", "Still open"], {"PM"}),
    ("trd", "TRD.md", "Technical requirements (TRD)", [], {"BACKEND", "COMPLIANCE"}),
    ("flow", "APP_FLOW.md", "App flow", ["Flows", "Screens"], {"PM", "TESTER"}),
    ("design", "DESIGN.md", "UI/UX design brief", [], {"DESIGN", "FRONTEND"}),
    ("schema", "SCHEMA.md", "Backend schema", ["Data"], {"BACKEND"}),
    ("plan", "PLAN.md", "Implementation plan", ["Plan check", "Build order", "Glossary"], set()),
]


def _sections(brief: str) -> Dict[str, str]:
    """The Brief's "## " sections by heading, so a doc can reuse them without writing them twice."""
    out = {}
    for part in re.split(r"(?m)^## ", brief)[1:]:
        head, _, body = part.partition("\n")
        out[head.strip()] = "## " + part.strip()
    return out


def _pick(sections: Dict[str, str], wanted: List[str]) -> str:
    """Every Brief section whose heading starts with one of the wanted names, in the wanted order."""
    return "\n\n".join(body for w in wanted for head, body in sections.items() if head.startswith(w))


def _ready(g: BuildingBeesEngine, bees: set) -> int:
    """Percent of the questions from these bees that are decided; 100 when they have asked nothing on a drawn board,
    0 on an empty one (an empty board scored 100, live audit 27 Oct 2026)."""
    qs = [q for q in g.nodes.values() if isinstance(q, QuestionNode) and q.category.value in bees]
    if not qs:
        return 100 if any(n.layer.value == "SCREEN" for n in g.nodes.values()) else 0
    return round(100 * sum(q.question_status == QuestionStatus.ANSWERED for q in qs) / len(qs))


def _lines(items: List[str]) -> str:
    return "\n".join(f"- {i}" for i in items) or "- (none listed)"


def _trd(d: Dict[str, Any]) -> str:
    stack = "\n".join(f"| {t['area']} | {t['choice']} | {t.get('why', '')} |" for t in d.get("stack", []))
    return (f"## Stack\n| Area | Choice | Why |\n|---|---|---|\n{stack}\n\n## Architecture\n{d.get('architecture') or '(not written)'}"
            f"\n\n## Integrations\n{_lines(d.get('integrations', []))}\n\n## Security, roles and data\n{_lines(d.get('security', []))}"
            f"\n\n## Non-functional needs\n{_lines(d.get('nonfunctional', []))}")


def _design(d: Dict[str, Any]) -> str:
    tokens = "\n".join(f"| {t['name']} | `{t['value']}` | {t.get('use', '')} |" for t in d.get("design_tokens", []))
    return (f"## Design tokens\n| Token | Value | Use |\n|---|---|---|\n{tokens}\n\n## Typography\n{d.get('typography') or '(not written)'}"
            f"\n\n## Components\n{_lines(d.get('components', []))}\n\n## Voice\n{d.get('voice') or '(not written)'}"
            f"\n\n## Accessibility\n{_lines(d.get('accessibility', []))}")


def _schema(d: Dict[str, Any]) -> str:
    parts = []
    for t in d.get("tables", []):
        cols = "\n".join(f"| {c['name']} | {c['type']} | {c.get('note', '')} |" for c in t["columns"])
        parts.append(f"### {t['name']}\n| Column | Type | Note |\n|---|---|---|\n{cols}\n\nRelations: {', '.join(t.get('relations', [])) or 'none'}"
                     f"\n\nAccess: {t.get('access') or 'NOT DECIDED'}")
    return "## Tables\n" + ("\n\n".join(parts) or "(none yet)")


def agents_md(g: BuildingBeesEngine, board_link: str = "") -> str:
    """AGENTS.md: the prompt a coding agent (Claude Code, Cursor, Codex) starts the build from."""
    wave = ready_wave(g)
    ready = ", ".join(f"{r['id']} {r['title']}" for r in wave["ready"]) or "nothing yet"
    return f"""# AGENTS.md: build {getattr(g, 'product_name', '') or 'this product'} from its BuildingBees plan

Read PRD.md, TRD.md, APP_FLOW.md, DESIGN.md, SCHEMA.md and PLAN.md before writing code. They were decided by people,
question by question; every id (F1 features, FL1 flows, S2 screens, B3 buttons, A1 APIs) means the same thing in all of them.

Rules:
1. Build in the order of PLAN.md. Build only screens that are ready: right now {ready}.
2. Anything marked NOT DECIDED is not yours to decide. Ask the person, or leave a note on the board.
3. Use the tokens in DESIGN.md and the tables in SCHEMA.md as written; do not add fields or colours.
4. Put the ids in commit messages ("S2: payment screen"), so a bug can be traced back to the plan.
5. When the plan is wrong or unclear, say so on the board instead of working around it.
{f'''
Live board: {board_link}
With the BuildingBees MCP server (`claude mcp add buildingbees -- python3 scripts/mcp_server.py`): next_to_build,
get_item, decision_log, add_note.''' if board_link else ''}
"""


def build_docs(g: BuildingBeesEngine, board_link: str = "") -> List[Dict[str, Any]]:
    """The 6 docs and AGENTS.md as Markdown, each with how ready it is."""
    sections = _sections(build_brief(g))
    d = getattr(g, "docs", None) or {}
    name = getattr(g, "product_name", "") or "This product"
    missing = "Not written yet. Press \"Write the tech docs\" (one AI call) once the screens are drawn."
    out = []
    for key, file, title, wanted, bees in DOCS:
        if key == "prd":
            head = (f"## Problem\n{d['problem']}\n\n## Success metric\n{d['success_metric']}\n\n" if d else "")
            body = head + _pick(sections, wanted)
        elif key == "trd":
            body = _trd(d) if d else missing
        elif key == "design":
            body = _design(d) if d else missing
        elif key == "schema":
            body = _schema(d) if d.get("tables") else _pick(sections, wanted) or missing
        else:
            body = _pick(sections, wanted)
        ready = _ready(g, bees) if key != "plan" else (
            round(100 * len(w["ready"]) / max(1, len(w["ready"]) + len(w["blocked"]))) if (w := ready_wave(g)) else 0)
        if key in ("trd", "design") and not d:
            ready = 0
        out.append({"name": key, "file": file, "title": title, "ready": ready,
                    "markdown": f"# {title}: {name}\n\n{body or '(nothing on the board for this yet)'}\n"})
    out.append({"name": "tests", "file": "TESTS.md", "title": "Test plan", "ready": _ready(g, {"TESTER"}),
                "markdown": test_plan(g)})
    out.append({"name": "agents", "file": "AGENTS.md", "title": "Build prompt for coding agents", "ready": out[-1]["ready"],
                "markdown": agents_md(g, board_link)})
    return out
