"""Schemas and prompts shared by every model engine (Gemini, NVIDIA)."""

from typing import List

from pydantic import BaseModel


# ---- Structured output schemas (what Gemini must return) ----

class XUser(BaseModel):
    id: str
    title: str
    description: str


class XFlow(BaseModel):
    id: str
    title: str
    goal: str
    user_id: str


class XScreen(BaseModel):
    id: str
    title: str
    flow_id: str
    description: str
    loading_state: str
    empty_state: str
    error_state: str


class XCTA(BaseModel):
    id: str
    label: str
    screen_id: str
    api_ids: List[str]
    success_screen_id: str
    failure_screen_id: str


class XAPI(BaseModel):
    id: str
    method: str
    path: str
    service: str
    vendor: str
    timeout_ms: int


class XQuestion(BaseModel):
    target_id: str
    category: str  # FRONTEND | BACKEND | DESIGN | TESTER | PM | COMPLIANCE
    question: str
    is_blocking: bool
    suggested_options: List[str]


class SpecExtract(BaseModel):
    product_name: str
    users: List[XUser]
    flows: List[XFlow]
    screens: List[XScreen]
    ctas: List[XCTA]
    apis: List[XAPI]
    questions: List[XQuestion]


class QuestionList(BaseModel):
    questions: List[XQuestion]


INGEST_PROMPT = """You are the BuildingBees information architect. Turn the product spec below into a
typed dependency graph: User -> Flow -> Screen -> CTA -> API.

Rules:
- Use short UPPER_SNAKE ids (e.g. W01_LOGIN, CTA_W01_SUBMIT, API_AUTH_LOGIN). Every reference must point to an id you defined.
- Every screen needs loading, empty and error states. If the spec does not say, write "UNSPECIFIED".
- Every CTA lists the APIs it calls and where it goes on success and on failure (a screen id, or "" if unknown).
- If the spec leaves a timeout unstated, use timeout_ms 0. If vendor is unknown use "".
- Assumption is not approval: never invent business rules. Wherever the spec is silent on something an
  engineer would need (failure paths, timeouts, retries, empty states, validation, permissions), add a question
  targeted at the exact node id. Mark it blocking if code cannot be written safely without the answer.
- Keep it to the 1-3 most important flows and at most 12 screens.

SPEC:
"""

INTERROGATE_PROMPT = """You are the BuildingBees Socratic Question Engine. Assumption is not approval.
Review this one spec node and its neighbours. List 2-4 questions an engineer would have to guess at
if they built it today: missing failure paths, timeouts, retries, idempotency, empty/error states,
validation, race conditions. Do not repeat the already-asked questions. Target every question at
node id "{node_id}". Mark blocking only if code cannot be written safely without the answer.

NODE AND NEIGHBOURS (JSON):
{context}

ALREADY ASKED:
{asked}
"""
