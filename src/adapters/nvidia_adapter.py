"""
NVIDIA adapter: Nemotron through any OpenAI-compatible endpoint.
Default endpoint is Nebius Token Factory, which the Nebius x NVIDIA hackathon requires. Set NVIDIA_BASE_URL
and NVIDIA_MODEL from the Token Factory dashboard; any OpenAI-compatible endpoint serving Nemotron works.
Same jobs as the Gemini adapter, with the same output schemas, so the graph code does not care which engine
ran. PDFs are converted to text first; a photo of a sketch goes to the vision model.
"""

import io
import json
import os
import re
from typing import List, Optional

import httpx

from src.adapters.gemini_adapter import EngineNotConfigured
from src.adapters.spec_prompts import (
    FLOWS_PROMPT, FlowsExtract, PLAN_PROMPT, PlanExtract, INGEST_PROMPT, INTERROGATE_PROMPT, QuestionList, Reaction, SpecExtract, XQuestion,
)

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"  # the hackathon requires Nebius Token Factory
# Routing, as the Best Apps and Agents track asks: "Reach for Nemotron 3 Ultra when you need serious reasoning,
# and let Nano or Super handle the fast, everyday calls." Ultra draws the flows, the screens and the plan; Super
# reads each round of answers and notes (a few seconds, a third of the price).
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
DEFAULT_HEAVY_MODEL = "nvidia/Nemotron-3-Ultra-550b-a55b"
VISION_MODEL = "nvidia/Nemotron-3.5-Super-VL"  # reads a photo of a whiteboard or napkin sketch
# A/B on 4 ideas (20 Oct 2026): for drawing flows, Super VL matched Ultra on quality (7 questions an idea, 0 on
# standard topics, 0 duplicates) at 6.6 s and $0.003 against 12 s and $0.014, and Ultra failed once in 4. For screens
# Ultra drew about 50% richer specs (12 screens, 12 APIs against 9 and 6), so it keeps the screens and the plan.
FLOWS_MODEL = VISION_MODEL
# When a model errors or returns JSON that does not fit, the other one answers instead.
FALLBACK = {DEFAULT_HEAVY_MODEL: VISION_MODEL, VISION_MODEL: DEFAULT_HEAVY_MODEL, DEFAULT_MODEL: VISION_MODEL}
# Token Factory prices in US dollars per token, input and output (read from its /v1/models on 20 Oct 2026).
PRICES = {DEFAULT_HEAVY_MODEL: (1.0e-6, 3.0e-6), DEFAULT_MODEL: (3.0e-7, 9.0e-7), VISION_MODEL: (3.0e-7, 9.0e-7)}
# Spend guard: we have $25 of credit that must last until judging ends on 15 Dec, so a day may spend at most this.
DAILY_BUDGET_USD = float(os.getenv("NVIDIA_DAILY_BUDGET_USD", "1.5"))
# Ultra drew screens in 17 s in the A/B but took 162 s when busy (video test, 20 Oct). Past this many seconds
# its fallback answers instead, so a person never waits minutes.
HEAVY_TIMEOUT_S = float(os.getenv("NVIDIA_HEAVY_TIMEOUT_S", "45"))


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
        # shortcut: the spend count lives in memory (one Cloud Run instance, max-instances 1); a restart resets it.
        # Move it to Firestore if the service ever runs more than one instance.
        self._day, self.spent_today = "", 0.0

    @property
    def enabled(self) -> bool:
        """True when an NVIDIA (Nebius Token Factory) API key is set."""
        return bool(self.api_key)

    def _spend(self, model: str, usage: dict) -> None:
        """Adds one call's cost (from the token counts Token Factory returns) to today's total."""
        price_in, price_out = PRICES.get(model, PRICES[DEFAULT_HEAVY_MODEL])
        self.spent_today += usage.get("prompt_tokens", 0) * price_in + usage.get("completion_tokens", 0) * price_out

    def _generate(self, prompt: str, schema, model: Optional[str] = None, image: Optional[tuple] = None):
        """Calls one Nemotron model; if it errors or never fits the schema, its fallback model answers instead."""
        model = model or self.model
        try:
            return self._generate_once(prompt, schema, model, image)
        except RuntimeError:
            raise  # the daily budget guard: no fallback, that would spend more
        except Exception:
            backup = FALLBACK.get(model)
            if not backup or (image and backup != VISION_MODEL):
                raise
            return self._generate_once(prompt, schema, backup, image)

    def _generate_once(self, prompt: str, schema, model: Optional[str] = None, image: Optional[tuple] = None):
        """Calls Nemotron with the schema in the prompt and validates the JSON; one retry with the validation error when it does not fit."""
        if not self.enabled:
            raise EngineNotConfigured("NVIDIA_API_KEY is not set")
        import time as _t
        today = _t.strftime("%Y-%m-%d")
        if today != self._day:
            self._day, self.spent_today = today, 0.0
        if self.spent_today >= DAILY_BUDGET_USD:
            raise RuntimeError("Today's Nemotron budget is used up, so the demo keeps its credit for tomorrow. Please try again tomorrow.")
        instructions = (
            prompt
            + "\n\nReply with ONLY one JSON object matching this JSON Schema, no prose:\n"
            + json.dumps(schema.model_json_schema())
        )
        user = instructions
        if image:  # OpenAI-style image part: the vision model reads the sketch next to the instructions
            import base64
            user = [{"type": "text", "text": instructions},
                    {"type": "image_url", "image_url": {"url": f"data:{image[1]};base64,{base64.b64encode(image[0]).decode()}"}}]
        messages = [
            {"role": "system", "content": "/no_think"},
            {"role": "user", "content": user},
        ]
        last_error = None
        for _ in range(2):  # one retry when the reply is not valid JSON for the schema
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                # Thinking off: left on, Nemotron 3 spends the whole token budget reasoning and the JSON is cut short.
                json={"model": model or self.model, "messages": messages, "temperature": 0.2, "max_tokens": 8192,
                      "chat_template_kwargs": {"enable_thinking": False}},
                timeout=HEAVY_TIMEOUT_S if model == DEFAULT_HEAVY_MODEL else 180,  # a busy Ultra hands over
            )
            resp.raise_for_status()
            body = resp.json()
            self._spend(model or self.model, body.get("usage") or {})
            content = body["choices"][0]["message"]["content"] or ""
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
        """Turns an idea, a PDF or a photo of a sketch into users, flows, branches and the first questions (stage one).
        Ultra reasons over text; a sketch photo goes to the vision model, which reads its boxes and arrows."""
        if pdf_bytes:
            text = pdf_to_text(pdf_bytes)
        if image:
            note = ("\n(See the attached image: a photo of the founder's own sketch. Read its boxes, arrows and labels as "
                    "their draft user flow: keep what it shows, and ask about what it leaves out.)")
            return self._generate(FLOWS_PROMPT + (text or "(see the attached image)")[:60000] + note, FlowsExtract,
                                  model=VISION_MODEL, image=image)
        return self._generate(FLOWS_PROMPT + text[:60000], FlowsExtract, model=os.getenv("NVIDIA_FLOWS_MODEL") or FLOWS_MODEL)

    def react(self, prompt: str) -> Reaction:
        """A bee reads one answer: a sharper follow-up if it is vague, otherwise changes to the board."""
        return self._generate(prompt, Reaction)

    def write_plan(self, board_json: str) -> PlanExtract:
        """Writes user stories with acceptance criteria, a feature list, a build order and a glossary from the board."""
        return self._generate(PLAN_PROMPT + board_json[:60000], PlanExtract, model=self.heavy_model)

    def interrogate(self, node_id: str, context_json: str, asked: List[str]) -> List[XQuestion]:
        """Looks for further product questions on one screen, button or API."""
        prompt = INTERROGATE_PROMPT.format(
            node_id=node_id, context=context_json, asked="\n".join(f"- {q}" for q in asked) or "(none)"
        )
        result = self._generate(prompt, QuestionList)
        for q in result.questions:
            q.target_id = node_id
        return result.questions
