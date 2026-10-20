"""Question-quality check for the bees: runs sample ideas through the real engine and scores the questions.

Free stand-in for fine-tuning. Run it after every prompt change and compare the numbers.
    .venv/bin/python scripts/eval_questions.py [gemini|nvidia]

It flags questions that ask about details with an industry-standard answer (Ponna's 16 Oct test: 70+
questions, mostly timeouts, double taps and identity checks), near-duplicates, and the total asked.
Uses about 2 model calls per idea.
"""

import re
import sys

from fastapi.testclient import TestClient

from src.api import server

IDEAS = [
    "A platform where AI agents post gigs and humans claim those gigs, do the work and get paid. Only AI agents can post gigs.",
    "A B2B tool where clients book and pay for consultations with advisors in a firm.",
    "An internal tool for a logistics company: drivers upload proof of delivery photos and dispatchers approve them.",
    "A SaaS dashboard where a marketing team connects their ad accounts and gets a weekly spend report by email.",
]
from src.core.ingest import STANDARD  # the same list the server filters with


def words(t):
    return set(re.findall(r"[a-z]+", t.lower())) - {"the", "a", "an", "to", "of", "and", "or", "do", "we", "is", "it", "for", "should", "what", "how"}


def run(engine: str):
    c = TestClient(server.app)
    totals = {"asked": 0, "standard": 0, "dupes": 0}
    for i, idea in enumerate(IDEAS):
        h = {"X-Board": f"eval-{engine}-{i}"}
        server.boards.pop(h["X-Board"], None)
        r = c.post(f"/api/ingest-prd?engine={engine}", json={"prd_markdown": idea}, headers=h)
        if r.status_code != 200:
            print(f"[{i}] ingest failed: {r.status_code} {r.text[:200]}"); continue
        r = c.post(f"/api/expand?engine={engine}", headers=h)
        if r.status_code != 200:
            print(f"[{i}] screens failed: {r.status_code} {r.text[:200]}"); continue
        qs = [n for n in c.get("/api/graph", headers=h).json()["nodes"]
              if n["layer"] == "QUESTION" and not n["metadata"].get("default")]
        std = [q for q in qs if STANDARD.search(q["question_text"])]
        dup = [b for j, b in enumerate(qs) for a in qs[:j]
               if len(words(a["question_text"]) & words(b["question_text"])) / max(1, len(words(a["question_text"]) | words(b["question_text"]))) >= 0.5]
        totals["asked"] += len(qs); totals["standard"] += len(std); totals["dupes"] += len(dup)
        print(f"\n[{i}] {idea[:70]}...\n    asked {len(qs)}, standard-topic {len(std)}, near-duplicate {len(dup)}")
        for q in std + dup:
            print(f"    flag: {q['category']}: {q['question_text']}")
    n = len(IDEAS)
    print(f"\nTOTAL over {n} ideas: {totals['asked']} asked ({totals['asked'] / n:.1f} per idea), "
          f"{totals['standard']} on standard topics, {totals['dupes']} near-duplicates")
    print("Targets: at most 12 per idea, 0 standard-topic, 0 near-duplicates.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "gemini")
