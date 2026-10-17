# Design rules

The rules the BuildingBees interface follows. The code lives in `web/index.html`; the interaction states are one block at the end of the stylesheet ("Interaction layer"), so they win over the older per-component rules above it.

## Read of the product

A calm B2B work tool for founders and product teams. Neutral surfaces, one accent (bee amber `--accent: #f5b301`), Geist type. Nothing decorative competes with the board.

## Tokens

| Token | Value | Use |
|---|---|---|
| `--ink` / `--ink-hover` / `--ink-press` | `#111110` / `#2e2d2a` / `#000` | Primary button at rest, hover, pressed |
| `--line-strong` / `--edge-hover` | `#cfcdc7` / `#a9a7a0` | Edge of a clickable thing at rest, then on hover |
| `--lift` | small two-layer shadow | "This is raised, press it" |
| `--lift-hover` | wider soft shadow | Hover |
| `--sink` | inset shadow | Pressed |
| `--t-state` / `--t-press` | 150 ms / 80 ms | State change / press |
| `--accent` + `--focus` | amber + pale amber | The one selected thing (a picked option, the active bee) |

## The rules

1. **Every clickable thing looks clickable at rest.** Text buttons and choice cards have a visible edge and a small shadow. Flat grey text on grey never stands for a button.
2. **Four states, all different.** Rest, hover (lift 1 px, edge darkens), pressed (sinks, shadow goes inside, scale 0.98), keyboard focus (2 px dark ring, offset 2 px). Disabled is 40% opacity, no shadow, no motion.
3. **One primary per view.** Solid ink with a faint top highlight. Everything else is secondary (white with an edge) or ghost (edge only).
4. **Choices are marked as choices.** Options lift on hover; a picked option turns amber. The "Just me / With my team" cards carry a radio dot that fills when picked.
5. **Toolbars stay quiet.** Icon buttons (`.tool`, `.icon-btn`, zoom, the bee rail) have no edge at rest, a fill on hover, a darker fill and scale 0.92 on press. Each has an `aria-label` and a tooltip.
6. **Feedback inside 100 ms.** Press uses 80 ms so it feels instant; hover uses 150 ms. A hover the person holds exits at the same speed it entered.
7. **Touch screens get no hover lift** (`@media (hover: none)`), because hover sticks after a tap there. Press feedback stays. Targets are at least 34 px tall and 44 px on the main actions.
8. **Contrast.** Button text meets WCAG AA (4.5:1). Never white text on a white button.
9. **Reduced motion.** `prefers-reduced-motion` turns transitions off; states still change, instantly.
10. **One shape language.** Text buttons and option chips are pills; cards are 14 px; inputs 12 px; toolbar icons 9 px.

## Sources

- ui-ux-pro-max skill: hover states, press feedback, touch and hover, focus states, cursor pointer.
- design-taste-frontend skill: tactile feedback on `:active`, button contrast check, one accent colour.
- `~/Desktop/founder skills/craft/FEEL.md`: exit-speed rule (a state the person holds open is symmetric).
