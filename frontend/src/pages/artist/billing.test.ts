import { describe, expect, it } from 'vitest';
import { formatBillingRow } from './billing';
import type { BillingItem } from '../../api/types';

const item: BillingItem = {
  id: 'p1', paidAt: '2026-10-05T06:30:00Z', tier: 'pro', billingCycle: 'monthly', amount: 599, currency: 'INR',
  status: 'paid', receiptUrl: 'https://rzp.io/i/inv_1',
};

describe('formatBillingRow', () => {
  it('formats a paid charge', () => {
    expect(formatBillingRow(item)).toEqual({
      date: 'Oct 5, 2026', plan: 'Pro · Monthly', amount: '₹599', status: 'Paid', receiptUrl: 'https://rzp.io/i/inv_1',
    });
  });
  it('formats a failed annual charge without receipt', () => {
    expect(formatBillingRow({ ...item, amount: 5999, billingCycle: 'annual', status: 'failed', receiptUrl: null })).toEqual({
      date: 'Oct 5, 2026', plan: 'Pro · Annual', amount: '₹5,999', status: 'Failed', receiptUrl: null,
    });
  });
});
