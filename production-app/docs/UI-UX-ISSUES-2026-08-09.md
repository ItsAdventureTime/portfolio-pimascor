# UI/UX issue record — 2026-08-09

This record captures the four reported demo issues and the production rules
that must inherit their fixes.

| Area | Observed issue | Resolution | Production carry-forward |
| --- | --- | --- | --- |
| Top-bar identity | The profile control looked like a disclosure but navigated directly to Administration. | It now opens an explicit profile menu; Administration/return is a menu action. | Identity controls must not perform unrelated navigation on the primary click. |
| Admin workspace cards | Fixed tracks and long role descriptions could compress cards and crowd action rows. | Role cards use responsive auto-fit tracks, zero-minimum grid items, and bounded text. | Use shrink-safe grid tracks and test long labels at desktop, tablet, and mobile widths. |
| Tax profile form | Grid children could retain intrinsic minimum widths; submit action did not consistently span the form. | Form labels can shrink, the action spans the form, and mobile collapses to one column. | Every control needs a shrink-safe parent and a full-width action at narrow widths. |
| DCS funding source | Native input sizing could collide with the adjacent button in a narrow card. | Input is styled, the grid track is `minmax(0, 1fr)`, and mobile stacks controls. | Never rely on native input sizing in dashboard forms. |

## Interaction contract

- A button displaying a chevron and identity information is a disclosure trigger
  unless its label explicitly describes navigation.
- The trigger exposes `aria-haspopup="menu"` and `aria-expanded`; actions have
  clear menu-item labels.
- Role cards remain real buttons with visible focus, pressed state, and one
  action target. Long descriptions wrap instead of expanding the grid.
- No component may create horizontal overflow at 320px, 390px, 768px, or
  1280px viewport widths.

## Verification matrix

Review demo and production in Chromium/Blink, Firefox/Gecko, and Safari/WebKit
at desktop and mobile widths. Check keyboard focus, screen-reader names, menu
state, text wrapping, and adjacent form controls.

## Reference guidance

- [WAI-ARIA disclosure pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/)
- [MDN `minmax()`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/minmax)
- [MDN `min-width`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/min-width)

## Implementation status — production review

The production web implementation now carries the four resolutions above.
The top-bar identity control is an explicit menu button with a labelled menu,
`aria-expanded`, `aria-controls`, focus placement, Escape handling, and
keyboard item navigation. Role cards use shrink-safe grid tracks and bounded
copy. Tax-profile and DCS funding forms keep intrinsic widths from forcing
overflow and stack their controls at narrow widths.
Roles without available profile actions do not expose an empty menu.

Before release, repeat the verification matrix in this document against the
built production artifact. Record browser/version, viewport, keyboard path,
overflow result, and any assistive-technology findings in the production QA
record; a successful TypeScript/Vite build alone does not establish responsive
or accessibility conformance.
