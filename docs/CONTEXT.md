# Context management rules for BuildingBees

Written 23 Oct 2026 from Google's own write-up of how they manage context in their Agent Development Kit
("Architecting efficient context-aware multi-agent framework for production", Google Developers Blog, 4 Dec 2025,
Hangfei Lin) and the Gemini 4 Argon platform notes (implicit prefix caching, 4,096-token minimum), revised the same day
after a Gemini Argon Deep Research review of current practice (Anthropic, OpenAI, Manus, Cognition, LangGraph, Letta,
Mem0, Zep/Graphiti, context-rot studies). We could not find a separate Google research paper on Argon's context
handling.

Google's thesis: **context is a compiled view over a richer stateful system.** The board, its history and its files are
the sources; a pipeline of named steps compiles them into the small prompt one model call needs; that prompt is thrown
away after the call.

## The four tiers, mapped to BuildingBees

| Google tier | What it holds | BuildingBees today | Rule |
|---|---|---|---|
| Working context | The prompt for one call | Built per endpoint by joining strings (`audience()` + prompt + Brief or board JSON) | Compile it per call from the tiers below; never keep it |
| Session | The durable log of what happened | The board in Firestore, `g.rounds` (round changelog), decisions on questions, `g.comments`, `g.conflicts` | Everything that happened is stored as structured records, not prompt text |
| Memory | Knowledge that outlives one board | **Missing** | Add a knowledge base (below) |
| Artifacts | Big inputs, by name and version | The spec or PDF text is stored on the board (up to 60,000 characters) and re-sent in later calls | Send a handle and a short summary; load the full text only when a step needs it |

## The rules

1. **Separate storage from presentation.** The board is the truth; a prompt is only a view of it. Never write model
   output back into the board without validating it against its schema (we already do this for every engine).
2. **Compile with named steps, not ad-hoc strings.** One place builds every prompt, in a fixed order: static rules,
   bee identity and talents, locked decisions, the slice of the board this call needs, the new input. Each step can
   be tested on its own.
3. **Shared, stable prefix first; call-specific parts after; the tail last.** Order: static rules and output schema,
   then the HIVE talents, then team defaults, then a compact index of the whole board (one line per part), all
   byte-identical between calls in a round so the provider's prefix cache (Gemini implicit caching, vLLM or SGLang
   prefix caching behind Nemotron) reuses them across every call; then the slice and the new input. Nothing with a
   timestamp, a request id or unsorted keys may sit in the prefix (serialise JSON with sorted keys).
4. **Scope by default, by the graph.** Each call gets the minimum it needs, chosen by structure (the parts it owns
   plus one hop of neighbours as short stubs), never by character count: a round update gets the parts of the board the answers
   touch (`_react_board` already does this), a bee's question pass gets its own talent and its own part, a screens
   call gets flows and decisions, not the chat history. A call reaches for more only through an explicit step.
5. **Locked decisions sit at the tail, every call.** Settled decisions are short lines ("D4: parents pay by UPI
   first"), placed at the very end of the prompt, just before the task, because models (smaller ones most of all)
   follow the last thing they read and lose what sits in the middle. Changed decisions keep their history
   (superseded, not overwritten).
6. **Evict, do not summarise.** BuildingBees already turns every round into structured board parts and decisions, so
   the board is the summary: once a round is applied, its raw answers leave the prompt (only the latest round's
   answers travel). No model-written summaries of old rounds (they drift and drop exact names). Replace today's
   fixed character cuts (`[:40000]`, `[:14000]`) with slices by structure: whole parts, never half a JSON object.
7. **Filter with rules before the model sees it.** Deterministic filters run first and cost nothing: the standard
   detail filter, near-duplicate check, failure exits, talent routing.
8. **Big inputs are artifacts.** A pasted spec, a PDF or a sketch photo is stored once with a name and a one-paragraph
   summary; prompts carry the summary and the handle; the full text is loaded only for the first map and for an
   explicit "re-read the spec" step.
9. **Untrusted text is quarantined.** Web research (Scout Bee), uploaded files and agent answers are data, never
   instructions: they enter prompts inside a marked block, after the rules, and Scout's findings should arrive as
   validated fields (title, url, one-line fact), not raw page text.
10. **Make the compile observable.** Log, per call, which steps ran, prompt and cached token counts (Gemini
    `cachedContentTokenCount`, OpenAI-compatible `prompt_tokens_details.cached_tokens`) and output tokens; the engine
    pill already shows model and time.
11. **Check every reply against the locked decisions in code.** Before a reply touches the board, drop questions on a
    topic already decided and choices that contradict a locked decision (retry once citing the clash). We already do
    this for standard details, duplicates and failure exits.
12. **Two modes, one state.** When a person's own agent does the model work over MCP, BuildingBees is the tool server,
    not the prompt writer: it hands out small work packages (`get_item`, `next_to_build`, a bee's slice) and validates
    what comes back, so the agent's own context and cache do the rest.

## The knowledge base (memory that outlives a board)

Two kinds, both searchable, both retrieved on demand rather than pinned into every prompt:

- **Team knowledge** (exact lookup by team, never similarity search): what a team decided once and should not be asked again on every new board: brand colours, the
  stack they use, their country and rules (DPDP, GST), who plays which role. Stored per owner, offered as defaults on
  a new board ("Your team uses Razorpay and Postgres; keep them?"), never applied silently.
- **BuildingBees knowledge:** what the product learns across boards: the question ratings people give (crucial,
  obvious, unclear), which questions unblocked builds, domain question banks (payments, health, education), and the
  adapted talent skills. Anonymised, with no personal data.

Before anything joins BuildingBees knowledge it is scrubbed in code: emails, phone numbers, ids (PAN, Aadhaar, GSTIN),
amounts and names replaced; only the question pattern and the board pattern are kept, never a founder's answer.
Search can stay free: keyword search first, embeddings from a free tier later if needed.

Retrieval follows Google's two patterns: **proactive** (before a call, look up what is likely relevant to this
input and add a few short snippets) and **reactive** (a bee asks for a fact it is missing). With our current single
calls, proactive comes first.

## How we know a context change helped
Fixed test boards (a marketplace with payments and GST, a booking app with consent, a file-upload tool, an offline
field app), run before and after each change, scored without a model judge: decisions contradicted (must be 0),
questions repeating an answered one (under 5%), risky steps with a failure exit (100%), names that agree across the 6
docs, and tokens per accepted decision (must not rise). `scripts/eval_questions.py` is the start of this.

## Second review (23 Oct 2026, Argon, on our real stack)

Checked against Nebius's own docs: **prefix caching on Token Factory is implicit and automatic** (no key or opt-in, best
effort), the cache is shared within one model, and the response reports `usage.prompt_tokens_details.cached_tokens`
(`prompt_tokens` includes cached tokens). `prompt_cache_key` only helps routing and is not a security boundary. So a
Plan call and a Docs call that both use Ultra share a cache only if their prompts start with the same bytes.

Rules added by the review:
13. **Pass structure, not prose, between calls.** Screens, Plan and Docs get a compact table of flows, screens, APIs and
    decisions, not the 40,000 to 60,000 character Markdown Brief; the Brief is only for the human to read.
14. **Server-side ids only.** The model never invents short ids; it refers to existing ones or a temporary reference,
    and the server mints the next FL, S, B, A, D, Q number from a counter that never goes back (deleted ids are archived).
15. **Put required behaviour in the schema,** not only in prose: risky steps carry required failure exits; a decision
    carries `topic_key`, `is_model_pick` and `rejected_values`. A required field is something a cheaper model cannot
    forget without failing validation and retrying.
16. **Split the Docs call** into three (TRD, design brief, schema) that share one prefix, so each has room to write and
    a validation error redoes one document, not all three.
17. **Guard board writes.** One lock per board around read, model call and write (a slow model call must not drop a
    teammate's answer), and a bounded memory cache.
18. **MCP work package** under about 2,500 tokens: role and guardrails (do not read the person's local files, do not write
    app code), the decision digest, the slice, what changed this round, the reply contract, and the board revision so a
    stale answer is refused.

## Order of work (after the 30 Oct submission)

1. A single prompt compiler (rules 2, 3, 4, 5): shared prefix, slices by structure, decisions at the tail; cache hits
   logged (rule 10).
2. Locked decisions with superseded history, and the post-reply check (rule 11).
3. Spec as an artifact with a summary (rule 8); evict applied rounds (rule 6); the fixed test boards.
4. Team knowledge (defaults on a new board), then BuildingBees knowledge from ratings.
5. Scout quarantine as validated fields (rule 9).
