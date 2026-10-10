"""
Google Gemini adapter.
1. Spec ingestion: PRD text or PDF -> typed BuildingBees graph (Gemini structured output).
2. Socratic interrogation: one node + its neighbours -> blocking questions.
With no GEMINI_API_KEY set, `enabled` is False and callers must say so; nothing is faked.
"""

import os
from typing import List, Optional

from src.adapters.spec_prompts import (  # noqa: F401  (re-exported for callers)
    FLOWS_PROMPT, FlowsExtract, INGEST_PROMPT, INTERROGATE_PROMPT, QuestionList, SpecExtract, XAPI, XCTA, XFlow, XQuestion, XScreen, XUser,
)

DEFAULT_MODEL = "gemini-3.5-flash"
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-flash-latest"]


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
        return bool(self.api_key)

    def _generate(self, contents, schema):
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
        for model in dict.fromkeys([self.model, *FALLBACK_MODELS]):
            try:
                resp = self._client.models.generate_content(model=model, contents=contents, config=config)
                self.last_model = model
                break
            except Exception as e:  # overloaded (503), rate limited (429) or timed out: try the next model
                last_error = e
                if not any(t in str(e) for t in ("503", "429", "404", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded", "imed out", "DEADLINE")):
                    raise
        if resp is None:
            raise RuntimeError(f"Gemini is busy right now, please try again in a minute. ({str(last_error)[:120]})")
        if resp.parsed is None:
            return schema.model_validate_json(resp.text)
        return resp.parsed

    def extract_spec(self, text: str = "", pdf_bytes: Optional[bytes] = None) -> SpecExtract:
        contents = [INGEST_PROMPT + (text or "(see attached PDF)")]
        if pdf_bytes:
            from google.genai import types
            contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))
        return self._generate(contents, SpecExtract)

    def extract_flows(self, text: str = "", pdf_bytes: Optional[bytes] = None) -> FlowsExtract:
        contents = [FLOWS_PROMPT + (text or "(see attached PDF)")]
        if pdf_bytes:
            from google.genai import types
            contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))
        return self._generate(contents, FlowsExtract)

    def interrogate(self, node_id: str, context_json: str, asked: List[str]) -> List[XQuestion]:
        prompt = INTERROGATE_PROMPT.format(
            node_id=node_id, context=context_json, asked="\n".join(f"- {q}" for q in asked) or "(none)"
        )
        result = self._generate([prompt], QuestionList)
        for q in result.questions:
            q.target_id = node_id
        return result.questions
