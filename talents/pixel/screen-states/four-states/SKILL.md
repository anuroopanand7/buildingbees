---
name: four-states
description: Use when planning any screen that shows a list, a result or a picture.
owner_bee: pixel
talent: screen_states
version: 1
source: ours (drafted by DeepSeek via OpenCode, rewritten and checked by Claude, 23 Oct 2026)
license: ours
max_tokens: 200
---

# Four states on every such screen: empty, loading, filled, error

- Ask which screens show a list, a result or a picture. Each needs all four states.
- Empty (nothing yet): ask what words people read and what they can do first.
- Loading (working): ask whether it is a spinner, grey placeholders or one line of text, and when it counts as too long.
- Filled (worked): ask what the one thing is that they must notice.
- Error (failed): say what happened in plain words, with no codes, and give a way to retry. Ask for the exact sentence.
- Each state has its own words and a next step; never share one message.
- Empty is not an error. Ask: is it truly empty, or did something break?
