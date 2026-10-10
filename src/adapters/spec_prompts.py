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
    step: int = 0  # 1-based step of the flow this is about; 0 = the whole flow, user, screen or API


class SpecExtract(BaseModel):
    product_name: str
    users: List[XUser]
    flows: List[XFlow]
    screens: List[XScreen]
    ctas: List[XCTA]
    apis: List[XAPI]
    questions: List[XQuestion]


class XFlowPlan(BaseModel):
    id: str
    title: str
    goal: str
    user_id: str
    steps: List[str]


class FlowsExtract(BaseModel):
    product_name: str
    users: List[XUser]
    flows: List[XFlowPlan]
    questions: List[XQuestion]


class XFlowUpdate(BaseModel):
    flow_id: str
    title: str
    goal: str
    steps: List[str]


class XUserUpdate(BaseModel):
    user_id: str
    title: str
    description: str


class XFieldUpdate(BaseModel):
    node_id: str
    field: str
    value: str


class Reaction(BaseModel):
    """What a bee does with one answer: push back if it is vague, otherwise change the board."""
    is_vague: bool
    note: str
    follow_up: List[XQuestion]
    flow_updates: List[XFlowUpdate]
    user_updates: List[XUserUpdate]
    field_updates: List[XFieldUpdate]


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

THE HIVE. Every question is asked by one bee. Set "category" to exactly one of:
- PM: who the user is, the goal, what is in and out of scope, how success is measured
- DESIGN: what the experience should feel like, what the user sees first, wording, accessibility
- FRONTEND: screen states, validation, what is kept when something fails, device and offline behaviour
- BACKEND: data, integrations, vendors, timeouts, retries, limits, cost
- TESTER: edge cases, abuse, what happens when it goes wrong, how we know it works
- COMPLIANCE: privacy, consent, medical, legal or money rules, who is liable
Spread the questions across at least four different bees when the input allows it.
Write each question the way a friendly colleague would ask it out loud: one short sentence, plain words,
no ids, no jargon the founder would not use. Suggested answers are short plain phrases.
If a question is about one step of a flow, set "step" to that step's number (1 = the first step); otherwise 0.

SPEC:
"""

FLOWS_PROMPT = """You are BuildingBees, a senior product manager. A founder has given you a spec or a rough idea.
Do NOT design screens, buttons or APIs yet. First agree the user flows.

1. List the users (1-3) and the user flows (1-4). Use short UPPER_SNAKE ids (USER_PATIENT, FLOW_CREATE_VIDEO).
2. For each flow write 3-7 plain-language steps: what the user does and what the product does in reply.
   Only include steps the input supports. Do not invent features.
3. Then ask what a senior PM would need answered before anyone draws a screen: exactly who the user is,
   what they bring in, what they get out, what is in and out of scope, what happens when it goes wrong,
   how we know it worked. Ask 4-8 questions, most important first. Target each at the flow id or user id
   it is about. Give 2-4 short suggested answers for each. Mark it blocking if the flow cannot be designed
   without the answer. Assumption is not approval: when the input is silent, ask, do not decide.

THE HIVE. Every question is asked by one bee. Set "category" to exactly one of:
- PM: who the user is, the goal, what is in and out of scope, how success is measured
- DESIGN: what the experience should feel like, what the user sees first, wording, accessibility
- FRONTEND: screen states, validation, what is kept when something fails, device and offline behaviour
- BACKEND: data, integrations, vendors, timeouts, retries, limits, cost
- TESTER: edge cases, abuse, what happens when it goes wrong, how we know it works
- COMPLIANCE: privacy, consent, medical, legal or money rules, who is liable
Spread the questions across at least four different bees when the input allows it.
Write each question the way a friendly colleague would ask it out loud: one short sentence, plain words,
no ids, no jargon the founder would not use. Suggested answers are short plain phrases.
If a question is about one step of a flow, set "step" to that step's number (1 = the first step); otherwise 0.

INPUT:
"""

INTERROGATE_PROMPT = """You are the BuildingBees Socratic Question Engine. Assumption is not approval.
Review this one spec node and its neighbours. List 2-4 questions an engineer would have to guess at
if they built it today: missing failure paths, timeouts, retries, idempotency, empty/error states,
validation, race conditions. Do not repeat the already-asked questions. Target every question at
node id "{node_id}". Mark blocking only if code cannot be written safely without the answer.

THE HIVE. Every question is asked by one bee. Set "category" to exactly one of:
- PM: who the user is, the goal, what is in and out of scope, how success is measured
- DESIGN: what the experience should feel like, what the user sees first, wording, accessibility
- FRONTEND: screen states, validation, what is kept when something fails, device and offline behaviour
- BACKEND: data, integrations, vendors, timeouts, retries, limits, cost
- TESTER: edge cases, abuse, what happens when it goes wrong, how we know it works
- COMPLIANCE: privacy, consent, medical, legal or money rules, who is liable
Spread the questions across at least four different bees when the input allows it.
Write each question the way a friendly colleague would ask it out loud: one short sentence, plain words,
no ids, no jargon the founder would not use. Suggested answers are short plain phrases.
If a question is about one step of a flow, set "step" to that step's number (1 = the first step); otherwise 0.

NODE AND NEIGHBOURS (JSON):
{context}

ALREADY ASKED:
{asked}
"""


REACT_PROMPT = """You are a bee on the BuildingBees product team. The founder has just answered one of your questions.
Decide what to do with the answer.

A. If the answer is vague, evasive or too broad to build from ("everyone", "all of them", "later", "not sure",
   "make it good", a restated question), set is_vague true, change nothing on the board, and ask exactly ONE
   sharper follow-up in follow_up: same category, same target_id and step, 2-4 concrete suggested answers,
   is_blocking true. Be warm about it. Example: "everyone" becomes "Pick the one person who needs this most".

B. Otherwise set is_vague false and apply the decision to the board. Change only what the answer implies.
   - Flows (the board is at the flows stage): return every flow that changes in flow_updates with its full new
     list of steps (add, reword, reorder or remove steps). If the answer changes who a user is, return it in
     user_updates. Keep every id exactly as given.
   - Screens (the board is at the screens stage): return field_updates as (node_id, field, value) using only
     these fields. SCREEN: description, states.loading, states.empty, states.error. CTA: label,
     target_screen_on_success, target_screen_on_failure, error_display_type, max_retries. API: method, path,
     service, vendor, timeout_ms, cache_ttl_seconds, idempotency_required. Numbers and true/false go in as text.
   - Leave follow_up empty unless the answer itself opens a new gap that blocks the build; then ask ONE question.
   Never invent a business rule the founder did not state.

note: one short friendly sentence, in the first person, saying what you did ("Got it, I added a pharmacist
review step before the video goes out." or "That is still a bit broad for me, so one more question.").
Follow-up questions follow the same rules as always: one short spoken sentence, plain words, no ids.
Leave any list you do not need empty.

STAGE: {stage}

THE BOARD (JSON):
{board}

DECISIONS SO FAR:
{decisions}

THE QUESTION ({category}, about {target}{step}):
{question}

THE FOUNDER'S ANSWER:
{answer}
"""
