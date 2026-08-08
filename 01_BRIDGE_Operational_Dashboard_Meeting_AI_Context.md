---
title: "BRIDGE Operational Dashboard: AI-Ready Meeting Context"
document_type: "Normalized semantic transcript and implementation context"
meeting_date: "July 22, 2026"
meeting_duration: "Approximately 72 minutes"
language: "English (US)"
source_language: "Tagalog-English code-switching"
participants:
  - name: "Alyssa Dimaano"
    role: "Accountant, BRIDGE PH, process owner, and domain expert"
  - name: "Juan Karlo de Guzman"
    aliases: ["JK", "Karlo"]
    role: "Technical lead and application developer"
status: "Working source of truth for analysis, design, implementation, testing, and documentation"
---

# Instructions for ChatGPT

Use this document as the primary source of truth for the BRIDGE operational dashboard discussed in the meeting.

## Processing Rules

1. Distinguish among:
   - **Confirmed requirements**
   - **Proposals or future ideas**
   - **Observed prototype defects**
   - **Open questions requiring confirmation**

2. Do not invent accounting, tax, legal, compliance, or operational rules that are not explicitly supported by this document.

3. Preserve the canonical role names:
   - Administrator
   - Requester
   - GM Approver
   - DCS
   - Mitch
   - BRIDGE Accounting

4. When producing a specification, implementation plan, test plan, code prompt, or issue list:
   - Map every function to its authorized role.
   - Preserve the end-to-end transaction trail.
   - Identify whether a requirement concerns viewing, creating, editing, approving, disbursing, closing, voiding, exporting, or administering.
   - Flag contradictions instead of silently resolving them.

5. Treat the financial and tax-related behavior below as **meeting-derived business rules**, not independently verified professional advice.

6. Prefer structured outputs using headings, tables, numbered workflows, acceptance criteria, and explicit assumptions.

7. Ignore casual conversation unless it explains project intent, scope, or a design decision.

# Recommended Task Prompt

Use the following template when attaching or pasting this document into ChatGPT:

> Using the attached BRIDGE Operational Dashboard meeting context as the source of truth, complete the following task: **[INSERT TASK]**.
>
> Requirements:
> - Separate confirmed requirements, proposals, defects, and unresolved questions.
> - Do not invent missing business or accounting rules.
> - Preserve role-based permissions and the transaction audit trail.
> - Identify conflicts or missing information before making implementation assumptions.
> - Produce the result in **[INSERT OUTPUT FORMAT]**.

# 1. Project Context

BRIDGE is defining a customized operational dashboard for a client. Alyssa provides the accounting and operational process knowledge. JK translates that process into a modern web application.

The application is intended to manage:

- Shipment-related Budget Requests
- Additional Budget Requests
- Approval workflows
- DCS disbursements
- Liquidations and variance closure
- Billing preparation and finalization
- Collections and SOA allocation
- Expense and payment requests
- Loan payments
- Receivables aging
- Role-based access
- Audit controls
- Future accounting-system integration

The near-term priority is a **working demonstration** that can be presented to Anna. The current prototype is visually strong but behaves mostly like a nonfunctional demo. Several controls do not save, submit, filter, export, or preserve state correctly.

# 2. Participant Responsibilities

## Alyssa Dimaano

- Defines the actual accounting and operational workflow.
- Demonstrates the existing Apps Script implementation.
- Identifies incorrect behavior and missing controls.
- Provides screenshots, examples, forms, invoices, and workflow explanations.
- Tests the application using realistic sample data.
- Represents BRIDGE's accounting and independent-control perspective.

## Juan Karlo "JK" de Guzman

- Designs and develops the new application.
- Converts Alyssa's process knowledge into system behavior.
- Manages hosting, security, application architecture, and future integrations.
- Documents requested changes and converts them into implementation prompts.
- Plans future mobile and accounting-system capabilities.

# 3. Canonical Terms

| Term | Meaning in This Project |
|---|---|
| Administrator | Full-access system role responsible for configuration and high-control actions. |
| Requester | User who creates Budget Requests, requests payments, and submits Liquidations. |
| GM Approver | General Manager role responsible for approving or rejecting requests. |
| DCS | Role responsible for disbursement and payment processing. |
| Mitch | Operational/accounting user responsible for Billing and closing Liquidation variances, subject to restrictions. |
| BRIDGE Accounting | External accounting/control role requiring broad visibility and accounting-data access. |
| BR | Budget Request associated with a shipment. |
| ABR | Additional Budget Request associated with an existing shipment or BR. |
| OPEX | Operating expense request. |
| SOA | Statement of Account. |
| Billing | Internal or supporting billing document that is not automatically treated as an official tax invoice. |
| Liquidation | Submission of actual expenses and supporting documents against an approved budget. |
| Variance | Difference between approved budget and actual expense. |
| Pass-through | Reimbursable amount that is not treated as the company's service revenue. |
| Service charge | Revenue-related billing line that may involve VAT and withholding-tax treatment. |
| DCS Payment | Disbursement action performed by DCS. |
| Aging | Number of days an outstanding receivable remains uncollected. |
| Master data | Controlled values such as clients, bank accounts, employees, expense types, and dropdown options. |

# 4. Decision Status Legend

- **Confirmed:** Explicitly agreed or repeatedly reinforced.
- **Proposed:** Suggested but not finalized.
- **Observed defect:** Incorrect or nonfunctional prototype behavior.
- **Open question:** Requires confirmation before implementation.

# 5. Confirmed Role and Permission Requirements

## 5.1 Permission Matrix

| Capability | Administrator | Requester | GM Approver | DCS | Mitch | BRIDGE Accounting |
|---|---:|---:|---:|---:|---:|---:|
| View complete system | Yes | No | Limited by permission | Broad view | Broad operational view | Yes |
| View full dashboard/Overview | Yes | No | View-only | View-only | Not confirmed | Yes |
| Create Budget Request | Yes | Yes | Not required | Not required | Not confirmed | Yes |
| Submit Additional Budget Request | Yes | Yes, for own shipment | Not required | Not required | Not confirmed | Yes |
| Submit Liquidation | Yes | Yes, for own request | Not required | Not required | Review/close only | Yes |
| Approve or reject Budget Request | Yes | No | Yes | No | No | Administrative override only |
| Approve or reject Liquidation | Yes | No | Yes, where applicable | No | No; closes after review | Administrative override only |
| View Billing | Yes | View-only | View-only | View-only | Yes | Yes |
| Edit Billing | Yes | No | No | No | Yes | Yes |
| Finalize Billing | Yes | No | No | No | Yes, subject to controls | Yes |
| Void/cancel finalized Billing | Yes | No | No | No | No | Yes if acting as administrator |
| View Collections and Allocation | Yes | Limited or none | View-only | View-only | Yes | Yes |
| Record and allocate payment | Yes | No | No | Not confirmed | Yes | Yes |
| View DCS Payment | Yes | No | View-only | Yes | View-only or none | Yes |
| Edit/process DCS Payment | Yes | No | No | Yes | No | Yes if administratively authorized |
| Close Liquidation variance | Yes | No | No | No | Yes | Yes |
| Access accounting-only view | Yes | No | No | No | No | Yes |
| Configure banks and controlled master data | Yes | No | No | Select only | No | Yes |
| Export accounting data | Yes | No | No | No | No | Yes |

## 5.2 Access Principles

- Requesters must only see information relevant to their own transactions.
- Requesters must not see the complete dashboard or sensitive organization-wide metrics.
- GM and DCS may have view-only access to the operational Overview, subject to permission filtering.
- The administrator can view and manage all areas.
- BRIDGE needs a separate accounting/control perspective with broad visibility.
- Ordinary users must not be able to configure sensitive master data or perform high-control actions.
- Mitch must not approve requests, perform DCS disbursement, or access the accounting-only view.

# 6. End-to-End Workflow

## 6.1 Controlled Setup

The Administrator or BRIDGE Accounting configures:

- Client master list
- Bank accounts and funding sources
- Employees and roles
- Expense categories
- Common Budget Request line items
- Service-charge and pass-through classifications
- Other recurring dropdown options

Users should select from controlled dropdowns instead of repeatedly entering unrestricted free text.

## 6.2 Shipment Budget Request

1. The Requester opens **Create Budget Request**.
2. The Requester manually enters the existing shipment code or reference.
3. The Requester selects an existing client from a dropdown.
4. The form contains separate:
   - Buying section
   - Selling section
   - Expense or line-item details
5. Common entries should be available through dropdowns.
6. The Requester classifies applicable items as:
   - Reimbursable/pass-through
   - Service charge
7. The Requester can:
   - Save as Draft
   - Submit for Approval
8. The Requester must not select or know the bank or funding source.
9. The submitted request appears in the GM Approver's Approval Center.

## 6.3 Approval

1. The Approval Center groups requests by type, such as:
   - Budget Requests
   - OPEX Requests
   - Marketing Requests
   - Loan Payment Requests
2. The GM sees direct **Approve** and **Reject** actions.
3. The GM may supersede an unused Department Head approval stage if no Department Head exists.
4. Approval must preserve an audit record.
5. After approval, a payment item appears in the DCS disbursement queue.

## 6.4 DCS Disbursement

1. DCS opens the approved payment request.
2. DCS selects a funding source from administrator-controlled values.
3. DCS records or confirms the disbursement.
4. Ordinary users cannot add arbitrary banks or funding sources.
5. After disbursement, the workflow proceeds to:
   - Liquidation
   - Billing
   - Or both, depending on the transaction

## 6.5 Additional Budget Request

1. A Requester opens an existing shipment or approved BR.
2. The Requester selects **Add Budget** or **Additional Budget Request**.
3. The Requester enters:
   - Reason
   - Additional amount
   - Relevant category
   - Reimbursable or service-charge classification
4. The ABR follows its own approval process.
5. Once approved, the ABR must create a **separate DCS disbursement line item**.
6. The additional approved amount must update the shipment's budget total.
7. It must also become visible in downstream Liquidation and Billing records where applicable.
8. The ABR must not be silently marked as disbursed.

## 6.6 Liquidation

1. The Requester sees only their own disbursed requests.
2. The Requester records actual spending and uploads required supporting documents.
3. The only primary actions should be:
   - Save as Draft
   - Submit for Approval
4. Remove manual **Post-Liquidation Journal Entry** actions from the Requester interface.
5. Any accounting posting should occur automatically or outside the Requester workflow.
6. The system calculates the variance:
   - Approved budget greater than actual spending: unused funds must be returned.
   - Actual spending greater than approved budget: reimbursement may be due.
7. The Requester submits the Liquidation but cannot close the variance.
8. Mitch reviews the submission and obtains supporting proof.
9. Mitch uploads:
   - Proof of returned funds when the Requester returns unused money
   - Proof of reimbursement when the Requester is owed money
10. Mitch closes the variance only after mandatory proof is available.
11. The transaction remains open while a variance is unresolved.

## 6.7 Billing

1. Mitch prepares the Billing record using shipment and approved-budget data.
2. The document should be called **Billing**, not automatically **Invoice**.
3. Buying, selling, pass-through, service-charge, VAT, and withholding-related fields must be represented according to the approved process.
4. Before finalization, Mitch may edit the Billing record.
5. Selecting **Finalize and Send** must display a clear confirmation.
6. After finalization, the Billing record becomes immutable.
7. Only the Administrator or authorized BRIDGE control role may void or cancel it.
8. A finalized document must never be silently overwritten.
9. A replacement should preserve the original record and use a controlled suffix or revision identifier.
10. A credit memo or equivalent correction record may be required and must be administrator-approved.
11. The complete history must remain available for audit.

## 6.8 Collections and SOA Allocation

1. Mitch or an authorized accounting user records a received payment.
2. The form should capture:
   - Check or payment reference number
   - Receiving bank account
   - Check or payment date
   - Total amount received
3. The system retrieves the client's existing outstanding SOAs.
4. The user allocates one payment across one or multiple SOAs.
5. Partial payments leave a visible outstanding balance.
6. The allocation must not be represented as "Mitch owns allocation."
7. The transaction status should reflect outcomes such as:
   - Unpaid
   - Partially Collected
   - Fully Collected
8. The dashboard must show receivables aging.

## 6.9 Non-Shipment Request for Payment

For payments not associated with a shipment:

1. The user opens **Request for Payment**.
2. The user selects an expense type:
   - OPEX
   - Marketing
   - Loan Payment
   - Other approved categories
3. The user enters the purpose and amount.
4. Remove requester-facing fields such as:
   - Requested Funding Source
   - Bank to Pay From
5. The request proceeds to GM approval.
6. After approval, it appears in DCS Payment.

## 6.10 Accounting Export and Integration

BRIDGE Accounting needs transaction data to be readily available for transfer into QuickBooks or another accounting system.

Near-term options:

- Export a structured CSV compatible with accounting workflows
- Export an accounting-ready transaction report
- Export a PDF where useful

Future options:

- QuickBooks connection
- API-based synchronization
- Integration with another accounting platform

The full integration is a later phase. The immediate priority is the interface and working operational workflow.

# 7. Accounting and Financial Classification Rules From the Meeting

> These rules are derived from Alyssa's explanation and require professional validation before being treated as formal tax or accounting policy.

- Buying and selling data must be represented separately.
- Service charges represent actual service revenue and may involve VAT and withholding-tax treatment.
- Pass-through amounts are generally reimbursable items rather than service revenue.
- Buying and selling amounts for pass-through items may be equal.
- A client-facing SOA may include reimbursable and service-related amounts.
- An internal Billing document is not automatically equivalent to an official tax invoice.
- Finalized financial records must retain revision, void, and replacement history.
- High-control corrections require administrator or BRIDGE authorization.

# 8. UI and UX Requirements

## Confirmed

- Modern, visually appealing, and professional interface
- Role-specific navigation and data visibility
- Simple, clear action labels
- Dropdowns for recurring data
- Separate buying and selling sections
- Approval Center organized by request type
- Payment Center and Approval Center should use consistent layouts
- Full working demo behavior, not a purely visual prototype
- A reset function for restoring sample data
- No unnecessary accounting controls in the Requester interface
- Do not expose sensitive dashboard data to Requesters

## Proposed

- Idle timeout of approximately 15 to 20 minutes
- Progressive web application behavior
- Native-looking Android and iPhone applications
- App Store and Play Store distribution
- Personalized client application branding

# 9. Security Requirements

## Current Prototype

- Email-based one-time verification code
- Aggressive automatic logout behavior

## Required Corrections

- Refreshing the page must not immediately log the user out.
- Session behavior must not cause unsaved data loss.
- Use a reasonable idle timeout.
- Preserve role-based authorization after refresh.
- Approval and administrative actions must only appear for authorized roles.

## Future

- Stronger two-factor authentication
- Formal security hardening
- Mobile-device testing
- Production-grade session management

# 10. Observed Prototype Defects

| Area | Observed Defect |
|---|---|
| Authentication | Refreshing often logs the user out immediately. |
| Persistence | Drafts and submitted entries disappear after refresh. |
| Role simulation | "View as Role" does not consistently match actual account behavior. |
| Approval Center | Requests do not consistently appear after submission. |
| Filters | Approval Center filters do not work. |
| Navigation | The interface may not return correctly from a simulated role view. |
| Administration | User-management buttons do not respond. |
| Export | PDF, CSV, and authorized-view exports do not respond. |
| Additional Budget | Approved ABR does not consistently create a separate DCS disbursement item. |
| Additional Budget | ABR may be incorrectly marked as automatically disbursed. |
| Additional Budget | Additional amounts do not consistently appear in Liquidation or Billing. |
| Liquidation | Buttons and status labels are confusing or redundant. |
| Billing | Correction, void, replacement, and credit-memo workflow is incomplete. |
| Collections | Existing implementation does not correctly allocate one payment across multiple SOAs. |
| Dashboard | Receivables aging is missing or incomplete. |
| Master data | Some staff names or data were copied unexpectedly. |
| Performance | Apps Script implementation is slow because of many lookups and controls. |
| Demo behavior | Many sections are visual only and do not perform real actions. |

# 11. Open Questions

1. Should BRIDGE use the ordinary Administrator role or a separate **BRIDGE Accounting Administrator** role?
2. Should Mitch have full operational view access, or only Billing, Collections, and Liquidation-review access?
3. Does the GM approve Liquidations, or does the GM only approve requests while Mitch performs final Liquidation closure?
4. Which users should see the complete dashboard in addition to GM, DCS, Administrator, and BRIDGE?
5. What is the exact required accounting treatment for:
   - Voided Billing records
   - Replacement records
   - Credit memos
   - Official invoices
6. What is the authoritative source for client, shipment, bank, employee, and SOA master data?
7. Which reports must be exportable in the first version?
8. What exact fields are required for Loan Payment Requests?
9. How should interest be entered when the Requester does not know the final amount?
10. Which notification events require email or in-app alerts?
11. What should the final session timeout be?
12. Which features are required for the Anna demonstration versus a later production release?

# 12. Prioritized Action Items

## Immediate Demo Priority

1. Fix saving and persistence.
2. Prevent logout on refresh.
3. Implement real role-based access.
4. Make the Budget Request form match the demonstrated content.
5. Implement the Approval Center by request type.
6. Implement DCS disbursement.
7. Implement ABR propagation.
8. Implement Liquidation and variance closure.
9. Correct Billing finalization and void controls.
10. Correct Collections and SOA allocation.
11. Add receivables aging.
12. Make essential exports functional.
13. Add a reset-to-sample-data function.

## Later Phases

- QuickBooks-compatible export
- QuickBooks or accounting API integration
- Stronger two-factor authentication
- Android and iPhone applications
- App-store distribution
- Per-client mobile branding
- Production performance optimization

# 13. Condensed Semantic Transcript

This section preserves the meeting's business meaning while removing repeated filler, casual chatter, and transcription noise.

## 0:00-3:42 — Product Direction and Development Method

**JK:** The application improved because the work was developed iteratively instead of asking the AI to build everything in one attempt. Alyssa's detailed process explanations allowed the system to become customized.

**Alyssa:** The concept had been proposed earlier, but discussing it in person made it easier to communicate.

**JK:** A customized application could strengthen BRIDGE's credibility. A future mobile app may make the offering more compelling.

## 3:42-7:25 — Mobile Application, Credentials, and Authentication

**Alyssa:** Mobile applications can be part of the next development phase.

**JK:** A progressive web application or store-distributed app may provide a native-looking experience. Per-client mobile applications could be included in a higher-priced package.

**JK:** The current login uses an emailed verification code. Stronger two-factor authentication is a future improvement.

**Alyssa:** The current method is not the final security design.

## 7:25-15:50 — Initial Prototype Review

**Alyssa:** The interface is visually strong, but the Budget Request content must follow the real operational form.

**Alyssa:** The form needs Budget, Buying, Selling, expense details, and dropdowns rather than a generic expected-cost field.

**JK and Alyssa:** Drafts and submitted requests disappear. Refreshing logs the user out. The prototype does not preserve data.

**Alyssa:** The demonstration must behave like a working system even if it is not yet hosted or production-ready.

## 16:18-27:19 — Roles, Permissions, and Approval Center

**Alyssa:** Every role must be tested separately. The role simulator does not consistently reflect the actual user experience.

**JK and Alyssa:** Administrator has full access. Requesters need limited access. GM and DCS need role-specific operational views.

**Alyssa:** The Approval Center must group Budget, OPEX, Marketing, and Loan requests. It should use a layout similar to the Payment Center.

**Alyssa:** Frequent entries should be controlled through dropdowns. The goal is to convert the client's usual process into a guided automated workflow.

## 27:19-34:38 — Budget Request and Approval

**Alyssa:** Shipment codes are manually entered because the company already assigns them. Client data should come from a dropdown.

**Alyssa:** Buying and selling classifications are essential. Service-charge and pass-through line items have different accounting meanings.

**Alyssa:** The submitted Budget Request should move to an approval matrix. The GM may supersede a Department Head stage when no Department Head exists.

**JK:** Screenshots and clear notes should be used to communicate the exact required layout and workflow.

## 34:38-43:53 — DCS Disbursement and Additional Budget

**Alyssa:** DCS must select from administrator-controlled bank accounts. Users must not add arbitrary banks.

**Alyssa:** An Additional Budget Request is associated with an existing shipment and must create a separate DCS disbursement item after approval.

**Alyssa and JK:** The prototype failed to create that separate item and may have incorrectly marked the ABR as disbursed.

**Alyssa:** Realistic sample data is necessary because workflow bugs appear only when the complete transaction trail is tested.

## 44:09-50:19 — Liquidation and Variance Closure

**Alyssa:** The Requester should only see simple Save as Draft and Submit actions.

**Alyssa:** Manual post-liquidation journal-entry controls should be removed.

**Alyssa:** If approved funds exceed actual spending, the difference must be returned. If actual spending exceeds the budget, reimbursement may be required.

**Alyssa:** Supporting proof is mandatory. Mitch, not the Requester, closes the variance after reviewing and uploading the proof.

## 50:19-59:22 — Billing, Finalization, and Audit Controls

**Alyssa:** Mitch prepares Billing. The system should not automatically call it an Invoice.

**Alyssa:** Once finalized and sent, the Billing record must become immutable.

**Alyssa:** Only the Administrator or BRIDGE control role may void or cancel it.

**Alyssa:** Replacement records must not overwrite the original. The history must show the void, the responsible administrator, and the replacement identifier.

**JK:** The correction workflow, including credit memos or replacement documents, is important enough to include.

## 59:22-1:04:39 — Collections, SOA Allocation, and Aging

**Alyssa:** Refreshing should not immediately end the session. A reasonable idle timeout is preferable.

**Alyssa:** Billing and Collections should be separate areas.

**Alyssa:** Record Payment must capture payment details and allocate one payment across one or more existing SOAs.

**Alyssa:** Partial allocation leaves an outstanding receivable.

**Alyssa:** The dashboard needs receivables aging, meaning the number of days a shipment remains unpaid.

## 1:04:39-1:08:23 — OPEX, Marketing, Loans, and Client Data

**Alyssa:** Non-shipment expenses should use a simple Request for Payment flow.

**Alyssa:** Add Loan Payment as an expense type.

**Alyssa:** Remove requester-facing bank-source fields.

**Alyssa:** A client master list makes request creation easier.

**Alyssa:** Remove the incorrect "Mitch owns allocation" concept. Payment allocation must follow the SOA-based workflow.

## 1:08:23-1:11:34 — Accounting View, Export, and Next Steps

**Alyssa:** BRIDGE needs an accounting-only view containing the client's full transaction history.

**Alyssa:** The information must eventually move into QuickBooks or another accounting system.

**JK:** A QuickBooks-compatible CSV export may be a practical first step before API synchronization.

**Alyssa:** The accounting integration should not delay the immediate demonstration. First fix the interface and core workflow.

**Alyssa and JK:** Existing export controls do not work. The transcript, screenshots, and recording will be used as development context.

# 14. Source-Fidelity Note

This is a normalized semantic transcript, not a word-for-word legal transcript. It preserves the operational meaning, decisions, defects, and proposals from the Tagalog-English meeting while removing duplicated phrases, filler speech, obvious transcription errors, and unrelated casual conversation.
