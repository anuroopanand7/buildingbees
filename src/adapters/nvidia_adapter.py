"""
NVIDIA adapter: Nemotron through any OpenAI-compatible endpoint.
Default endpoint is Nebius Token Factory, which the Nebius x NVIDIA hackathon requires. Set NVIDIA_BASE_URL
and NVIDIA_MODEL from the Token Factory dashboard; any OpenAI-compatible endpoint serving Nemotron works.
Same two jobs as the Gemini adapter, with the same output schemas, so the graph code
does not care which engine ran. PDFs are converted to text first (no multimodal input).
"""

import io
import json
import os
import re
from typing import List, Optional

import httpx

from src.adapters.gemini_adapter import EngineNotConfigured
from src.adapters.spec_prompts import (
    FLOWS_PROMPT, FlowsExtract, INGEST_PROMPT, INTERROGATE_PROMPT, QuestionList, Reaction, SpecExtract, XQuestion,
)

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"  # the hackathon requires Nebius Token Factory
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"  # of the four Nemotron models on Token Factory (11 Oct 2026): Lightning is quicker but misses vague answers
# Drawing every screen, button and API from the agreed flows is the one heavy reasoning job, so it goes to
# the largest Nemotron. Everything the founder waits on between answers stays on the fast one.
DEFAULT_HEAVY_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"


def pdf_to_text(data: bytes) -> str:
    """Nemotron takes text only, so a PDF is turned into its text first."""
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)


def _first_json_object(text: str) -> str:
    """Cuts the first complete JSON object out of a reply that may have text around it."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Model reply contained no JSON object")
    return text[start:end + 1]


class NvidiaNemotronAdapter:
    key = "nvidia"
    label = "NVIDIA Nemotron"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "")
        # `or`, not a getenv default: .env ships these two as empty lines, and empty must mean "use the default".
        self.model = model or os.getenv("NVIDIA_MODEL") or DEFAULT_MODEL
        self.heavy_model = os.getenv("NVIDIA_HEAVY_MODEL") or DEFAULT_HEAVY_MODEL
        self.base_url = (base_url or os.getenv("NVIDIA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    @property
    def enabled(self) -> bool:
        """True when an NVIDIA (Nebius Token Factory) API key is set."""
        return bool(self.api_key)

    def _generate(self, prompt: str, schema, model: Optional[str] = None):
        """Calls Nemotron with the schema in the prompt and validates the JSON; one retry with the validation error when it does not fit."""
        if not self.enabled:
            raise EngineNotConfigured("NVIDIA_API_KEY is not set")
        instructions = (
            prompt
            + "\n\nReply with ONLY one JSON object matching this JSON Schema, no prose:\n"
            + json.dumps(schema.model_json_schema())
        )
        messages = [
            {"role": "system", "content": "/no_think"},
            {"role": "user", "content": instructions},
        ]
        last_error = None
        for _ in range(2):  # one retry when the reply is not valid JSON for the schema
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                # Thinking off: left on, Nemotron 3 spends the whole token budget reasoning and the JSON is cut short.
                json={"model": model or self.model, "messages": messages, "temperature": 0.2, "max_tokens": 8192,
                      "chat_template_kwargs": {"enable_thinking": False}},
                timeout=180,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"] or ""
            try:
                out = schema.model_validate_json(_first_json_object(content))
                self.last_model = model or self.model
                return out
            except Exception as e:
                last_error = e
                messages += [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"That was not valid for the schema ({e}). Reply with only the corrected JSON."},
                ]
        raise ValueError(f"Nemotron did not return valid JSON: {last_error}")

    def extract_spec(self, text: str = "", pdf_bytes: Optional[bytes] = None) -> SpecExtract:
        """Draws screens, buttons and APIs from the agreed flows and decisions (stage two), on the heavy model."""
        if pdf_bytes:
            text = pdf_to_text(pdf_bytes)
        return self._generate(INGEST_PROMPT + text[:60000], SpecExtract, model=self.heavy_model)

    def extract_flows(self, text: str = "", pdf_bytes: Optional[bytes] = None,
                      image: Optional[tuple] = None) -> FlowsExtract:
        """Turns an idea or PDF into users, flows, branches and the first questions (stage one)."""
        if image:
            raise ValueError("Nemotron reads text only here; switch to Google Gemini to map a photo of a sketch")
        if pdf_bytes:
            text = pdf_to_text(pdf_bytes)
        return self._generate(FLOWS_PROMPT + text[:60000], FlowsExtract)

    def react(self, prompt: str) -> Reaction:
        """A bee reads one answer: a sharper follow-up if it is vague, otherwise changes to the board."""
        return self._generate(prompt, Reaction)

    def interrogate(self, node_id: str, context_json: str, asked: List[str]) -> List[XQuestion]:
        """Looks for further product questions on one screen, button or API."""
        prompt = INTERROGATE_PROMPT.format(
            node_id=node_id, context=context_json, asked="\n".join(f"- {q}" for q in asked) or "(none)"
        )
        result = self._generate(prompt, QuestionList)
        for q in result.questions:
            q.target_id = node_id
        return result.questions
