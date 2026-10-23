# Context management rules for BuildingBees

Written 23 Oct 2026 from Google's own write-up of how they manage context in their Agent Development Kit
("Architecting efficient context-aware multi-agent framework for production", Google Developers Blog, 4 Dec 2025,
Hangfei Lin) and the Gemini 4 Argon platform notes (implicit prefix caching, 4,096-token minimum). We could not find a
separate Google research paper on Argon's context handling; these are the primary sources we used.

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
3. **Stable prefix first, changing parts last.** Static instructions, the HIVE talents and the schema go at the front,
   unchanged between calls, so Gemini's and Nemotron's prefix caches reuse them; nothing with a timestamp, board id
   or random order may sit in that prefix.
4. **Scope by default.** Each call gets the minimum it needs: a round update gets the parts of the board the answers
   touch (`_react_board` already does this), a bee's question pass gets its own talent and its own part, a screens
   call gets flows and decisions, not the chat history. A call reaches for more only through an explicit step.
5. **Locked decisions travel in every call, compacted.** Settled decisions are short lines ("D4: parents pay by UPI
   first"), re-sent each round as "do not contradict or re-ask"; changed decisions keep their history
   (superseded, not overwritten).
6. **Compact the session, do not truncate it.** When rounds pile up, older rounds are summarised into one entry
   (what was decided, what changed), and the raw rounds stay in storage for audit. Today we cut text at fixed
   character limits (`[:40000]`, `[:14000]`); replace cuts with summaries.
7. **Filter with rules before the model sees it.** Deterministic filters run first and cost nothing: the standard
   detail filter, near-duplicate check, failure exits, talent routing.
8. **Big inputs are artifacts.** A pasted spec, a PDF or a sketch photo is stored once with a name and a one-paragraph
   summary; prompts carry the summary and the handle; the full text is loaded only for the first map and for an
   explicit "re-read the spec" step.
9. **Untrusted text is quarantined.** Web research (Scout Bee), uploaded files and agent answers are data, never
   instructions: they enter prompts inside a marked block, after the rules, and Scout's findings should arrive as
   validated fields (title, url, one-line fact), not raw page text.
10. **Make the compile observable.** Log, per call, which steps ran and how many tokens each added (the engine pill
    already shows model and time); that is how we see what to cut.

## The knowledge base (memory that outlives a board)

Two kinds, both searchable, both retrieved on demand rather than pinned into every prompt:

- **Team knowledge:** what a team decided once and should not be asked again on every new board: brand colours, the
  stack they use, their country and rules (DPDP, GST), who plays which role. Stored per owner, offered as defaults on
  a new board ("Your team uses Razorpay and Postgres; keep them?"), never applied silently.
- **BuildingBees knowledge:** what the product learns across boards: the question ratings people give (crucial,
  obvious, unclear), which questions unblocked builds, domain question banks (payments, health, education), and the
  adapted talent skills. Anonymised, with no personal data.

Retrieval follows Google's two patterns: **proactive** (before a call, look up what is likely relevant to this
input and add a few short snippets) and **reactive** (a bee asks for a fact it is missing). With our current single
calls, proactive comes first.

## Order of work (after the 30 Oct submission)

1. A single prompt compiler (rules 2, 3, 4) with a test per step, stable prefix measured with cache hits.
2. Locked decisions as short lines with superseded history (rule 5).
3. Spec as an artifact with a summary (rule 8); round compaction (rule 6).
4. Team knowledge (defaults on a new board), then BuildingBees knowledge from ratings.
5. Scout quarantine as validated fields (rule 9).
