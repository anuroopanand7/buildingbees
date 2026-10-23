"""Skills compiled into prompts at build time (talents/<bee>/<talent>/<skill>/SKILL.md).

Only skills that apply are added, and only their body (the YAML header is for people and tests). Today one skill is
wired in: Shield's India pack (personal data law and GST), added when the product looks like it is for India.
Rules for every skill live in talents/README.md; the lint test in tests/ keeps them to their token cap.
"""

import os
import re
from functools import lru_cache

TALENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "talents")
# Words that say a product is for India. Deliberately plain: a false hit only adds ~270 tokens of questions to ask.
INDIA = re.compile(r"\b(india|indian|inr|rupees?|upi|gstin?|aadhaar|hsn|pune|mumbai|delhi|bengaluru|bangalore|hyderabad|"
                   r"chennai|kolkata)\b|₹", re.I)


def skill_body(relative_path: str) -> str:
    """The text of a skill after its YAML header."""
    with open(os.path.join(TALENTS_DIR, relative_path), encoding="utf-8") as f:
        text = f.read()
    return text.split("\n---\n", 1)[1].strip() if text.startswith("---\n") else text.strip()


@lru_cache(maxsize=1)
def _india_pack() -> str:
    return "\n\nLOCAL RULES (Shield Bee: this product is for India; ask about each, never assume):\n" + \
        skill_body("shield/local-rules/india-dpdp-gst/SKILL.md")


def local_rules(text: str) -> str:
    """The India pack when the idea or spec looks Indian, else nothing."""
    return _india_pack() if text and INDIA.search(text) else ""
