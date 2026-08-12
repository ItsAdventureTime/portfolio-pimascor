import type { AttentionItem, BudgetRequest, PageId, Role, Tone } from './types'

export const pageMeta: Record<PageId, { title: string; description: string }> = {
  dashboard: { title: 'Shipment Profitability', description: 'Compare approved selling, actual spending, profit, liquidation, and collections.' },
  quotations: { title: 'Sales Quotations', description: 'Start each shipment with an approved and client-accepted quotation.' },
  'budget-requests': { title: 'Budget Requests', description: 'Create and follow shipment funding from draft through payment.' },
  approvals: { title: 'Approval', description: 'Review submitted requests and record attributable approval decisions.' },
  releases: { title: 'DCS for Payment', description: 'Pay, hold, return, and annotate every approved payable in one queue.' },
  liquidation: { title: 'Liquidation', description: 'Match released funds to actual spend and resolve every variance.' },
  billing: { title: 'Billing', description: 'Prepare Billing, obtain GM approval, finalize, and trace every controlled revision.' },
  collections: { title: 'Client Payments', description: 'Record money received and allocate it safely across Billing balances.' },
  'payment-requests': { title: 'Request for Payment', description: 'Create and follow OPEX, Marketing, Loan Payment, and Other requests in one place.' },
  opex: { title: 'OPEX', description: 'Manage operating expense requests, approval, disbursement, and history.' },
  marketing: { title: 'Marketing', description: 'Manage campaign requests, approval, disbursement, and history.' },
  'loan-payments': { title: 'Loan Payments', description: 'Request, approve, and pay company loan obligations.' },
  accounting: { title: 'Accounting Export', description: 'Export attributable operational events for accountant-reviewed mapping.' },
  'clients-documents': { title: 'Clients & Documents', description: 'Find client records and protected supporting documents.' },
  support: { title: 'Support', description: 'Ask questions, share suggestions, and track help requests with a ticket number.' },
  admin: { title: 'Administration', description: 'Manage people, permissions, funding sources, and system controls.' },
  login: { title: 'Sign in', description: 'Secure access to PIMASCOR Operational Control.' },
}

export const roleDescriptions: Record<Role, string> = {
  Admin: 'Superuser access to every workflow and administration control',
  Requester: 'Creates shipment budgets and liquidation records',
  GM: 'Reviews and decides requests',
  DCS: 'CEO payment queue and money movement',
  Mich: 'Creates payment requests and manages billing, collections, and liquidation closure',
}

export const budgetRequests: BudgetRequest[] = [
  {
    id: 'br-1', reference: 'BR-0726-159', date: 'Jul 18, 2026', client: 'Archipelago Cargo Trading',
    shipment: 'Manila to Davao • MV Isla Verde', requester: 'Rob Pulido', buying: 76300, selling: 96360,
    approval: 'Approved', release: 'Released', liquidation: 'Partial', billing: 'Partially collected', updated: '18 min ago',
  },
  {
    id: 'br-2', reference: 'BR-0726-164', date: 'Jul 19, 2026', client: 'Harborline Foods Inc.',
    shipment: 'Cebu to Manila • Reefer service', requester: 'Lea Santos', buying: 58200, selling: 78800,
    approval: 'Pending GM', release: 'Unreleased', liquidation: 'Not started', billing: 'Not billed', updated: '42 min ago',
  },
  {
    id: 'br-3', reference: 'BR-0726-167', date: 'Jul 19, 2026', client: 'Pacific Buildworks',
    shipment: 'Batangas port handling', requester: 'Rob Pulido', buying: 42600, selling: 59000,
    approval: 'Rejected', release: 'Unreleased', liquidation: 'Not started', billing: 'Not billed', updated: '2 hr ago',
  },
  {
    id: 'br-4', reference: 'BR-0726-171', date: 'Jul 20, 2026', client: 'Southern Isles Retail',
    shipment: 'Manila to Iloilo • Consolidated cargo', requester: 'Nina Reyes', buying: 91500, selling: 124000,
    approval: 'Draft', release: 'Unreleased', liquidation: 'Not started', billing: 'Not billed', updated: '3 hr ago',
  },
  {
    id: 'br-5', reference: 'BR-0626-141', date: 'Jun 27, 2026', client: 'Archipelago Cargo Trading',
    shipment: 'Subic port services', requester: 'Lea Santos', buying: 63800, selling: 86200,
    approval: 'Approved', release: 'Partially released', liquidation: 'Ready to close', billing: 'Billed', updated: 'Yesterday',
  },
]

export const attentionByRole: Record<Role, AttentionItem[]> = {
  Admin: [
    { id: 'a1', tone: 'warning', eyebrow: 'Approval waiting 18 hours', title: 'BR-0726-164 needs a decision', detail: 'Harborline Foods Inc. • PHP 58,200 buying budget', age: '18h', action: 'Review request', page: 'approvals' },
    { id: 'a2', tone: 'danger', eyebrow: 'Overdue receivable', title: 'SOA-0382 is 34 days past due', detail: 'Archipelago Cargo Trading • PHP 12,400 remaining', age: '34d', action: 'Open collection', page: 'collections' },
    { id: 'a3', tone: 'info', eyebrow: 'Ready for closure', title: 'BR-0626-141 liquidation is complete', detail: 'All receipts and return proof are present', age: '2h', action: 'Review closure', page: 'liquidation' },
  ],
  Requester: [
    { id: 'r1', tone: 'danger', eyebrow: 'Returned for correction', title: 'BR-0726-167 needs your update', detail: 'GM requested a clearer breakdown of port handling charges', age: '2h', action: 'Correct request', page: 'budget-requests' },
    { id: 'r2', tone: 'warning', eyebrow: 'Missing receipt', title: 'BR-0726-159 liquidation is incomplete', detail: 'PHP 8,750 of released funds still needs support', age: '1d', action: 'Add actual spend', page: 'liquidation' },
  ],
  GM: [
    { id: 'g1', tone: 'warning', eyebrow: 'Decision required', title: 'BR-0726-164 awaits approval', detail: 'Harborline Foods Inc. • Projected profit PHP 20,600', age: '18h', action: 'Review request', page: 'approvals' },
    { id: 'g2', tone: 'info', eyebrow: 'Marketing request', title: 'MKT-0726-019 awaits approval', detail: 'Maritime Expo booth materials • PHP 48,000', age: '4h', action: 'Review request', page: 'payment-requests' },
    { id: 'g3', tone: 'info', eyebrow: 'Loan payment request', title: 'LOAN-2026-00001 awaits approval', detail: 'Demo Development Bank • PHP 44,000', age: '2h', action: 'Review request', page: 'payment-requests' },
  ],
  DCS: [
    { id: 'd1', tone: 'warning', eyebrow: 'Approved and unpaid', title: 'BR-0726-172 is ready for payment', detail: 'Pacific Buildworks • PHP 66,000 approved', age: '3h', action: 'Open payment', page: 'releases' },
    { id: 'd2', tone: 'info', eyebrow: 'OPEX payment', title: 'OPEX-0726-031 is ready', detail: 'Annual software subscription • PHP 24,900', age: '1h', action: 'Open payment', page: 'releases' },
    { id: 'd3', tone: 'info', eyebrow: 'Loan payment', title: 'LOAN-2026-00002 is approved', detail: 'Demo Equipment Finance • PHP 72,500', age: '3h', action: 'Open payment', page: 'releases' },
  ],
  Mich: [
    { id: 'm1', tone: 'danger', eyebrow: 'Overdue receivable', title: 'SOA-0382 has PHP 12,400 remaining', detail: 'Archipelago Cargo Trading • 31 to 60 days', age: '34d', action: 'Open allocation', page: 'collections' },
    { id: 'm2', tone: 'info', eyebrow: 'Ready for closure', title: 'BR-0626-141 is fully supported', detail: 'Return proof verified • PHP 3,500 returned', age: '2h', action: 'Close liquidation', page: 'liquidation' },
    { id: 'm3', tone: 'warning', eyebrow: 'Ready to bill', title: 'BR-0726-172 selling lines are approved', detail: 'Pacific Buildworks • PHP 84,500 selling amount', age: '3h', action: 'Prepare Billing', page: 'billing' },
  ],
}

export const kpis = [
  { label: 'Needs attention', value: '7', detail: 'Across your permitted workspaces', tone: 'warning' as Tone, trend: '2 due today' },
  { label: 'Budget released', value: '₱1.84M', detail: 'July 2026', tone: 'brand' as Tone, trend: '82% liquidated' },
  { label: 'Projected profit', value: '₱486.2K', detail: 'Approved selling minus buying', tone: 'info' as Tone, trend: '18.7% margin' },
  { label: 'Actual profit', value: '₱392.8K', detail: 'Billed revenue minus actual cost', tone: 'success' as Tone, trend: '16.2% margin' },
  { label: 'Outstanding A/R', value: '₱614.5K', detail: 'Net of allocated collections', tone: 'danger' as Tone, trend: '₱96.4K overdue' },
]

export const monthlyProfit = [
  { month: 'Feb', projected: 292, actual: 248 },
  { month: 'Mar', projected: 326, actual: 301 },
  { month: 'Apr', projected: 355, actual: 338 },
  { month: 'May', projected: 391, actual: 342 },
  { month: 'Jun', projected: 438, actual: 376 },
  { month: 'Jul', projected: 486, actual: 393 },
]

export const aging = [
  { label: 'Current', value: 332100, percent: 54, tone: 'info' as Tone },
  { label: '1–30 days', value: 185980, percent: 30, tone: 'warning' as Tone },
  { label: '31–60 days', value: 64120, percent: 11, tone: 'danger' as Tone },
  { label: '61–90 days', value: 21300, percent: 3, tone: 'danger' as Tone },
  { label: 'Over 90 days', value: 11000, percent: 2, tone: 'danger' as Tone },
]

export const approvalQueue = [
  { id: 'ap-1', type: 'Budget Request', reference: 'BR-0726-164', owner: 'Lea Santos', party: 'Harborline Foods Inc.', purpose: 'Cebu to Manila reefer service', amount: 58200, selling: 78800, age: '18h', documents: 3, status: 'Pending GM' },
  { id: 'ap-2', type: 'Marketing', reference: 'MKT-0726-019', owner: 'Nina Reyes', party: 'Maritime Expo 2026', purpose: 'Booth materials and event fees', amount: 48000, selling: 0, age: '4h', documents: 2, status: 'Pending GM' },
  { id: 'ap-3', type: 'OPEX', reference: 'OPEX-0726-033', owner: 'Rob Pulido', party: 'Metro Office Solutions', purpose: 'Printer repair and replacement parts', amount: 13800, selling: 0, age: '1h', documents: 1, status: 'Pending GM' },
  { id: 'ap-4', type: 'Loan Payment', reference: 'LOAN-DEMO-00002', owner: 'Rob Pulido', party: 'Demo Development Bank', purpose: 'Equipment-loan installment', amount: 64800, selling: 0, age: '2h', documents: 1, status: 'Pending GM' },
]

export const releaseQueue = [
  { reference: 'BR-0726-172', client: 'Pacific Buildworks', requester: 'Rob Pulido', approved: 66000, released: 0, status: 'Unreleased', approvedAt: 'Jul 20 • 08:42' },
  { reference: 'BR-0726-159', client: 'Archipelago Cargo Trading', requester: 'Rob Pulido', approved: 76300, released: 76300, status: 'Released', approvedAt: 'Jul 18 • 14:22' },
  { reference: 'BR-0726-155', client: 'Southern Isles Retail', requester: 'Nina Reyes', approved: 120000, released: 85000, status: 'Partially released', approvedAt: 'Jul 17 • 10:08' },
]

export const liquidationRows = [
  { reference: 'BR-0626-141', requester: 'Lea Santos', released: 63800, actual: 60300, returned: 3500, reimbursed: 0, status: 'Ready to close', age: '9d' },
  { reference: 'BR-0726-159', requester: 'Rob Pulido', released: 76300, actual: 67550, returned: 0, reimbursed: 0, status: 'Partial', age: '2d' },
  { reference: 'BR-0726-155', requester: 'Nina Reyes', released: 85000, actual: 0, returned: 0, reimbursed: 0, status: 'Not started', age: '3d' },
]

export const billingRows = [
  { reference: 'BR-0726-172', client: 'Pacific Buildworks', selling: 84500, billed: 0, due: 'Not set', status: 'Ready to bill' },
  { reference: 'BR-0726-164', client: 'Harborline Foods Inc.', selling: 78800, billed: 0, due: 'Not set', status: 'Awaiting approval' },
  { reference: 'BR-0726-159', client: 'Archipelago Cargo Trading', selling: 96360, billed: 96360, due: 'Aug 15, 2026', status: 'Partially collected' },
]

export const receivables = [
  { soa: 'SOA-0382', shipment: 'BR-0726-159', client: 'Archipelago Cargo Trading', due: 'Jun 16, 2026', netDue: 95800, collected: 83400, remaining: 12400, aging: '31–60 days' },
  { soa: 'SOA-0391', shipment: 'BR-0626-141', client: 'Archipelago Cargo Trading', due: 'Jul 25, 2026', netDue: 86200, collected: 0, remaining: 86200, aging: 'Current' },
  { soa: 'SOA-0396', shipment: 'BR-0726-148', client: 'Southern Isles Retail', due: 'Jul 8, 2026', netDue: 124500, collected: 65000, remaining: 59500, aging: '1–30 days' },
]

export function toneForStatus(status: string): Tone {
  const value = status.toLowerCase()
  if (value.includes('reject') || value.includes('over') || value.includes('void')) return 'danger'
  if (value.includes('pending') || value.includes('partial') || value.includes('ready') || value.includes('unreleased')) return 'warning'
  if (value.includes('approved') || value.includes('released') || value.includes('closed') || value.includes('collected')) return 'success'
  if (value.includes('billed')) return 'info'
  return 'neutral'
}
