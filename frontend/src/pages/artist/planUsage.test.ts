import { describe, expect, it } from 'vitest';
import { leadBanner, usageNote, usagePct } from './planUsage';
import type { PlanUsage } from '../../api/types';

const basic: PlanUsage = { tier: 'pro', name: 'Pro', status: 'active', leadLimitMonthly: 15, leadsUsedThisMonth: 6, leadsRemaining: 9, periodEnd: '2026-10-24', trialEndsAt: null, trialAvailable: false };
const pro: PlanUsage = { ...basic, tier: 'premium', name: 'Premium', leadLimitMonthly: -1, leadsUsedThisMonth: 40, leadsRemaining: null };

describe('usageNote', () => {
  it('shows used out of limit', () => expect(usageNote(basic)).toBe('15 leads/month · 6 used'));
  it('shows unlimited plans', () => expect(usageNote(pro)).toBe('Unlimited leads · 40 this month'));
  it('mentions trial end', () => expect(usageNote({ ...pro, status: 'trial', trialEndsAt: '2026-10-06' })).toBe('Trial ends Oct 6, 2026 · 40 leads this month'));
});

describe('usagePct', () => {
  it('is the share of the cap used', () => expect(usagePct(basic)).toBe(40));
  it('caps at 100 when over quota', () => expect(usagePct({ ...basic, leadsUsedThisMonth: 16, leadsRemaining: 0 })).toBe(100));
  it('is 0 for unlimited plans', () => expect(usagePct(pro)).toBe(0));
});

describe('leadBanner', () => {
  it('counts remaining leads', () => expect(leadBanner(basic)).toEqual({ strong: 'You have 9 leads remaining this month.', rest: 'Upgrade to Premium for unlimited leads.' }));
  it('explains locked leads at the cap', () =>
    expect(leadBanner({ ...basic, leadsUsedThisMonth: 16, leadsRemaining: 0 })).toEqual({ strong: "You've used all 15 leads this month.", rest: 'New leads are locked until you upgrade.' }));
  it('is null on unlimited plans', () => expect(leadBanner(pro)).toBeNull());
});
