---
name: knowledge-base
description: Use when deciding what BuildingBees should remember beyond one board, or when a new board could start from what a team or the product already knows. Two kinds of knowledge, both retrieved on demand and never pinned into every prompt.
owner: engine
version: 1
source: ours
license: ours
max_tokens: 400
---

# Knowledge base

## Team knowledge (exact lookup, never similarity search)
What a team decided once and should not be asked again: brand colours, stack, country and rules (DPDP, GST), who plays
which role. Stored per owner in Firestore, offered as defaults on a new board ("Your team uses Razorpay; keep it?"),
never applied silently. At most a few lines in a prompt.

## BuildingBees knowledge (patterns across boards)
Question ratings (crucial, obvious, unclear), questions that unblocked builds, domain question banks (payments, health,
education), failure-exit templates, adapted talent skills.

## Before anything is shared across boards (scrub in code, no model)
- Remove emails, phone numbers, URLs, keys, ids (PAN, Aadhaar, GSTIN) and amounts.
- Replace the product, company and people names with tokens.
- Keep only the question pattern and the board pattern, never a founder's answer.

## Retrieval
Proactive: before a call, add at most 3 short snippets relevant to the new input. Reactive: a bee asks for a fact it is
missing. Keyword search first; embeddings from a free tier only if needed. Dropped from the prompt once used.
