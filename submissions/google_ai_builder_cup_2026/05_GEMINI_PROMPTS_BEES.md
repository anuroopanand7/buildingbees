# Gemini prompts: bee persona icons and the animated bee (18 Oct 2026)

Run these in Gemini with **3.1 Pro** selected (not Flash). Ask for **SVG code**, not pictures: code drops straight into the app, stays sharp at any size, and can be animated with CSS. Paste each prompt as it is; then paste Gemini's SVG back to Claude to wire in.

**Shared brief (paste at the top of every prompt):**

```
You are designing the bee mascots for BuildingBees, a planning tool where a team of AI "bees" interviews a product team and draws the plan of a software product before anyone builds it. Brand: honey-bee black and yellow. Yellow #FFC800 (pressed #F0B400), black #121210, white #FFFFFF, one soft accent allowed only where stated. Style: flat, friendly, geometric, thick even black outlines (2px at 24px size, scale with size), rounded joins, no gradients, no shadows, no text. Every bee shares one body (a rounded hexagon or oval with three black stripes, two small wings, two short antennae, two dot eyes) so the set reads as one family; each persona differs only by one accessory and its pose. Must read clearly at 24 by 24 px and look good at 128 by 128 px. Output: one self-contained inline SVG per bee, viewBox="0 0 64 64", no external fonts or images, ids prefixed with the bee's name, colours as the hex values above.
```

## 1. The seven bee personas (one prompt, one SVG each)

```
Using the shared brief, draw these seven bees as seven separate SVGs, each with a short comment naming it:
1. Queen Bee (product and scope, the product manager): a small crown, holds a tiny clipboard. Calm, confident.
2. Design Bee (what people see and feel): a beret, holds a pencil or brush.
3. Frontend Bee (screens, states, loading and errors): wears small glasses, holds a phone-shaped rectangle.
4. Backend Bee (data, services, timeouts): a hard hat, holds a small database cylinder (three stacked discs).
5. Test Bee (edge cases, what breaks): a magnifying glass held up to one eye, slightly curious tilt.
6. Compliance Bee (privacy, money and legal rules): a small shield on its chest, upright stance.
7. Scout Bee (reads the web first): binoculars raised, wings mid-flap, leaning forward.
Keep the body, eyes and outline weight identical across all seven; only the accessory and the tilt change. After the SVGs, list the exact pixel sizes you tested (24, 32, 64, 128) and anything that does not read at 24 px.
```

## 2. Team role badges (for team mode, optional)

```
Using the shared brief, draw six small round badges (viewBox 0 0 32 32), black outline, yellow fill, each with a simple white or black glyph and no text: Product manager (compass), Client (handshake), Designer (pen nib), Frontend engineer (browser window), Backend engineer (server stack), Tester (check mark in a circle). Same line weight as the bees. One SVG per badge.
```

## 3. The animated bee (a "thinking" mascot, like ChatGPT's pulsing dot or Grok's animated mark)

```
Using the shared brief, make ONE animated bee as a single self-contained SVG with CSS @keyframes inside a <style> tag (no JavaScript, no external files), viewBox="0 0 64 64", that will be shown at 20 to 96 px. Give it five states, each switched by a class on the root <svg>: 
- "idle": a gentle hover, the body bobs 2px up and down every 2.4 s, wings flutter slowly.
- "thinking" (the AI is working, shown in place of a spinner): the bee flies a small figure-eight loop inside the box, wings a fast blur (flap every 80 to 120 ms), three tiny honey dots trail behind it and fade, loop length 1.6 s.
- "asking" (a bee has a question for the person): the bee tilts its head, one antenna bounces, a small yellow question-dot pops above it once every 3 s.
- "redrawing" (the board is being updated): the bee carries a small pencil and draws a short line beneath itself, left to right, then lifts and repeats, 1.4 s.
- "done": one happy loop-de-loop, then lands and stays still with a small sparkle; plays once (animation-iteration-count: 1).
Requirements: animate only transform and opacity (smooth at 60 fps); transform-origin set on each moving part; respect prefers-reduced-motion by switching to a still pose with a slow 2 s opacity pulse; total file under 6 KB; colours only from the brief. After the code, give the class names, each state's loop length, and a one-line note on how to swap states with JavaScript (svg.className.baseVal = "thinking").
```

## 4. A frame strip (only if a video or GIF is needed)

```
Using the shared brief, describe and then draw as 12 separate small SVG frames (viewBox 0 0 64 64, the same bee in each) one loop of the "thinking" flight: frames 1 to 12 at 12 fps, the bee moving along a figure-eight, wings alternating up and down every frame, honey dots trailing. Number each frame in a comment so they can be stitched into a 1-second looping GIF at 256 by 256 px.
```

## Where they go in the app (Claude wires them in)

| Bee | Used in |
|---|---|
| The seven personas | The bee rail on the left, the pins on cards, the question panel, the start screen crew list |
| The animated bee | The "Updating the board" tray, the drawing chip, the loading screen while a map is drawn |
| Role badges | The "Who is answering here?" picker in team mode |
