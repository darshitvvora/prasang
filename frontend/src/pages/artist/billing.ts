import { formatDate } from '../../api/format';
import type { BillingItem } from '../../api/types';

export interface BillingRow { date: string; plan: string; amount: string; status: string; receiptUrl: string | null }

const TIER = { basic: 'Basic', pro: 'Pro', premium: 'Premium' } as const;
const istDate = (iso: string) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date(iso));

export function formatBillingRow(item: BillingItem): BillingRow {
  return {
    date: formatDate(istDate(item.paidAt)),
    plan: `${TIER[item.tier]} · ${item.billingCycle === 'annual' ? 'Annual' : 'Monthly'}`,
    amount: `₹${item.amount.toLocaleString('en-IN')}`,
    status: item.status === 'paid' ? 'Paid' : 'Failed',
    receiptUrl: item.receiptUrl,
  };
}
