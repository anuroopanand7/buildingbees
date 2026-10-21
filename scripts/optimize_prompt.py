"""Self-improving prompt for Nemotron: tunes the flows prompt against yes/no checks, one small edit at a time.

Nebius Token Factory cannot fine-tune Nemotron, so this is how we adapt it to our job (idea: the "Self-Improving
Agent Skills" loop in Shubhamsaboo/awesome-llm-apps, after Karpathy's autoresearch; found by BSR, 21 Oct 2026):

    1. Executor: Super VL drafts the flows for 6 sample ideas with the current prompt; 8 yes/no checks score each.
    2. Analyst and mutator (one Super call): read the failures, pick ONE strategy (add a constraint, add an example,
       add an edge case, restructure) and return ONE edit: an exact passage of the prompt and its replacement.
    3. Re-run. Keep the edit only if the score rises, else revert. Repeat for N rounds.
    4. Re-score the winner and the original once more, so a lucky round is not mistaken for a better prompt.

The winner is saved to src/adapters/tuned/flows_nemotron.txt, which only the Nemotron adapter reads; Gemini keeps
the shared prompt. The raw model output is scored (before the server's own filters), so this measures the prompt.

    .venv/bin/python -m scripts.optimize_prompt [rounds]
Costs about $0.02 a round on Token Factory; stops early if the spend passes MAX_SPEND.
"""

import json
import os
import re
import sys
import time
from typing import List

from pydantic import BaseModel

from src.adapters import nvidia_adapter as nv
from src.adapters.spec_prompts import FLOWS_PROMPT, FlowsExtract
from src.api.server import audience
from src.core.ingest import STANDARD

IDEAS = [
    "A platform where AI agents post gigs and humans claim those gigs, do the work and get paid. Only AI agents can post gigs.",
    "A B2B tool where clients book and pay for consultations with advisors in a firm.",
    "An internal tool for a logistics company: drivers upload proof of delivery photos and dispatchers approve them.",
    "A SaaS dashboard where a marketing team connects their ad accounts and gets a weekly spend report by email.",
    "A tuition centre app in Pune: parents see attendance and test marks, pay monthly fees, and get a message when the child misses class.",
    "A dog walking app in Bangalore: owners book a walker by the hour, see the walk live on a map, and pay by UPI.",
]
RISKY = re.compile(r"\b(pay|paid|payment|book|upload|approve|reject|submit|claim|verify|check|send|sign|order|accept)\w*", re.I)
MAX_SPEND = 0.40  # US dollars for one run of this script
OUT = os.path.join(os.path.dirname(__file__), "..", "src", "adapters", "tuned", "flows_nemotron.txt")
LOG = os.path.join(os.path.dirname(__file__), "..", "docs", "prompt_tuning_log.md")


def words(t: str) -> set:
    """Content words, for spotting two questions that ask the same thing."""
    return set(re.findall(r"[a-z]+", t.lower())) - {"the", "a", "an", "to", "of", "and", "or", "do", "we", "is", "it",
                                                    "for", "should", "what", "how", "can", "be", "in", "on", "with"}


def checks(x: FlowsExtract) -> dict:
    """The 8 yes/no checks for one idea's draft. True means it passed."""
    qs = x.questions
    ids = {u.id for u in x.users} | {f.id for f in x.flows}
    texts = [q.question for q in qs]
    dup = any(len(words(a) & words(b)) / max(1, len(words(a) | words(b))) >= 0.5
              for i, a in enumerate(texts) for b in texts[:i])
    return {
        "4 to 12 questions": 4 <= len(qs) <= 12,
        "no standard-detail questions": not any(STANDARD.search(t) for t in texts),
        "no near-duplicate questions": not dup,
        "at least 2 flows": len(x.flows) >= 2,
        # only flows with a step that can fail need a split; a "view the report" flow has nothing to split on
        "risky flows have a failure split": all(f.branches for f in x.flows if RISKY.search(" ".join(f.steps))),
        "blocking questions offer 2+ options": all(len(q.suggested_options) >= 2 for q in qs if q.is_blocking),
        "questions point at real users or flows": all(q.target_id in ids for q in qs),
        "features listed and linked to flows": bool(x.features) and all(set(f.flow_ids) <= ids and f.flow_ids for f in x.features),
    }


def evaluate(engine: nv.NvidiaNemotronAdapter, prompt: str) -> tuple:
    """Runs every idea with this prompt; returns (passed, total, failures as text)."""
    passed, total, fails = 0, 0, []
    for idea in IDEAS:
        try:
            x = engine._generate(prompt + audience("solo") + "\n\nTHE IDEA:\n" + idea, FlowsExtract, model=nv.FLOWS_MODEL)
        except Exception as e:  # a draft that never parses fails every check
            total += 8; fails.append(f"- {idea[:60]}: no valid JSON ({str(e)[:120]})"); continue
        for name, ok in checks(x).items():
            total += 1; passed += ok
            if not ok:
                fails.append(f"- {idea[:60]}: FAILED {name}")
    return passed, total, "\n".join(fails)


class Edit(BaseModel):
    """One surgical change to the prompt, chosen by the analyst."""
    diagnosis: str
    strategy: str  # add_constraint | add_example | add_edge_case | restructure
    start_line: int  # first numbered line of the prompt to replace; 0 means add new_text at the end
    end_line: int    # last line to replace (inclusive); equal to start_line for a one-line edit
    new_text: str


MUTATE = """You improve a prompt that a model uses to draft user flows and product questions from a founder's idea.
Below are the prompt and the checks its drafts failed. Diagnose the most common root cause, pick ONE strategy
(add_constraint, add_example, add_edge_case or restructure) and make ONE small edit: the prompt's lines are numbered;
give start_line and end_line of the lines to replace and new_text to put there (or start_line 0 to add a short rule at
the end). Do not include the line numbers in new_text.
Keep every existing rule unless the edit is that rule. Plain English, no em dashes. Edits already tried and rejected:
{tried}

FAILED CHECKS:
{fails}

THE PROMPT:
<<<
{numbered}
>>>"""


def main(rounds: int) -> None:
    """Baseline, N rounds of edit and re-score, then a confirmation run; saves the winner and a log."""
    eng = nv.NvidiaNemotronAdapter()
    start = time.strftime("%Y-%m-%d %H:%M")
    best = FLOWS_PROMPT
    p, t, fails = evaluate(eng, best)
    base = (p, t)
    log = [f"# Prompt tuning log ({start})\n", f"Baseline: {p}/{t} checks passed. Failures:\n{fails}\n"]
    print(log[-1], flush=True)
    tried: List[str] = []
    for r in range(1, rounds + 1):
        if eng.spent_today > MAX_SPEND:
            log.append(f"Stopped before round {r}: spend ${eng.spent_today:.3f} passed ${MAX_SPEND}.\n"); break
        try:
            lines = best.split("\n")
            numbered = "\n".join(f"{i + 1:3d}| {ln}" for i, ln in enumerate(lines))
            e = eng._generate(MUTATE.format(tried="\n".join(tried) or "(none)", fails=fails or "(none)", numbered=numbered),
                              Edit, model=nv.DEFAULT_MODEL)
        except Exception as ex:
            log.append(f"Round {r}: no usable edit ({str(ex)[:100]}).\n"); continue
        if e.start_line == 0:
            cand = best.rstrip() + "\n" + e.new_text.strip() + "\n"
        elif 1 <= e.start_line <= e.end_line <= len(lines):
            cand = "\n".join(lines[:e.start_line - 1] + e.new_text.rstrip("\n").split("\n") + lines[e.end_line:])
        else:
            tried.append(f"- {e.strategy}: lines {e.start_line}-{e.end_line} out of range"); log.append(f"Round {r}: line range out of the prompt, skipped.\n"); continue
        lost = words(" ".join(lines[e.start_line - 1:e.end_line])) - words(e.new_text) if e.start_line else set()
        if len(lost) > 8:  # an edit may sharpen a rule, never quietly drop guidance (run 2 lost "at most 3 branches")
            tried.append(f"- {e.strategy}: dropped existing guidance ({', '.join(sorted(lost)[:6])})")
            log.append(f"Round {r}: edit would delete existing guidance ({len(lost)} words), skipped.\n"); continue
        cp, ct, cfails = evaluate(eng, cand)
        kept = cp > p
        log.append(f"Round {r}: {e.strategy}: {e.diagnosis[:160]}\n  edit: {e.new_text[:200]!r}\n  score {cp}/{ct} vs {p}/{t}: {'KEPT' if kept else 'reverted'}. Spend so far ${eng.spent_today:.3f}.\n")
        print(log[-1], flush=True)
        if kept:
            best, p, t, fails = cand, cp, ct, cfails
        else:
            tried.append(f"- {e.strategy}: {e.new_text[:80]}")
    if best != FLOWS_PROMPT:  # a second look, so one lucky run does not pick the prompt
        bp, bt, _ = evaluate(eng, best)
        op, ot, _ = evaluate(eng, FLOWS_PROMPT)
        log.append(f"Confirmation: tuned {bp}/{bt}, original {op}/{ot}.\n")
        if bp > op:
            os.makedirs(os.path.dirname(OUT), exist_ok=True)
            open(OUT, "w").write(best)
            log.append(f"Saved the tuned prompt to src/adapters/tuned/flows_nemotron.txt.\n")
        else:
            log.append("Not saved: the tuned prompt did not beat the original on the confirmation run.\n")
    log.append(f"Baseline {base[0]}/{base[1]}. Total spend ${eng.spent_today:.3f}.\n")
    print("".join(log[-3:]))
    with open(LOG, "a") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
