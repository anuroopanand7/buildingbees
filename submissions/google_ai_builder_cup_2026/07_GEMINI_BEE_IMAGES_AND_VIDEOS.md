# Bee images, then bee animations (Gemini, 20 Oct 2026)

Roger's rule: the bees should not move all the time. Each bee has ONE still pose. An animation always starts from that pose and ends on exactly that pose, so it can play once and stop, or loop with no jump.

**How:** Step 1 makes the still image of each bee. Step 2 turns each still into a short video where the still is both the first and the last frame. Use Gemini with **3.1 Pro** for the images. For the videos use Gemini's video tool (Veo); if it does not let you set a last frame, use Google Flow (labs.google/flow), which takes a first frame and a last frame: upload the same image as both.

## Step 1: the still images (one prompt per bee)

**Shared style (paste first, every time):**
```
Flat vector mascot, honey bee, friendly and simple, for a software product called BuildingBees. Body: a rounded oval with three thick black stripes on bright bee yellow #FFC800, small white wings with black outline, two short antennae, two black dot eyes, a small smile. Thick even black outline #121210 everywhere, rounded joins, no gradients, no shadows, no texture, no text. Centered, facing slightly to the right, three-quarter view, the whole bee visible with space around it. Plain solid white background. Square image, 1024 by 1024. The same body, eyes and outline thickness for every bee in the set, so they look like one family.
```

Then add ONE of these lines:

| Bee | Add this line |
|---|---|
| Queen Bee (product, scope) | "It wears a small gold crown and holds a tiny clipboard. Calm and confident." |
| Design Bee (what people see) | "It wears a small black beret and holds a pencil." |
| Frontend Bee (screens, states) | "It wears small round glasses and holds a phone-shaped rectangle with a simple screen." |
| Backend Bee (data, services) | "It wears a small yellow hard hat and holds a database cylinder made of three stacked discs." |
| Test Bee (edge cases) | "It holds a magnifying glass up to one eye, head slightly tilted, curious." |
| Compliance Bee (privacy, rules) | "It has a small white shield on its chest, standing upright." |
| Scout Bee (reads the web) | "It holds binoculars up to its eyes, leaning forward, wings slightly raised." |

**Check each image:** same body and outline as the others, readable when shrunk to a small icon, white background. Save each as `bee-queen.png`, `bee-design.png`, and so on.

## Step 2: the animations (each starts and ends on its own still)

Upload the bee's still image as the **first frame** and the **same image as the last frame**, then use the prompt. Ask for 2 to 3 seconds, 1:1, no sound.

**Shared rules (paste first):**
```
Animate this exact mascot in the same flat vector style, with no change to its colours, shapes, outline or background. The video must START on this exact image and END on this exact image, in the same position and pose, so it loops with no jump. Smooth, gentle, playful motion; no camera movement, no zoom, no new objects except the ones named. 2 to 3 seconds, square, white background.
```

| Use in the app | Prompt (after the shared rules) |
|---|---|
| **Thinking** (while the AI works) | "The bee's wings flutter fast, it lifts off a little, flies one small figure-eight loop, then lands back exactly where it started." |
| **Asking** (a bee has a question) | "The bee tilts its head, one antenna bounces twice, a small yellow dot pops above its head and fades, then it returns to the starting pose." |
| **Redrawing** (the board updates) | "The bee draws a short line under itself with a small pencil, left to right, the line fades away, and the bee returns to the starting pose." |
| **Done** (round finished) | "The bee does one happy little hop with a tiny sparkle, then settles back into the starting pose." |
| **Idle** (optional, plays rarely) | "The bee blinks once and its wings twitch once, then it is still." |

**Tips:** make the Thinking video for the Queen Bee first (it is the one people see most); if the bee drifts or changes shape, add "keep the bee the same size and in the same place" and try again; download the MP4 or GIF and send it to Claude.

## How Claude wires them in
- Still images: the bee rail, the pins on cards, the question panel and the start screen.
- Videos: played once on a trigger (Thinking while a map or update runs, Asking when a new question appears, Done when a round finishes), then the still image shows again. Under reduced motion only the still is shown.
