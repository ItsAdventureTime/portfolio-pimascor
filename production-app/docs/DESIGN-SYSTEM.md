# PIMASCOR Design System

This guide implements the terminology, role boundaries, and task structure in `REQUIREMENTS-V2.md`. WCAG 2.2 AA is the accessibility target.

## 1. Design character

The interface is calm, maritime, trustworthy, and operational. It uses the PIMASCOR navy and silver identity with restrained gold accents. Decoration never competes with financial status or action queues.

## 2. Color tokens

| Token | Value | Use |
| --- | --- | --- |
| Navy 900 | `#14213D` | Sidebar and high-contrast headings |
| Navy 800 | `#1C2A4A` | Primary brand surfaces |
| Navy 700 | `#243357` | Secondary brand surfaces |
| Silver 400 | `#B9BCC4` | Borders and brand support |
| Canvas | `#F4F6FB` | Application background |
| Surface | `#FFFFFF` | Cards, sheets, and tables |
| Gold 500 | `#C9A227` | Selected navigation and priority accents |
| Gold 100 | `#F8F0D2` | Soft priority background |
| Green 700 | `#157347` | Success text and icons |
| Green 100 | `#DCF5E8` | Success background |
| Amber 700 | `#9A6700` | Warning text and icons |
| Amber 100 | `#FFF0C2` | Warning background |
| Red 700 | `#B42318` | Error and rejection text |
| Red 100 | `#FEE4E2` | Error and rejection background |
| Blue 700 | `#175CD3` | Informational state |
| Blue 100 | `#DDEBFF` | Informational background |

Text and interactive color combinations must meet WCAG 2.2 AA contrast requirements.

### Brand marks

- Use `pimascor-logo.jpg` for the sign-in screen and protected-workspace splash,
  where the complete portrait lockup has enough space to remain legible.
- Use the square `pimascor-app-icon.jpg` for the sidebar and official document
  letterhead. The adjacent product or company name supplies the full identity.
- Every brand image uses `object-fit: contain`. Never use `cover`, stretch the
  artwork, clip the ship or wordmark, or place content over the clear area.
- A logo that is the only identity has the alternative text `PIMASCOR`. A compact
  mark beside visible `PIMASCOR` text is decorative and uses an empty alternative.
- Installed-app assets include 192 and 512 pixel regular PNG icons, separate
  maskable icons with safe padding, and a 180 pixel Apple touch icon. The launch
  background stays white so the navy-and-silver artwork remains intact.

## 3. Typography

- Primary family: Inter with system sans-serif fallbacks.
- Page title: 28 to 32 pixels, 700 weight.
- Section title: 18 to 20 pixels, 650 to 700 weight.
- Body: 14 to 16 pixels, 400 to 500 weight.
- Table label: 12 to 13 pixels, 650 weight, not all uppercase for long text.
- Financial value: tabular numerals.

## 4. Spacing and geometry

- Base spacing unit: 4 pixels.
- Standard content gap: 16 or 24 pixels.
- Card radius: 16 pixels.
- Input and button radius: 10 pixels.
- Primary touch height: 44 pixels minimum.
- Desktop sidebar: 260 pixels expanded, 84 pixels collapsed.
- Maximum readable content width: 1600 pixels with responsive margins.

## 5. Components

### Status pill

Contains icon, human-readable label, and optional count. Color is secondary to the text.

### KPI card

Contains label, primary value, short explanation, trend or exception, and drill-down action. Projected and actual values use distinct headings.

### Attention item

Contains urgency, record reference, reason it needs attention, age, owner, and one clear next action.

### Data table

Contains sticky header, server-side filters, predictable alignment, tabular money, and one row-open action. Important actions belong in the record view rather than a row full of small links.

### Record drawer

Shows summary, next action, key amounts, ownership, and timeline without losing the list context. Complex editing opens a full page.

### Confirmation dialog

States the record, action, consequence, and whether it can be reversed. High-risk actions require a reason or typed confirmation only when proportionate.

## 6. Motion

- Use brief 120 to 200 millisecond transitions for drawers, menus, and state changes.
- Dashboard totals count smoothly to their current value and profitability bars reveal
  progressively. These effects run once, never loop, and never delay the data.
- Respect reduced-motion preferences.
- Avoid decorative looping animation.

## 7. Accessibility

- Full keyboard operation and visible focus.
- Semantic headings, forms, tables, dialogs, and live notifications.
- A dialog moves focus inside itself, contains Tab and Shift+Tab, closes with Escape,
  restores focus to its opener, and never lets a nested dialog close its parent.
- Interactive targets are at least 24 by 24 CSS pixels; primary touch controls remain at least 44 pixels high where practical.
- Status never depends only on color.
- Forms link errors to affected inputs.
- Tables provide a mobile alternative rather than forcing unreadable horizontal compression.
- Test at 200 percent zoom and common tablet orientations.
- Protected document previews reserve a stable viewing area, identify loading
  progress, render images and PDFs with type-appropriate elements, and replace a
  failed or unsupported preview with a plain-language retry action.

## 8. Task language

- Name navigation after the user's goal: Budget Requests, Approval, DCS for Payment, Liquidations, Billing, Client Payments, and Request for Payment.
- Keep OPEX, Marketing, Loan Payment, and Other as types or tabs inside Request for Payment.
- Use precise state-changing verbs: Save Draft, Submit to GM, Approve, Reject, Record Payment, Finalize Approved Billing, Print Official Document, and Close Liquidation.
- Explain each work queue with one short sentence describing who acts and what happens next.
- Keep status labels in ordinary language and never encode status only through color.

## Official documents

- A printable record is a dedicated document composition, not the visible application with elements hidden.
- Use A4 portrait paged media, a formal letterhead, a centered document title, bordered account and shipment particulars, tabular financial lines, terms, and signature fields.
- Keep currency and totals aligned with tabular numerals. Repeat the table header when a long record continues to another page and avoid splitting totals, terms, or signatures.
- Draft or pending records carry a visible status watermark. Finalized records do not.
- Never place navigation, dialogs, action controls, app notifications, or browser-workspace metadata inside the printable tree.
- Use **Mich** consistently.

## 9. High-consequence actions

Finalization, rejection, payment, voiding, and closure state their consequence, require deliberate confirmation where irreversible, preserve audit history, and display the resulting status. Draft saving must never look equivalent to submission.

## 10. Action feedback and error recovery

- Identify the problem in text and provide a known correction.
- Every action result, status update, form error, and workflow warning uses a centered
  modal dialog, never a corner toast. Dim and softly blur the background, move focus to the
  dismissal action, keep focus inside, support Escape, and return focus to the
  control that triggered the message.
- The dialog states **what happened** and **what to do next**. It remains visible until
  the user deliberately dismisses it. Errors use **Return and correct it**; routine
  updates use **Close and continue**.
- Use `role="alertdialog"` for an error or warning and `role="dialog"` for successful
  or informational action results.
- Offer Continue only for a recoverable condition; make Stop the safe primary action
  when outcome is uncertain.
- Keep **This was not a problem** visible without erasing the report.
- Use calm motion, strong hierarchy, keyboard focus, 48 px mobile actions, safe-area
  padding, and the existing reduced-motion override.
- Never display stack traces, HTTP terminology, database language, or secret values
  to business users.
