"""
Google Gemini adapter.
1. Spec ingestion: PRD text or PDF -> typed BuildingBees graph (Gemini structured output).
2. Socratic interrogation: one node + its neighbours -> blocking questions.
With no GEMINI_API_KEY set, `enabled` is False and callers must say so; nothing is faked.
"""

import time
import os
from typing import List, Optional

from src.adapters.spec_prompts import (  # noqa: F401  (re-exported for callers)
    FLOWS_PROMPT, FlowsExtract, PLAN_PROMPT, PlanExtract, INGEST_PROMPT, INTERROGATE_PROMPT, QuestionList, Reaction, SpecExtract, XAPI, XCTA, XFlow, XQuestion, XScreen, XUser,
)

DEFAULT_MODEL = "gemini-3.7-flash"  # strong and steady: 24 s on a full flow plan (17 Oct 2026)
# Each model has its own free quota (20 requests a day per model), so the chain keeps the bees answering when
# one is busy or spent. Strong Flash models only, newest after the default; no Flash-Lite (Roger, 18 Oct 2026:
# "lets not use lame models"). Pro models need a paid tier on this key, so they are not in the chain.
# 17 Oct measurements: 3.7-flash 24 s, flash-latest 23 s, 3.8-flash overloaded at the time. 18 Oct: 3-flash-preview
# timed out after 82 s on a full flow plan, so it is out.
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-flash-latest"]
# Emergency only (Roger, 18 Oct 2026): when every strong model is busy or out of its daily quota, Flash-Lite
# answers so a tester or judge never sees an error. The engine pill shows the model, so it is never hidden.
EMERGENCY_MODEL = "gemini-3.1-flash-lite"
# Agent Platform (Vertex AI) on our own Google Cloud project, billed to the Free Trial credit (18 Oct 2026:
# about Rs 28,800 left, a Free Trial account is never charged unless it is upgraded). It unlocks Pro and is
# what the AI Builder Cup judges look for ("ultimately you have to use agent platform"). Pro first; Gemini 4
# Argon is left out (80 s for one word on 18 Oct). Set GEMINI_VERTEX_PROJECT to turn it on.
VERTEX_MODELS = ["gemini-3.1-pro-preview", "gemini-3.8-flash", "gemini-3.7-flash"]
# Spend guard: at most this many Agent Platform calls a day; past it the free API key takes over.
VERTEX_DAILY_CAP = int(os.getenv("GEMINI_VERTEX_DAILY_CAP", "300"))


class EngineNotConfigured(RuntimeError):
    pass


class GoogleGeminiAdapter:
    key = "gemini"
    label = "Google Gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._client = None
        self.vertex_project = os.getenv("GEMINI_VERTEX_PROJECT", "")
        self.vertex_location = os.getenv("GEMINI_VERTEX_LOCATION", "global")
        self._vertex = None
        self._vertex_day, self._vertex_calls = "", 0  # the daily spend guard

    @property
    def enabled(self) -> bool:
        """True when a Gemini API key or an Agent Platform project is set."""
        return bool(self.api_key or self.vertex_project)

    def _vertex_ok(self) -> bool:
        """True while Agent Platform is on and today's call cap is not reached; counts the call."""
        if not self.vertex_project:
            return False
        day = time.strftime("%Y-%m-%d")
        if day != self._vertex_day:
            self._vertex_day, self._vertex_calls = day, 0
        if self._vertex_calls >= VERTEX_DAILY_CAP:
            return False
        self._vertex_calls += 1
        return True

    def _generate(self, contents, schema):
        """Calls Gemini for structured JSON matching `schema`, falling over across models and retrying once after a pause when Gemini is busy."""
        if not self.enabled:
            raise EngineNotConfigured("GEMINI_API_KEY is not set")
        from google import genai
        from google.genai import types

        if self._client is None and self.api_key:
            # 40 s per attempt: a full flow plan takes 15 to 25 s on a healthy model, so this only cuts off a stuck one
            # (17 Oct: 25 s cut off good answers and cascaded through the chain).
            self._client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=40_000))
        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema, temperature=0.2,
        )
        resp, last_error = None, None
        if self._vertex_ok():  # Agent Platform first: Pro, then strong Flash; 90 s, since Pro thinks longer
            if self._vertex is None:
                self._vertex = genai.Client(vertexai=True, project=self.vertex_project, location=self.vertex_location,
                                            http_options=types.HttpOptions(timeout=90_000))
            for model in VERTEX_MODELS:
                try:
                    resp = self._vertex.models.generate_content(model=model, contents=contents, config=config)
                    self.last_model = f"{model} (Agent Platform)"
                    break
                except Exception as e:  # busy, out of quota or slow: the next model, then the free API key
                    last_error = e
        if resp is not None:
            return resp.parsed if resp.parsed is not None else schema.model_validate_json(resp.text)
        if self._client is None:
            raise RuntimeError(f"Gemini is busy right now, please try again in a minute. ({str(last_error)[:120]})")
        for attempt in range(3):  # strong chain, the strong chain again after a pause, then the emergency model
            if attempt == 1:
                if "PerDay" in str(last_error):  # the day's quota is spent: waiting 4 s will not bring it back
                    continue
                time.sleep(4)
            chain = [EMERGENCY_MODEL] if attempt == 2 else list(dict.fromkeys([self.model, *FALLBACK_MODELS]))
            for model in chain:
                try:
                    resp = self._client.models.generate_content(model=model, contents=contents, config=config)
                    self.last_model = model
                    break
                except Exception as e:  # overloaded (503), rate limited (429) or timed out: try the next model
                    last_error = e
                    if not any(t in str(e) for t in ("503", "429", "404", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded", "imed out", "DEADLINE")):
                        raise
            if resp is not None:
                break
        if resp is None:
            raise RuntimeError(f"Gemini is busy right now, please try again in a minute. ({str(last_error)[:120]})")
        if resp.parsed is None:
            return schema.model_validate_json(resp.text)
        return resp.parsed

    def extract_spec(self, text: str = "", pdf_bytes: Optional[bytes] = None) -> SpecExtract:
        """Draws screens, buttons and APIs from the agreed flows and decisions (stage two)."""
        contents = [INGEST_PROMPT + (text or "(see attached PDF)")]
        if pdf_bytes:
            from google.genai import types
            contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))
        return self._generate(contents, SpecExtract)

    def extract_flows(self, text: str = "", pdf_bytes: Optional[bytes] = None,
                      image: Optional[tuple] = None) -> FlowsExtract:
        """Turns an idea, a PDF, or a photo of a sketch into users, flows, branches and the first questions (stage one).
        `image` is (bytes, mime type): a whiteboard, napkin or screenshot that Gemini reads with vision."""
        from google.genai import types
        note = ("\n(See the attached image: a photo or screenshot of the founder's own sketch. Read its boxes, arrows and "
                "labels as their draft user flow: keep what it shows, and ask about what it leaves out.)") if image else ""
        contents = [FLOWS_PROMPT + (text or "(see the attachment)") + note]
        if pdf_bytes:
            contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))
        if image:
            contents.append(types.Part.from_bytes(data=image[0], mime_type=image[1]))
        return self._generate(contents, FlowsExtract)

    def react(self, prompt: str) -> Reaction:
        """A bee reads one answer: a sharper follow-up if it is vague, otherwise changes to the board."""
        return self._generate([prompt], Reaction)

    def write_plan(self, board_json: str) -> PlanExtract:
        """Writes user stories with acceptance criteria, a feature list, a build order and a glossary from the board."""
        return self._generate([PLAN_PROMPT + board_json], PlanExtract)

    def interrogate(self, node_id: str, context_json: str, asked: List[str]) -> List[XQuestion]:
        """Looks for further product questions on one screen, button or API."""
        prompt = INTERROGATE_PROMPT.format(
            node_id=node_id, context=context_json, asked="\n".join(f"- {q}" for q in asked) or "(none)"
        )
        result = self._generate([prompt], QuestionList)
        for q in result.questions:
            q.target_id = node_id
        return result.questions
