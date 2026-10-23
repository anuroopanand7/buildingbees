---
name: who-can-do-what
description: Use before any database design, to agree who may see and change each kind of data.
owner_bee: bolt
talent: data_modelling
version: 1
source: ours (drafted by DeepSeek via OpenCode, rewritten and checked by Claude, 23 Oct 2026)
license: ours
max_tokens: 200
---

# Who can do what, before any tables

- List the kinds of data in the founder's words first. Ask: what are the main things you store?
- Draw a small table: who (owner, admin, member, visitor) down the side; create, read, change, delete across the top, for each kind of data. Ask: are these the right roles?
- Ask who may see whose data. Ask: can a member see other members' entries, or only their own?
- Ask who may change or delete someone else's entry. Ask: should an admin edit a member's entry?
- Ask what a visitor sees before signing in. Ask: what is public, and what needs a login?
- Ask who can invite or remove people.
- A box nobody has decided stays a question, never a guess. Read the finished table back before the design starts.
