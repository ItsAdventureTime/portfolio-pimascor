# UX and Philippine billing controls

Reviewed: 23 July 2026

This note records the design and terminology basis used by the revised demo. It is guidance for implementation and accountant review, not tax or legal advice.

## Task-based language

- **Budget Requests** is the user-facing name for shipment funding requests.
- **Approval** is the single place where the GM decides submitted work.
- **DCS for Payment** is the CEO/DCS queue for approved amounts that still require actual payment.
- **Liquidations** compares approved/released budget with documented actual spend.
- **Billing / Statement of Account** is used for the client-facing commercial record until PIMASCOR's accountant confirms the exact BIR document type and numbering policy.
- **Client Payments** contains receivable aging, the check/payment register, and SOA allocations.

Navigation follows a user's job rather than the database module name. USWDS recommends clear, task-oriented navigation and W3C requires consistent navigation and help. References: [USWDS header](https://designsystem.digital.gov/components/header/), [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Forms and responsive layout

- Save as Draft and Submit for Approval are separate, immediately visible actions.
- Each irreversible action explains its consequence and preserves history.
- Repeated money lines use a compact table-like editor on desktop and a single-column editor on narrow screens.
- Tables include real headers and responsive `data-label` equivalents rather than presenting a desktop table as an unexplained horizontal strip.
- Primary controls are at least 44 CSS pixels high. WCAG 2.2's normative target-size minimum is 24 by 24 CSS pixels; the larger application default improves touch use.
- Tooltips open on keyboard focus as well as pointer hover, use `role="tooltip"`, and are supplemental. Required instructions remain visible in the page. References: [WAI tooltip pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/), [WAI table guidance](https://www.w3.org/WAI/tutorials/tables/), [WCAG 2.2 target size](https://www.w3.org/TR/WCAG22/#target-size-minimum).

## Readability and motion

- Operational body text, labels, table cells, helper text, and status text use a larger rem-based scale so browser zoom and user font preferences still work.
- Content reflows at a 320 CSS-pixel viewport; data tables become labeled cards where a two-dimensional table is not essential.
- Dashboard values count once to the current value and bars reveal once to their
  proportional length. Other feedback animations are short and use opacity/transform
  where possible. Nothing loops continuously or delays a task.
- `prefers-reduced-motion: reduce` removes non-essential transitions and entrance motion across Gecko, Blink, and WebKit engines.

References: [WCAG text resize and reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html), [WCAG animation from interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions), [MDN prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/prefers-reduced-motion), and [web.dev animation performance](https://web.dev/articles/animations-guide).

## Admin monitoring and privacy

- Bridge PH receives an Admin-only graphical view of attributable business/security events.
- The default staff view excludes Admin only as a display filter; Admin actions remain recorded and can be included. OWASP advises against excluding trusted users from audit collection.
- Monitoring is purpose-limited: no passwords, OTPs, keys, full bank data, keystrokes, screenshots, webcams, or unrelated activity.
- Production must notify staff, complete a privacy impact assessment, restrict reviewers, define retention/review cadence, and copy events to protected centralized storage with alerting.

References: [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html), [NIST SP 800-53 Rev. 5 audit controls](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf), and [Philippine NPC monitoring guidance](https://privacy.gov.ph/npc-phe-bulletin-no-14-updated-frequently-asked-questions-faqs/).

## Private documents

- Uploads happen inside the related workflow rather than as context-free files.
- The object key uses lowercase prefixes plus opaque record IDs; the original filename remains in PostgreSQL for display and audit.
- The API checks PDF/JPEG/PNG signatures, limits each file to 100 MB, hashes in bounded chunks, uses managed multipart transfer, records SHA-256, and provides an audited same-origin inline, no-store stream. Download UI is absent and the download endpoint is denied.
- S3 prefixes are virtual, so no empty folders are created before the first upload.

References: [Backblaze S3-compatible API](https://www.backblaze.com/docs/en/cloud-storage-call-the-s3-compatible-api), [Backblaze application-key capabilities](https://www.backblaze.com/docs/cloud-storage-s3-compatible-app-keys), and [Amazon S3 object-key guidance](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html).

## VAT and withholding controls

BIR Revenue Regulations No. 7-2024 revised invoicing requirements, including the use of an invoice as primary evidence for sales and showing VAT information and breakdowns on the invoice. Revenue Regulations No. 11-2024 amended transitional invoicing provisions. References: [BIR RR 7-2024](https://bir-cdn.bir.gov.ph/BIR/pdf/RR%20No.%207-%202024.pdf), [BIR RR 11-2024](https://bir-cdn.bir.gov.ph/BIR/pdf/RR%2011-2024.pdf).

Creditable withholding tax is conditional on the transaction and taxpayer classification. For example, BIR RR 11-2018 describes withholding on certain income payments, while RR 24-2025 amended specific provisions. A blanket hard-coded rate would therefore be unsafe. References: [BIR RR 11-2018 digest](https://bir-cdn.bir.gov.ph/local/pdf/Digest%20RR%2011-2018.pdf), [BIR RR 24-2025 digest](https://bir-cdn.bir.gov.ph/BIR/pdf/RR%20No.%2024-2025%20Digest%20FINAL.pdf).

The application consequently:

1. lets only an Administrator activate accountant-approved VAT/CWT profiles;
2. applies the active profile by service-charge or pass-through classification;
3. snapshots the applied rate and amount on every Billing line;
4. shows the automatic computation before finalization;
5. requires GM or Administrator approval before Billing finalization;
6. locks finalized Billing;
7. uses a GM/Administrator-approved Credit Memo or replacement plus attributable Admin void instead of rewriting history.

## Profitability and printing

- Shipment Profitability uses connected Budget Request, Liquidation, Billing, and collection data.
- Bar comparisons use distinct shape/labels and are paired with a complete table so color is never the only cue.
- The Billing print action activates a dedicated A4 document with letterhead, metadata, itemized charges, totals, terms, signatures, and footer. Navigation, drawers, and surrounding application controls do not print.

References: [USWDS data visualizations](https://designsystem.digital.gov/components/data-visualizations/), [WCAG 2.2 use of color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html), and [MDN printing](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Media_queries/Printing).

Before production launch, PIMASCOR's Philippine tax adviser must confirm document naming, authority-to-print/e-invoicing obligations, VAT treatment, CWT/EWT rates, customer classifications, rounding, numbering, and required legal fields.

## Error assistance and incident privacy

The shared recovery dialog implements WCAG 2.2 error identification, correction
suggestions, and programmatic status messages. OWASP logging guidance supplies the
minimum “when, where, who, what” context while excluding passwords, sessions, keys,
bank data, form payloads, and document contents. Resend sends separate Admin and
Developer notices with idempotency keys. Sources:
[WCAG 2.2 Input Assistance](https://www.w3.org/TR/WCAG22/#input-assistance),
[WCAG Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages),
[OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html),
and [Resend idempotency](https://resend.com/docs/dashboard/emails/idempotency-keys).
