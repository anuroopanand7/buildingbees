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
    FLOWS_PROMPT, FlowsExtract, INGEST_PROMPT, INTERROGATE_PROMPT, QuestionList, Reaction, SpecExtract, XAPI, XCTA, XFlow, XQuestion, XScreen, XUser,
)

DEFAULT_MODEL = "gemini-3.8-flash"  # newest Flash on the free tier (checked 17 Oct 2026)
# Each model has its own free daily quota, so a long chain keeps the bees answering when one runs out
# (17 Oct: gemini-3.5-flash hit its daily limit mid-demo while 3.8 still answered).
FALLBACK_MODELS = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-3.5-flash-lite"]


class EngineNotConfigured(RuntimeError):
    pass


class GoogleGeminiAdapter:
    key = "gemini"
    label = "Google Gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._client = None

    @property
    def enabled(self) -> bool:
        """True when a Gemini API key is set."""
        return bool(self.api_key)

    def _generate(self, contents, schema):
        """Calls Gemini for structured JSON matching `schema`, falling over across models and retrying once after a pause when Gemini is busy."""
        if not self.enabled:
            raise EngineNotConfigured("GEMINI_API_KEY is not set")
        from google import genai
        from google.genai import types

        if self._client is None:
            # 45 s per attempt: a slow or overloaded model must fail over, not hang the visitor.
            self._client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=45_000))
        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema, temperature=0.2,
        )
        resp, last_error = None, None
        for attempt in range(2):  # a busy spell often passes in seconds: one more round after a short pause
            if attempt:
                time.sleep(4)
            for model in dict.fromkeys([self.model, *FALLBACK_MODELS]):
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

    def interrogate(self, node_id: str, context_json: str, asked: List[str]) -> List[XQuestion]:
        """Looks for further product questions on one screen, button or API."""
        prompt = INTERROGATE_PROMPT.format(
            node_id=node_id, context=context_json, asked="\n".join(f"- {q}" for q in asked) or "(none)"
        )
        result = self._generate([prompt], QuestionList)
        for q in result.questions:
            q.target_id = node_id
        return result.questions
