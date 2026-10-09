"""
Google Gemini adapter.
1. Spec ingestion: PRD text or PDF -> typed BuildingBees graph (Gemini structured output).
2. Socratic interrogation: one node + its neighbours -> blocking questions.
With no GEMINI_API_KEY set, `enabled` is False and callers must say so; nothing is faked.
"""

import os
from typing import List, Optional

from src.adapters.spec_prompts import (  # noqa: F401  (re-exported for callers)
    INGEST_PROMPT, INTERROGATE_PROMPT, QuestionList, SpecExtract, XAPI, XCTA, XFlow, XQuestion, XScreen, XUser,
)

DEFAULT_MODEL = "gemini-3.7-flash"


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
            self._client = genai.Client(api_key=self.api_key)
        resp = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )
        if resp.parsed is None:
            return schema.model_validate_json(resp.text)
        return resp.parsed

    def extract_spec(self, text: str = "", pdf_bytes: Optional[bytes] = None) -> SpecExtract:
        contents = [INGEST_PROMPT + (text or "(see attached PDF)")]
        if pdf_bytes:
            from google.genai import types
            contents.append(types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"))
        return self._generate(contents, SpecExtract)

    def interrogate(self, node_id: str, context_json: str, asked: List[str]) -> List[XQuestion]:
        prompt = INTERROGATE_PROMPT.format(
            node_id=node_id, context=context_json, asked="\n".join(f"- {q}" for q in asked) or "(none)"
        )
        result = self._generate([prompt], QuestionList)
        for q in result.questions:
            q.target_id = node_id
        return result.questions
