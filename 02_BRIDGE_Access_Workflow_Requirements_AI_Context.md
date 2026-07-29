---
title: "BRIDGE Access and Workflow Requirements: AI-Ready Context"
document_type: "Focused normalized conversation and implementation requirements"
language: "English (US)"
participants:
  - name: "Alyssa Dimaano"
    role: "Accountant, BRIDGE PH, and process owner"
  - name: "Juan Karlo de Guzman"
    aliases: ["JK"]
    role: "Technical lead and application developer"
status: "Focused change-request context"
---

# Instructions for ChatGPT

Treat this document as a focused requirements supplement for the BRIDGE operational dashboard.

## Processing Rules

1. Use the **Canonical Requirements** section as the primary implementation source.
2. Treat the **Ambiguities and Required Confirmations** section as unresolved.
3. Do not grant permissions that are not explicitly listed.
4. Distinguish:
   - View-only access
   - Create access
   - Edit access
   - Approval authority
   - Payment/disbursement authority
   - Liquidation-closing authority
   - Administrative authority
5. Do not infer that access to a module automatically includes approval or edit access.
6. Preserve auditability. Finalized records must not be silently edited, replaced, or deleted.
7. Do not invent accounting or tax treatment.
8. When producing implementation tasks, include acceptance criteria and negative-permission tests.

# Recommended Task Prompt

> Using this focused BRIDGE access and workflow requirements document as the source of truth, produce **[INSERT DELIVERABLE]**.
>
> Requirements:
> - Preserve the role-permission matrix.
> - Separate confirmed requirements from unresolved items.
> - Include negative-access tests.
> - Preserve the Billing, Liquidation, Additional Budget, and Collections audit trail.
> - Do not invent missing accounting rules.

# 1. Canonical Role-Permission Matrix

| Role | Confirmed Access |
|---|---|
| Administrator | Full access to all modules, data, settings, approval controls, audit controls, and administrative actions. |
| Requester | Create and manage own Budget Requests; submit own Liquidations; view own Billing records only. No full dashboard or Overview. No funding-source or bank selection. |
| GM Approver | Approve or reject Budget Requests and applicable Liquidations; view Billing, Collections and Allocation, DCS Payment, and all expenses. Those nonapproval areas are view-only. |
| DCS | Broad view-only access to relevant operational data. Can edit and process DCS Payment. |
| Mitch | Broad operational access except: cannot approve, cannot process DCS Payment, and cannot access the accounting-only view. Responsible for Billing and Liquidation-variance closure. |
| BRIDGE Accounting | Requires broad administrative/accounting visibility. Exact role design remains unresolved: full Administrator or separate BRIDGE Accounting Administrator. |

# 2. Dashboard and Overview Access

## Confirmed

- Administrator: full access.
- Requester: no dashboard or full Overview.
- GM: view-only access to the permitted Overview.
- DCS: view-only access to the permitted Overview.
- BRIDGE Accounting: requires full accounting visibility.

## Implementation Rule

The Overview must be permission-filtered. A role having access to the Overview does not mean that it may see all organization-wide data.

# 3. Requester Requirements

The Requester must be able to:

- Create a Budget Request.
- Create an Additional Budget Request for an existing shipment where permitted.
- Save a request as a draft.
- Submit a request for approval.
- Submit a Liquidation.
- View their own Billing record where applicable.

The Requester must not be able to:

- View the full dashboard or organization-wide Overview.
- Approve or reject requests.
- Select the requested funding source.
- Select the bank from which the payment will be taken.
- Process DCS Payment.
- Close a Liquidation variance.
- Access the accounting-only view.

## Required Primary Buttons

- Save as Draft
- Submit for Approval

Avoid additional redundant save, post, approve, or accounting buttons in the Requester interface.

# 4. GM Approver Requirements

The GM Approver must be able to:

- Receive submitted requests.
- Approve or reject Budget Requests.
- Approve or reject applicable Liquidations.
- View all expenses.
- View Billing.
- View Collections and Allocation.
- View DCS Payment.

The following must remain view-only for the GM unless separately authorized:

- Billing editing
- Collection recording
- SOA allocation
- DCS Payment editing or disbursement
- Accounting administration

Once a Requester submits an item, the GM should immediately see clear:

- Approve
- Reject

The GM must not need to select a bank or funding source.

# 5. DCS Requirements

DCS must have:

- Broad view-only operational access.
- Edit and processing access specifically within DCS Payment.
- Access to approved requests requiring disbursement.
- Ability to select only administrator-configured funding sources.

DCS must not automatically receive general approval authority.

# 6. Mitch Requirements

Mitch must be able to:

- Access operational records needed for Billing.
- Prepare and edit Billing before finalization.
- Review submitted Liquidations.
- Review variance proof.
- Upload or record proof where required.
- Close a Liquidation variance after verification.
- Work with Collections and SOA Allocation.

Mitch must not be able to:

- Approve Budget Requests.
- Approve other requests merely because the record is visible.
- Process DCS Payment.
- Access the accounting-only view.
- Void or cancel finalized Billing unless separately elevated as Administrator.

# 7. Liquidation and Variance Closure

## Workflow

1. Requester submits a Liquidation.
2. The system calculates any variance.
3. The Requester supplies supporting documentation.
4. Mitch reviews the Liquidation.
5. When unused funds must be returned:
   - Mitch obtains the Requester's proof of deposit.
   - Mitch uploads or records that proof.
6. When the Requester must be reimbursed:
   - Mitch uploads or records proof of reimbursement.
7. Mitch closes the variance only after the proof is complete.

## Acceptance Rules

- The Requester cannot close the variance.
- Proof is mandatory before closure.
- The system retains the identity of the person who closed it.
- The record remains open while the variance is unresolved.

# 8. Billing Finalization and Correction

## Finalization

- Billing can be edited before finalization.
- Once sent and finalized, Billing becomes immutable.
- A confirmation should appear before finalization.

## Cancellation and Replacement

- Only the Administrator may cancel or void a finalized Billing record.
- A replacement record may be created when necessary.
- The replacement must not overwrite the original.
- The original must remain in the audit history.
- A controlled revision suffix or identifier should distinguish the replacement.
- Accounting corrections may require a Credit Memo.
- Credit Memo approval must belong to the Administrator.

# 9. Additional Budget Request Defect

## Expected Behavior

When an Additional Budget Request is created for an existing shipment BR:

1. It is submitted through the appropriate approval path.
2. After approval, it creates a separate DCS Payment or disbursement item.
3. The additional approved amount updates the shipment budget.
4. The additional amount appears in Liquidation.
5. The additional amount appears in Billing where applicable.
6. It remains separate from the original disbursement for audit purposes.

## Observed Defects

- The Additional Budget was not automatically added to the expected workflow.
- The parallel workflow did not function.
- The new amount did not appear in Liquidation.
- The new amount did not appear in Billing.
- Some downstream fields became required incorrectly.
- The system may have treated the ABR as already disbursed.

# 10. Funding-Source and Bank Visibility

## Confirmed Rule

The Requester should not select or view the requested funding source because the Requester may not know:

- Which bank will fund the payment
- Which internal source should be used
- The final interest amount for a loan-related payment

Remove the funding-source field from:

- Budget Request
- OPEX Request
- Other requester-facing payment requests

The funding source should be selected later by DCS or an authorized administrative role using controlled master data.

# 11. Loan Payment Requirement

Add **Loan Payment** as an approved Request for Payment category.

## Minimum Confirmed Fields

- Purpose
- Requested amount
- Expense or payment type
- Supporting documentation, where required

## Open Issue

The Requester may not know the final interest amount. The application must not force the Requester to invent it.

Possible designs require confirmation:

- Request principal only; authorized accounting user adds interest later.
- Select a predefined loan record with stored terms.
- Permit an estimated amount that must later be reconciled.
- Calculate interest from administrator-maintained loan data.

# 12. Collections and Allocation Correction

The current Collections implementation is incorrect.

## Required Behavior

- Use a **Record Payment** workflow.
- Record the payment or check details.
- Retrieve existing outstanding SOAs for the selected client.
- Allocate one received payment across one or multiple SOAs.
- Support partial allocation.
- Preserve the remaining balance.
- Remove any incorrect concept that "Mitch owns allocation."
- Add receivables aging.

# 13. Accounting View and Export

BRIDGE requires an accounting-only view that ordinary client roles cannot access.

The accounting data must be readily available for:

- QuickBooks import
- Another accounting platform
- Structured CSV export
- Future API synchronization

The accounting view should expose the complete authorized transaction history while preserving role and privacy boundaries.

# 14. Budget Request Interface Changes

Revise the Budget Request interface based on the preceding meeting requirements.

At minimum:

- Separate Buying and Selling sections.
- Use client and common-item dropdowns.
- Use shipment reference data.
- Support Additional Budget Requests.
- Remove requester-facing bank and funding-source fields.
- Show only:
  - Save as Draft
  - Submit for Approval
- Ensure submitted items appear in the GM Approval view.
- Ensure approved amounts propagate to DCS Payment, Liquidation, and Billing.
- Preserve the full audit trail.

# 15. Observed Defects Summary

| Defect | Expected Correction |
|---|---|
| Additional Budget does not propagate | Create separate approved disbursement item and update downstream modules. |
| Liquidation does not show additional amount | Include all approved shipment budgets. |
| Billing does not show additional amount | Include applicable approved additional budgets. |
| Collections logic is incorrect | Implement payment recording and SOA allocation. |
| Requester sees funding fields | Remove them from requester-facing forms. |
| Requester may see an Overview | Remove or strictly permission-filter the Overview. |
| Approval controls may appear under wrong roles | Render actions only for authorized roles. |
| Parallel process fails | Implement independent state transitions with a linked audit trail. |
| Required fields appear incorrectly | Make fields conditional on role and workflow stage. |
| Budget Request UI does not match the real process | Redesign it using the previous meeting requirements. |

# 16. Ambiguities and Required Confirmations

1. Is BRIDGE a normal Administrator, or should it have a separate BRIDGE Accounting Administrator role?
2. Does the GM approve Liquidations, or does the GM approve the submission while Mitch performs the final accounting closure?
3. How much operational data should Mitch be able to view outside Billing, Collections, and Liquidation?
4. Should Requesters view only their own Billing records or all Billing records connected to their department?
5. Who records received payments: Mitch, BRIDGE Accounting, or another Collections role?
6. What exact fields are required for Loan Payment?
7. How should unknown interest be handled?
8. Which accounting exports are required for the first release?
9. Does "GM and DCS can view only" refer specifically to the dashboard/Overview or to additional modules?
10. Which events should create notifications?

# 17. Negative-Permission Test Cases

1. A Requester cannot see the full Overview.
2. A Requester cannot select a funding bank.
3. A Requester cannot approve their own request.
4. A Requester cannot close their Liquidation variance.
5. A GM cannot edit Billing.
6. A GM cannot process DCS Payment.
7. DCS cannot approve a Budget Request.
8. Mitch cannot approve a Budget Request.
9. Mitch cannot process DCS Payment.
10. Mitch cannot access the accounting-only view.
11. A nonadministrator cannot void finalized Billing.
12. A replacement Billing record cannot overwrite the original.
13. An ABR cannot be considered complete without creating its separate disbursement trail.
14. A Liquidation variance cannot close without proof.
15. A payment allocation cannot exceed the received amount.

# 18. Normalized Source Conversation

**Alyssa:** The Administrator should have full access.

The Requester should have access to Budget Requests and Liquidation and should only be able to view Billing. The Requester should not have a dashboard or complete Overview.

The GM Approver should handle Budget Request and Liquidation approval. The GM may view Billing, Collections and Allocation, DCS Payment, and all expenses, but those areas should remain view-only.

DCS may view relevant operational information, but only DCS Payment should be editable.

Mitch may access most operational areas, but Mitch must not approve requests, process DCS Payment, or access the accounting-only view.

BRIDGE needs an administrative or accounting-level view. Whether this is the ordinary Administrator role or a separate BRIDGE role must still be decided.

For Requesters, the only primary actions should be **Save as Draft** and **Submit for Approval**.

Mitch should close Liquidation variances. If unused funds are returned, Mitch should obtain and upload the Requester's proof of deposit. If the Requester is owed reimbursement, Mitch should upload proof that the reimbursement was completed.

Once Billing is sent and finalized, it must no longer be editable. Only the Administrator may cancel or void it. When a replacement is necessary, the original must not be overwritten. Accounting correction may require a Credit Memo, and that Credit Memo must require Administrator approval.

Add receivables aging and Loan Payment.

Create an Approver view.

The accounting view must make transaction data readily available for upload or export to QuickBooks or another accounting system.

The Additional Budget workflow is not working correctly. An ABR was created for an existing shipment BR, but the parallel process did not work. The additional amount did not appear in Liquidation or Billing.

The Requester should not see or choose the requested funding source. The Requester may not know which fund or bank will be used. Apply the same rule to OPEX and similar requests.

A loan Requester may not know the final interest amount. The system must provide a controlled way to handle that instead of requiring the Requester to guess.

When a request is submitted to the GM, clear Approve and Reject controls should appear. Bank information should not be required in the GM approval step.

Approval controls must not appear for unauthorized roles.

The current Requester view still appears to expose some Overview information. Remove or strictly filter it.

The Additional Budget did not appear in Liquidation or Billing. The Collections implementation is also incorrect.

Revise the Budget Request interface according to the earlier meeting requirements.
