"""A live mock of a board's APIs (Raju's idea, built 26 Oct 2026): every API on the board answers at
/mock/<board>/<its path> with example JSON shaped from its response fields, so frontend work can start before the
backend exists. Placeholders only: never the board's decisions, never real data."""

import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.graph import BuildingBeesEngine
from src.core.schema import APINode


def sample_for(field: str) -> Any:
    """An example value guessed from a field name only (the same rules as the API panel in web/index.html)."""
    k = re.split(r"[:\s(]", str(field).lower(), maxsplit=1)[0]
    if re.search(r"^(is|has|can)_|enabled|active|paid$", k):
        return True
    if re.search(r"(_at|date|time)$", k):
        return "2026-11-01T10:30:00Z"
    if re.search(r"count|qty|quantity|amount|price|total|fee|rating|age|minutes", k):
        return 0
    if re.search(r"(^id$|_id$)", k):
        return re.sub(r"_id$", "", k) + "_123"
    if "email" in k:
        return "name@example.com"
    if re.search(r"phone|mobile", k):
        return "+91 90000 00000"
    if re.search(r"(s|list|items)$", k) and not re.search(r"status|address", k):
        return []
    return "text"


def sample_json(fields: List[str]) -> Dict[str, Any]:
    """Example object for a list of field names."""
    return {re.split(r"[:\s(]", str(f), maxsplit=1)[0]: sample_for(f) for f in fields or []}


def _pattern(path: str) -> re.Pattern:
    """An API path as a regex: {id} or :id segments match any one segment."""
    parts = [r"[^/]+" if re.fullmatch(r"\{[^}]*\}|:\w+", p) else re.escape(p) for p in path.strip("/").split("/")]
    return re.compile("^" + "/".join(parts) + "/?$")


def match(g: BuildingBeesEngine, method: str, path: str) -> Tuple[Optional[APINode], List[str]]:
    """The API on this board that answers METHOD /path, and the methods that path allows (for a 405)."""
    allowed = []
    for n in g.nodes.values():
        if isinstance(n, APINode) and n.path and _pattern(n.path).match(path.strip("/")):
            if (n.method or "GET").upper() == method.upper():
                return n, []
            allowed.append((n.method or "GET").upper())
    return None, allowed
