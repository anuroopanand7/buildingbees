"""
NVIDIA adapter: Nemotron through any OpenAI-compatible endpoint.
Default is NVIDIA's API catalogue (build.nvidia.com). For the Nebius hackathon, point
NVIDIA_BASE_URL at Nebius AI Studio and use a Nemotron model id it serves.
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
    FLOWS_PROMPT, FlowsExtract, INGEST_PROMPT, INTERROGATE_PROMPT, QuestionList, SpecExtract, XQuestion,
)

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"


def pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)


def _first_json_object(text: str) -> str:
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
        self.model = model or os.getenv("NVIDIA_MODEL", DEFAULT_MODEL)
        self.base_url = (base_url or os.getenv("NVIDIA_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _generate(self, prompt: str, schema):
        if not self.enabled:
            raise EngineNotConfigured("NVIDIA_API_KEY is not set")
        instructions = (
            prompt
            + "\n\nReply with ONLY one JSON object matching this JSON Schema, no prose:\n"
            + json.dumps(schema.model_json_schema())
        )
        messages = [
            {"role": "system", "content": "detailed thinking off"},
            {"role": "user", "content": instructions},
        ]
        last_error = None
        for _ in range(2):  # one retry when the reply is not valid JSON for the schema
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": messages, "temperature": 0.2, "max_tokens": 8192},
                timeout=180,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"] or ""
            try:
                return schema.model_validate_json(_first_json_object(content))
            except Exception as e:
                last_error = e
                messages += [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"That was not valid for the schema ({e}). Reply with only the corrected JSON."},
                ]
        raise ValueError(f"Nemotron did not return valid JSON: {last_error}")

    def extract_spec(self, text: str = "", pdf_bytes: Optional[bytes] = None) -> SpecExtract:
        if pdf_bytes:
            text = pdf_to_text(pdf_bytes)
        return self._generate(INGEST_PROMPT + text[:60000], SpecExtract)

    def extract_flows(self, text: str = "", pdf_bytes: Optional[bytes] = None) -> FlowsExtract:
        if pdf_bytes:
            text = pdf_to_text(pdf_bytes)
        return self._generate(FLOWS_PROMPT + text[:60000], FlowsExtract)

    def interrogate(self, node_id: str, context_json: str, asked: List[str]) -> List[XQuestion]:
        prompt = INTERROGATE_PROMPT.format(
            node_id=node_id, context=context_json, asked="\n".join(f"- {q}" for q in asked) or "(none)"
        )
        result = self._generate(prompt, QuestionList)
        for q in result.questions:
            q.target_id = node_id
        return result.questions
