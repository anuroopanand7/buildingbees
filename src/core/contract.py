"""Two exports built from the board with no model call (Raju's second list, 26 Oct 2026):
an OpenAPI 3.0 spec of the board's APIs, and a test plan (TESTS.md) walking every flow's screens and failure paths."""

import re
from typing import Any, Dict, List

from src.core.brief import short_ids
from src.core.graph import BuildingBeesEngine
from src.core.mock import sample_json
from src.core.schema import APINode, CTANode, ScreenNode


def _params(path: str) -> List[str]:
    """Path parameters, written {id} or :id."""
    return [a or b for a, b in re.findall(r"\{([^}]+)\}|:(\w+)", path)]


def openapi(g: BuildingBeesEngine) -> Dict[str, Any]:
    """OpenAPI 3.0 for every API on the board. Field names come from the board; types and examples are placeholders
    (the board does not decide types), and each operation says so, so a reader never mistakes them for decisions."""
    ids = short_ids(g)
    paths: Dict[str, Dict[str, Any]] = {}
    custom = getattr(g, "mock_data", {}) or {}
    for a in sorted((n for n in g.nodes.values() if isinstance(n, APINode) and n.path), key=lambda n: ids.get(n.id, n.id)):
        path = "/" + re.sub(r":(\w+)", r"{\1}", a.path.strip("/"))
        req = a.inputs_schema.get("fields", [])
        res = a.outputs_schema.get("fields", [])
        op: Dict[str, Any] = {
            "operationId": ids.get(a.id, a.id),
            "summary": a.title or f"{a.method} {a.path}",
            "description": "Fields from the BuildingBees board; types and examples are placeholders, not decisions.",
            "parameters": [{"name": p, "in": "path", "required": True, "schema": {"type": "string"}} for p in _params(a.path)],
            "responses": {"200": {"description": "OK", "content": {"application/json": {
                "schema": {"type": "object", "properties": {k: {} for k in sample_json(res)}},
                "example": custom.get(a.id, sample_json(res))}}}}}
        if req and a.method.upper() in ("POST", "PUT", "PATCH"):
            op["requestBody"] = {"content": {"application/json": {
                "schema": {"type": "object", "properties": {k: {} for k in sample_json(req)}}, "example": sample_json(req)}}}
        for code, info in (a.error_codes or {}).items():
            op["responses"][str(code)] = {"description": ", ".join(str(v) for v in (info or {}).values()) or "Error"}
        paths.setdefault(path, {})[(a.method or "GET").lower()] = op
    return {"openapi": "3.0.3", "info": {"title": f"{getattr(g, 'product_name', '') or 'Product'} API", "version": "0.1.0",
            "description": "Generated from a BuildingBees board."}, "paths": paths}


def test_plan(g: BuildingBeesEngine) -> str:
    """TESTS.md: one happy-path scenario per flow (its screens in order, each button and the API it calls), one
    scenario per drawn failure screen, and the buttons that call an API with no failure screen yet, as gaps to decide."""
    ids = short_ids(g)
    sid = lambda i: ids.get(i, i)  # noqa: E731
    out, n = ["# Test plan", "", "Written from the board: each step is a screen, button or API the team agreed on. "
              "Turn each scenario into a Playwright or Cypress test.", ""], 0
    gaps = []
    for f in (x for x in g.nodes.values() if x.layer.value == "FLOW"):
        screens = [g.nodes[s] for s in f.screen_ids if isinstance(g.nodes.get(s), ScreenNode)]
        if not screens:
            continue
        n += 1
        out.append(f"## {n}. Happy path: {f.title}")
        step = 0
        for s in screens:
            step += 1
            out.append(f"{step}. Open {sid(s.id)} ({s.title}); check it shows its content, and its empty and error states.")
            for c in (g.nodes[c] for c in s.cta_ids if isinstance(g.nodes.get(c), CTANode)):
                apis = [g.nodes[a] for a in c.apis_called if isinstance(g.nodes.get(a), APINode)]
                calls = "; ".join(f"expect {a.method} {a.path} to succeed" for a in apis)
                to = g.nodes.get(c.target_screen_on_success)
                step += 1
                out.append(f"{step}. Tap {sid(c.id)} \"{c.label}\"" + (f": {calls}" if calls else "")
                           + (f"; expect {sid(to.id)} ({to.title})" if to is not None else ""))
                bad = g.nodes.get(c.target_screen_on_failure)
                if apis and isinstance(bad, ScreenNode) and bad.id != s.id:
                    gaps.append(("fail", s, c, apis, bad))
                elif apis:
                    gaps.append(("gap", s, c, apis, None))
        out.append("")
    fails = [x for x in gaps if x[0] == "fail"]
    for _, s, c, apis, bad in fails:
        n += 1
        out += [f"## {n}. Failure path: {sid(c.id)} \"{c.label}\" on {sid(s.id)}",
                f"1. On {sid(s.id)}, make {apis[0].method} {apis[0].path} fail (mock an error or a timeout).",
                f"2. Tap {sid(c.id)}; expect {sid(bad.id)} ({bad.title}) with a way to try again.", ""]
    open_gaps = [x for x in gaps if x[0] == "gap"]
    if open_gaps:
        out.append("## Not decided yet: what happens when these fail")
        out += [f"- {sid(c.id)} \"{c.label}\" on {sid(s.id)} calls {', '.join(sid(a.id) for a in apis)} and has no failure screen."
                for _, s, c, apis, _ in open_gaps]
    return "\n".join(out).strip() + "\n"
