"""Beta testers' feedback board, built the way AIRs does it.

1. Anyone can report a bug or an idea: the part of the product, what happened, up to 3 screenshots.
2. Every report is public to testers: they upvote and comment, so the most wanted fixes rise to the top.
3. Statuses: new, in_progress, shelved, fix_deployed, resolved. Only the team (ADMIN_UIDS) changes them,
   and team comments show as official.
4. When a fix is deployed, testers press "Confirm fixed"; three confirmations resolve the report.

Reports live in Firestore collection `feedback` on Cloud Run, and in memory locally and in tests.
A tester is identified by their Firebase uid when signed in, otherwise by a random browser id sent
in the X-Tester header (good enough for a beta; it can be gamed by clearing storage).
"""

import datetime
import os
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/feedback")

SECTIONS = ["Board and flows", "Bee questions", "Screens", "Brief and sign-off", "Team and roles",
            "Sign-in and my boards", "Speed or errors", "General or other"]
STATUSES = ["new", "in_progress", "shelved", "fix_deployed", "resolved"]
CONFIRMS_TO_RESOLVE = 3
MAX_SHOTS, MAX_SHOT_CHARS = 3, 340_000  # a downscaled JPEG as a data URL; keeps a report under Firestore's 1 MB

_mem: Dict[str, Dict[str, Any]] = {}  # local runs and tests


def _col():
    """The Firestore collection, or None when the app runs locally (boards and feedback then stay in memory)."""
    from src.api import server  # late import: server imports this module
    db = getattr(server, "_db", None) if getattr(server, "_store", None) is not None else None
    return db.collection("feedback") if db is not None else None


def _get(fid: str) -> Dict[str, Any]:
    """One report, or 404."""
    col = _col()
    if col is None:
        item = _mem.get(fid)
    else:
        snap = col.document(fid).get()
        item = snap.to_dict() if snap.exists else None
    if not item:
        raise HTTPException(status_code=404, detail="No such report")
    return item


def _put(item: Dict[str, Any]) -> None:
    """Saves one report."""
    col = _col()
    if col is None:
        _mem[item["id"]] = item
    else:
        col.document(item["id"]).set(item)


def _tester(authorization: str, tester: str) -> str:
    """Who is acting: the signed-in uid if there is one, else the browser's random tester id."""
    from src.api import server
    uid = server._uid(authorization or "")
    if uid:
        return "u:" + uid
    if not tester or len(tester) > 64:
        raise HTTPException(status_code=400, detail="Missing tester id")
    return "t:" + tester


def _is_team(authorization: str) -> bool:
    """True for the BuildingBees team: signed-in uids listed in the ADMIN_UIDS environment variable."""
    from src.api import server
    uid = server._uid(authorization or "")
    return bool(uid) and uid in {u.strip() for u in os.getenv("ADMIN_UIDS", "").split(",") if u.strip()}


def _public(item: Dict[str, Any], me: str) -> Dict[str, Any]:
    """A report as the browser sees it: counts instead of voter ids, and whether this tester voted or confirmed."""
    out = {k: v for k, v in item.items() if k not in ("voters", "confirmers", "reporter_key")}
    out.update(votes=len(item["voters"]), voted=me in item["voters"], confirms=len(item["confirmers"]),
               confirmed=me in item["confirmers"], mine=item.get("reporter_key") == me)
    return out


def _now() -> str:
    """UTC timestamp for reports and comments."""
    return datetime.datetime.utcnow().isoformat()


class NewReport(BaseModel):
    section: str = "General or other"
    description: str
    name: str = ""
    board: str = ""
    screenshots: List[str] = []


class NewComment(BaseModel):
    text: str
    name: str = ""


class NewStatus(BaseModel):
    status: str


@router.get("")
def list_reports(authorization: str = Header(""), x_tester: str = Header("")) -> Dict[str, Any]:
    """Every report, open ones first and the most voted at the top; resolved ones sink to the end."""
    me = _tester(authorization, x_tester) if (authorization or x_tester) else ""
    col = _col()
    items = list(_mem.values()) if col is None else [d.to_dict() for d in col.stream()]
    items.sort(key=lambda i: (i["status"] == "resolved", -len(i["voters"]), i["created"]), reverse=False)
    return {"sections": SECTIONS, "reports": [_public(i, me) for i in items], "team": _is_team(authorization)}


@router.post("")
def create_report(r: NewReport, authorization: str = Header(""), x_tester: str = Header("")) -> Dict[str, Any]:
    """Files a new report. The reporter's vote is counted, as on AIRs."""
    me = _tester(authorization, x_tester)
    text = r.description.strip()
    if len(text) < 3:
        raise HTTPException(status_code=400, detail="Say what happened or what you would like")
    shots = [s for s in r.screenshots[:MAX_SHOTS] if s.startswith("data:image/") and len(s) <= MAX_SHOT_CHARS]
    if len(shots) != len(r.screenshots[:MAX_SHOTS]):
        raise HTTPException(status_code=400, detail="A screenshot was not an image or was too large")
    item = {"id": uuid.uuid4().hex[:12], "section": r.section if r.section in SECTIONS else SECTIONS[-1],
            "description": text[:2000], "name": r.name.strip()[:40] or "A tester", "board": r.board[:80],
            "screenshots": shots, "status": "new", "created": _now(), "reporter_key": me,
            "voters": [me], "confirmers": [], "comments": []}
    _put(item)
    return _public(item, me)


@router.post("/{fid}/vote")
def toggle_vote(fid: str, authorization: str = Header(""), x_tester: str = Header("")) -> Dict[str, Any]:
    """Upvotes a report, or takes the vote back."""
    me, item = _tester(authorization, x_tester), _get(fid)
    item["voters"] = [v for v in item["voters"] if v != me] if me in item["voters"] else item["voters"] + [me]
    _put(item)
    return _public(item, me)


@router.post("/{fid}/comment")
def add_comment(fid: str, c: NewComment, authorization: str = Header(""), x_tester: str = Header("")) -> Dict[str, Any]:
    """Adds a comment; the team's comments are marked official."""
    me, item = _tester(authorization, x_tester), _get(fid)
    if not c.text.strip():
        raise HTTPException(status_code=400, detail="The comment is empty")
    team = _is_team(authorization)
    item["comments"].append({"name": "BuildingBees team" if team else (c.name.strip()[:40] or "A tester"),
                             "text": c.text.strip()[:1000], "official": team, "at": _now()})
    _put(item)
    return _public(item, me)


@router.post("/{fid}/status")
def set_status(fid: str, s: NewStatus, authorization: str = Header(""), x_tester: str = Header("")) -> Dict[str, Any]:
    """The team moves a report along: new, in_progress, shelved, fix_deployed, resolved."""
    if not _is_team(authorization):
        raise HTTPException(status_code=403, detail="Only the BuildingBees team can change a status")
    if s.status not in STATUSES:
        raise HTTPException(status_code=400, detail="Unknown status")
    item = _get(fid)
    item["status"] = s.status
    if s.status == "fix_deployed":
        item["confirmers"] = []  # a new fix needs fresh confirmations
    _put(item)
    return _public(item, _tester(authorization, x_tester))


@router.post("/{fid}/confirm")
def confirm_fixed(fid: str, authorization: str = Header(""), x_tester: str = Header("")) -> Dict[str, Any]:
    """A tester confirms a deployed fix works; the third confirmation resolves the report."""
    me, item = _tester(authorization, x_tester), _get(fid)
    if item["status"] != "fix_deployed":
        raise HTTPException(status_code=400, detail="This report has no fix deployed yet")
    if me not in item["confirmers"]:
        item["confirmers"].append(me)
    if len(item["confirmers"]) >= CONFIRMS_TO_RESOLVE:
        item["status"] = "resolved"
    _put(item)
    return _public(item, me)
