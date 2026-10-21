# Prompt tuning log (2026-10-21 15:27)

Baseline: 42/48 checks passed.

Round 1: edit did not match the prompt, skipped.

Round 2: edit did not match the prompt, skipped.

Round 3: edit did not match the prompt, skipped.

Round 4: edit did not match the prompt, skipped.

Round 5: add_example: The instruction 'BRANCHES. Real flows split...' repeats verbatim multiple times but the model still omits drawing explicit branches in generated flows, indicati
  edit: 'Example: "Pick a slot: The client chooses a stylist and an open time."\nAnother example: "Confirm booking: The system checks if the slot is still available and sends a confirmation if yes, or shows alt'
  score 42/48 vs 42/48: reverted. Spend so far $0.039.

Round 6: edit did not match the prompt, skipped.

Round 7: edit did not match the prompt, skipped.

Round 8: edit did not match the prompt, skipped.

Round 9: edit did not match the prompt, skipped.

Round 10: edit did not match the prompt, skipped.

Baseline 42/48. Total spend $0.044.

# Prompt tuning log (2026-10-21 15:29)

Baseline: 41/48 checks passed. Failures:
- A platform where AI agents post gigs and humans claim those : FAILED every flow has a failure split
- A B2B tool where clients book and pay for consultations with: FAILED every flow has a failure split
- An internal tool for a logistics company: drivers upload pro: FAILED every flow has a failure split
- A SaaS dashboard where a marketing team connects their ad ac: FAILED every flow has a failure split
- A tuition centre app in Pune: parents see attendance and tes: FAILED every flow has a failure split
- A tuition centre app in Pune: parents see attendance and tes: FAILED features listed and linked to flows
- A dog walking app in Bangalore: owners book a walker by the : FAILED every flow has a failure split

Round 1: add_constraint: The prompt requires explicit branching logic but does not enforce drawing splits for all plausible failure points, leading to omitted failure paths in generated
  edit: 'If the input does not say, still draw the split where a real product clearly can fail (a payment, a slot or stock someone else can take, an upload, a check that can say no). When that other path has a'
  score 42/48 vs 41/48: KEPT. Spend so far $0.028.

Round 2: add_constraint: The prompt requires explicit branching logic but does not enforce asking clarifying questions when splits are ambiguous, leading to assumed failure paths instea
  edit: 'If the input does not specify behavior on either path of a potential split, you MUST ask a clarifying question about user intent or system behavior before drawing any branch—never assume failure or su'
  score 42/48 vs 42/48: reverted. Spend so far $0.042.

Round 3: add_constraint: The prompt correctly instructs to draw splits but does not require asking clarifying questions when both paths of a split are unspecified, leading to assumed fa
  edit: "If neither path of a split is specified by the input, do not draw any steps for either path—instead, generate a PM question on that flow asking what should happen on each path, using 'step' set to at_"
  score 41/48 vs 42/48: reverted. Spend so far $0.058.

Round 4: add_constraint: The prompt incorrectly requires drawing failure splits even when the input does not mention possible failures, leading to speculative branches that violate the 
  edit: 'If the input does not say what happens on the other path, do not draw the split unless the input explicitly mentions a condition that could fail (like a payment attempt or availability check). Drawing'
  score 42/48 vs 42/48: reverted. Spend so far $0.075.

Round 5: add_constraint: The prompt instructs to always draw splits even when the input doesn't specify behavior on the other path, leading to unnecessary failure branches.
  edit: 'If the input does not say what happens on the other path, do not draw the split unless the input implies a clear failure condition (e.g., payment declined, upload rejected). When drawn, if the other p'
  score 42/48 vs 42/48: reverted. Spend so far $0.092.

Round 6: add_constraint: The prompt instructs to always draw splits even when the input does not specify behavior on the other path, leading to unnecessary failure splits in generated f
  edit: "If the input does not say what happens on the other path, do not draw the split unless the input implies a clear alternative outcome (e.g., 'can fail' or 'might reject'). Otherwise, leave the split un"
  score 42/48 vs 42/48: reverted. Spend so far $0.109.

Round 7: add_constraint: The prompt instructs to always draw splits even when the input doesn't specify behavior on the other path, leading to speculative failure flows.
  edit: 'If the input does not say what happens on the other path, do not draw the split unless the input implies a clear failure condition (e.g., payment declined, upload rejected). Otherwise, leave the path '
  score 42/48 vs 42/48: reverted. Spend so far $0.123.

Round 8: add_constraint: The prompt incorrectly instructs to draw splits even when the input does not specify behavior on the other path, leading to speculative failure branches.
  edit: 'If the input does not say what happens on the other path, do not draw the split; instead, ask whether that split is needed as a PM question on the flow.'
  score 42/48 vs 42/48: reverted. Spend so far $0.137.

Round 9: add_constraint: The prompt incorrectly requires drawing splits even when the input doesn't specify alternative paths, leading to speculative failure branches.
  edit: 'Only draw a split if the input explicitly describes what happens on both paths. If the input does not say what happens on the other path, do not draw the split and instead ask whether that path is nee'
  score 42/48 vs 42/48: reverted. Spend so far $0.151.

Round 10: add_constraint: The prompt instructs to always draw splits even when unspecified, leading to unwanted failure branches.
  edit: 'Only draw a split if the input explicitly describes what happens on both paths. If the input does not say what happens on the other path, do not draw the split; instead, ask whether that path is neede'
  score 42/48 vs 42/48: reverted. Spend so far $0.165.

Confirmation: tuned 42/48, original 41/48.

Saved the tuned prompt to src/adapters/tuned/flows_nemotron.txt.

Baseline 41/48. Total spend $0.194.

