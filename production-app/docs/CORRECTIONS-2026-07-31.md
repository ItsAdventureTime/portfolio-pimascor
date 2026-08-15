# Corrections applied on 2026-07-31

This correction implements Sections 2 onward of the owner-provided test
correction document. Section 1's proposed user-role redesign is not applied.

## Completed behavior

- The Sales Quotation print preview remains data-driven and now uses the
  owner-provided revised quotation terms. Shipment summary fields, charge-line
  currencies, amounts, totals, client, and approval data are populated from the
  quotation record, not from a static PDF.
- A signed quotation with stored object metadata opens in the protected viewer.
  A demo-baseline row that has only a filename remains visibly unavailable until
  a real signed PDF/JPEG/PNG is uploaded; the UI no longer implies that such
  metadata is an openable file.
- Every authenticated role can view an authorized supporting file. Mich, GM,
  DCS, and Admin can download it through a separate audited endpoint.
- Admin now opens directly in the workspace-selector controls, where Mich is a
  selectable workspace alongside the other existing roles.
- GM can perform a DCS Payment override. A GM action or recorded payment must
  include a reason of at least ten characters, and the audit event is prefixed
  `GM_PAYMENT_OVERRIDE` rather than being recorded as a DCS action.
- Shipment Profitability and complete local-record exports are authorized only
  for Mich, GM, DCS, and Admin. Requesters are denied by the API as well as
  omitted from the Shipment Profitability navigation.

## Demo deployment

Transfer from this Mac:

```bash
/Users/jk.deguzman/dev/bridge-ph_Dashboard/production-app/infra/scripts/deploy-demo-vps.sh
```

Then, after signing in to the VPS:

```bash
cd /var/home/jk/bridge-ph/pimascor-demo/source && ./infra/scripts/update-demo.sh --source /var/home/jk/bridge-ph/pimascor-demo/source --api-image-archive /var/home/jk/bridge-ph/pimascor-demo/release-artifacts/COMMIT/api-image.tar --web-dist /var/home/jk/bridge-ph/pimascor-demo/release-artifacts/COMMIT/web-dist && bash ./infra/scripts/reconcile-demo-web-root.sh
```

The current demo intentionally keeps complete local-record archive generation
disabled. Enable the export worker and private object-store retention only in
the production configuration after its storage, email, and retention controls
have been reviewed.

## References

- Revised visual and terms reference: `docs/reference/AAA_FORMAT_QUOTATION_revised.pdf`
- Authorization and object-access approach: OWASP Authorization and File Upload
  Cheat Sheets.
