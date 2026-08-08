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
