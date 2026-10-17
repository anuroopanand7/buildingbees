# Deep research round 3 (17 Oct 2026): the plan an agent can build from

Run each in Gemini (3.1 Pro or Argon, Deep Research). Paste each answer back to Claude, or save it next to this file.

## 13. What plan format makes AI coding agents build without guessing

```
I am building BuildingBees, a B2B planning platform. AI role agents interview a founder or a product team and produce a complete plan of a software product (user flows with every failure branch, screens with every state, data, APIs, decisions, assumptions, open questions). The plan is handed to AI coding agents (Claude Code, Cursor, Google Jules, Kiro, GitHub Copilot agent) to build. Agents hallucinate when the plan has gaps, so the plan's format matters.

Research "spec-driven development" and agent-ready specifications in 2025 and 2026:
1. The formats in use and what each contains: AWS Kiro (requirements.md with user stories and EARS acceptance criteria, design.md, tasks.md), GitHub Spec Kit (spec, plan, tasks), AGENTS.md, CLAUDE.md, Cursor rules, Google Jules task specs, PRD templates written for agents.
2. Evidence on what reduces agent mistakes: acceptance criteria formats (EARS, Given-When-Then), task granularity, explicit non-goals, decision and assumption logs, test-first instructions, examples versus rules.
3. The ideal structure of one exported plan (sections, order, level of detail) so a coding agent can build a whole product end to end, and how to split it into files.
4. How to mark uncertainty so agents ask instead of guessing (open questions, assumed versus confirmed).
5. A concrete template we can generate automatically, with a short example for "a B2B tool where clients book and pay for consultations with advisors".
Cite sources inline.
```

## 14. Assumption logs that people actually read

```
BuildingBees (an AI planning tool) fills in many details itself with standard defaults (timeouts, retries, loading and error states) and its own recommendations, instead of asking the founder or team about each one. We want an "assumption log" the person can check without having to approve every line.

Research how assumptions and decisions are recorded and reviewed in product and engineering work:
1. Assumption logs, RAID logs (risks, assumptions, issues, dependencies), architecture decision records (ADRs), decision logs, assumption mapping (David Bland), and how teams keep them useful.
2. Status lifecycles for an assumption (assumed, confirmed, changed, risky) and who should confirm which kind.
3. How to show many assumptions without fatigue: grouping, risk ranking, "confirm all in this group", highlighting only the risky ones, and evidence from UX on review and consent screens.
4. How to word assumptions for a non-technical founder versus an engineer.
5. A recommended design for our assumption log: fields, groups, ranking rule, and the confirm or change interaction.
Cite sources inline.
```

## 15. User stories, acceptance criteria and feature lists, written for two audiences

```
BuildingBees turns an interview with a founder or team into user flows (steps, decision branches, failure paths), screens and decisions. We want to generate, automatically and reliably, (a) user stories with acceptance criteria for every flow and branch, (b) a feature list with priorities, and (c) a build order, in plain words for a non-technical founder and in technical terms for an engineering team.

Research:
1. Best practice for user stories and acceptance criteria (INVEST, Given-When-Then, EARS, job stories), common mistakes, and how many criteria per story.
2. Deriving stories and criteria from user flows and failure branches: methods and examples.
3. Feature prioritisation methods that work for a first version (MoSCoW, Kano, RICE, story mapping with a walking skeleton) and how to pick "must have for v1" automatically from a plan.
4. Build order for agents and small teams: vertical slices, walking skeleton, each slice with a done check.
5. Writing the same plan in two voices (layman and technical): what changes, what must stay identical, with examples.
6. A generation recipe (inputs, rules, output schema) an AI can follow, with a short example for "a B2B tool where clients book and pay for consultations with advisors".
Cite sources inline.
```
