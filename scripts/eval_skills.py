"""Before-and-after test for one skill (talents/README.md rule 6): runs the same ideas with the skill off and on, on a
real engine, and prints a number that the skill is meant to move.

    .venv/bin/python -m scripts.eval_skills no-tech|four-states|who-can-do-what [nvidia|gemini]

Costs a few cents on Nemotron. Single runs are noisy: read the numbers as a direction, and repeat if close.
"""

import re
import sys

import httpx
from fastapi.testclient import TestClient

from scripts.eval_questions import IDEAS
from src.api import server
from src.core import skills

DEMO = "https://buildingbees-nemotron-853213660594.asia-south1.run.app"
EXTRA = ["A tuition centre app in Pune: parents see attendance and test marks and pay monthly fees by UPI.",
         "A dog walking app in Bangalore: owners book a walker by the hour, see the walk live and pay by UPI."]
TECH = re.compile(r"\b(react|angular|vue|node(\.js)?|django|flask|fastapi|postgres(ql)?|mysql|mongo(db)?|firebase|supabase|"
                  r"redis|aws|azure|gcp|kubernetes|docker|graphql|rest api|stripe|razorpay|twilio|sendgrid|swift|kotlin|"
                  r"flutter|tailwind|next\.js)\b", re.I)
DEFAULT_STATE = {"loading": "Skeleton loading state", "empty": "Zero state / Empty placeholder",
                 "error": "Full-page or contextual error container"}
ROLES = re.compile(r"\b(owner|admin|member|visitor|public|teacher|parent|student|buyer|seller|client|advisor|driver|dispatcher)\b", re.I)
NODE = {"no-tech": skills.NO_TECH, "four-states": skills.FOUR_STATES, "who-can-do-what": skills.WHO_CAN}


def graph(c, h):
    return c.get("/api/graph", headers=h).json()


def measure_no_tech(c, engine, n):
    """Technology names in flows, steps, features and questions (lower is better)."""
    h = {"X-Board": f"sk-{n}"}
    server.boards.pop(h["X-Board"], None)
    c.post(f"/api/ingest-prd?engine={engine}", json={"prd_markdown": IDEAS[n % 4] if n < 4 else EXTRA[n - 4]}, headers=h)
    g = graph(c, h)
    text = " ".join([f"{x['title']} {' '.join(x['metadata'].get('steps', []))}" for x in g["nodes"] if x["layer"] == "FLOW"] +
                    [f"{f['name']} {f.get('why', '')}" for f in g.get("features", [])] +
                    [x["question_text"] for x in g["nodes"] if x["layer"] == "QUESTION"])
    return {"tech_mentions": len(TECH.findall(text)), "questions": sum(x["layer"] == "QUESTION" for x in g["nodes"])}


def measure_four_states(c, engine, n):
    """Of the screens that show a list or a picture, how many carry their own words for loading, empty and error."""
    h = {"X-Board": f"sk-{n}"}
    server.boards.pop(h["X-Board"], None)
    c.post(f"/api/ingest-prd?engine={engine}", json={"prd_markdown": EXTRA[n % 2]}, headers=h)
    c.post(f"/api/expand?engine={engine}", headers=h)
    g = graph(c, h)
    need = [x for x in g["nodes"] if x["layer"] == "SCREEN" and {e.get("kind") for e in x["metadata"].get("elements", [])} & {"list", "image"}]
    own = sum(1 for x in need for k in DEFAULT_STATE if x["states"].get(k) and x["states"][k] != DEFAULT_STATE[k])
    return {"screens_with_list_or_image": len(need), "own_state_texts": own, "of": 3 * len(need)}


def measure_who_can(c, engine, n):
    """Schema tables whose access line names who may read and who may change (higher is better)."""
    h = {"X-Board": f"sk-{n}"}
    server.boards.pop(h["X-Board"], None)
    demo = httpx.get(DEMO + "/api/graph", headers={"X-Board": "videotest-20oct"}, timeout=60).json()  # a board with screens
    c.post("/api/restore", json=demo, headers=h)
    c.post(f"/api/docs?engine={engine}", headers=h)
    tables = (graph(c, h).get("docs") or {}).get("tables", [])
    good = [t for t in tables if len(set(m.lower() for m in ROLES.findall(t.get("access", "")))) >= 2
            and re.search(r"read|see|view", t.get("access", ""), re.I) and re.search(r"write|change|edit|create|delete|update", t.get("access", ""), re.I)]
    return {"tables": len(tables), "tables_with_clear_access": len(good)}


MEASURE = {"no-tech": (measure_no_tech, 6), "four-states": (measure_four_states, 2), "who-can-do-what": (measure_who_can, 1)}


def main(name, engine="nvidia"):
    fn, runs = MEASURE[name]
    c = TestClient(server.app)
    for label, on in (("OFF", False), ("ON", True)):
        skills.ENABLED.clear()
        if on:
            skills.ENABLED.add(NODE[name])  # off by default in the product, so OFF is what runs today
        rows = [fn(c, engine, i) for i in range(runs)]
        total = {k: sum(r[k] for r in rows) for k in rows[0]}
        print(f"{name} {label}: {total}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "nvidia")
