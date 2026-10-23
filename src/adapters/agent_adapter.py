"""
Bring your own AI: the person's own agent (Claude Code, Cursor, Codex, any MCP client) does the thinking with its own
model and pays for it; BuildingBees supplies the prompts, the rules and the board. Nothing here calls a model.

How one bee call works with engine=agent (two HTTP calls, both on the normal endpoints):
1. The endpoint builds its prompt as usual and asks this adapter. No answer is waiting, so the adapter raises
   NeedAgent: HTTP 409 with the exact prompt and the JSON Schema the reply must match.
2. The agent's model writes that JSON and posts it to /api/agent/answer; the agent then repeats the same endpoint call.
   This time the adapter returns the stored answer, validated against the same Pydantic schema the Gemini and
   Nemotron engines use, so the board code cannot tell which engine ran.
"""

import json
from typing import Dict, List, Optional

from fastapi import HTTPException

from src.adapters.spec_prompts import (
    DOCS_PROMPT, DocsExtract, FlowsExtract, PlanExtract, INTERROGATE_PROMPT, QuestionList, Reaction, SpecExtract, XQuestion, FLOWS_PROMPT,
    INGEST_PROMPT, PLAN_PROMPT,
)

# One stored answer per board and per kind of call; an answer is used once.
SCHEMAS = {"docs": DocsExtract, "flows": FlowsExtract, "spec": SpecExtract, "react": Reaction, "plan": PlanExtract, "questions": QuestionList}


class NeedAgent(HTTPException):
    """The person's AI has to answer this prompt first. 409 so it never looks like success."""

    def __init__(self, kind: str, prompt: str):
        super().__init__(status_code=409, detail={
            "needs_agent": True, "kind": kind,
            "instructions": "Answer the prompt with ONE JSON object that matches the schema. POST it to "
                            "/api/agent/answer as {\"kind\": \"%s\", \"answer\": <your JSON>} with the same X-Board header, "
                            "then repeat the request you just made." % kind,
            "prompt": prompt, "schema": SCHEMAS[kind].model_json_schema()})


class AgentAdapter:
    key = "agent"
    label = "Your own AI"
    enabled = True  # no key needed: the person's agent brings the model
    model = "your own AI"

    def __init__(self):
        self.answers: Dict[str, Dict[str, str]] = {}  # board id -> kind -> raw JSON
        # shortcut: answers live in memory (Cloud Run max-instances 1, used within seconds); move to Firestore if the
        # service ever runs more than one instance.
        self.board = lambda: "default"  # the server points this at its current-board lookup

    def put(self, kind: str, answer) -> None:
        """Stores the agent's answer for this board, after checking it fits the schema (bad JSON fails here, early)."""
        raw = answer if isinstance(answer, str) else json.dumps(answer)
        if len(raw) > 300_000:  # a full board plan is well under this; anything bigger is a mistake or abuse
            raise ValueError("answer is too large (over 300 KB)")
        SCHEMAS[kind].model_validate_json(raw)  # raises a clear validation error for the agent to fix
        self.answers.setdefault(self.board(), {})[kind] = raw

    def _take(self, kind: str, prompt: str):
        """Returns the stored answer once, or asks the agent for it."""
        raw = self.answers.get(self.board(), {}).pop(kind, None)
        if raw is None:
            raise NeedAgent(kind, prompt)
        self.last_model = "your own AI"
        return SCHEMAS[kind].model_validate_json(raw)

    def extract_flows(self, text: str = "", pdf_bytes: Optional[bytes] = None, image=None) -> FlowsExtract:
        """Stage one, drawn by the person's AI. PDFs and photos stay with Gemini or Nemotron: an agent pastes text."""
        if pdf_bytes or image:
            raise HTTPException(status_code=400, detail="With your own AI, paste the idea as text.")
        return self._take("flows", FLOWS_PROMPT + text)

    def extract_spec(self, text: str = "", pdf_bytes: Optional[bytes] = None) -> SpecExtract:
        """Stage two: screens, buttons and APIs."""
        return self._take("spec", INGEST_PROMPT + text)

    def react(self, prompt: str) -> Reaction:
        """A round of answers and notes, applied to the board."""
        return self._take("react", prompt)

    def write_plan(self, board_text: str) -> PlanExtract:
        """User stories, features, build order, glossary."""
        return self._take("plan", PLAN_PROMPT + board_text)

    def write_docs(self, board_text: str) -> DocsExtract:
        """The TRD, design brief and schema."""
        return self._take("docs", DOCS_PROMPT + board_text)

    def interrogate(self, node_id: str, context_json: str, asked: List[str]) -> List[XQuestion]:
        """More questions on one screen, button or API."""
        prompt = INTERROGATE_PROMPT.format(node_id=node_id, context=context_json,
                                           asked="\n".join(f"- {q}" for q in asked) or "(none)")
        out = self._take("questions", prompt).questions
        for q in out:
            q.target_id = node_id
        return out
