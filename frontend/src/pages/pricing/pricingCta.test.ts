import { describe, expect, it } from 'vitest';
import { pricingCta } from './pricingCta';
import type { Me, PlanUsage } from '../../api/types';

const artist: Me = { id: 'a', email: null, fullName: 'A', phone: null, role: 'artist', avatarUrl: null, artistSlug: 's', createdAt: '' };
const planner: Me = { ...artist, role: 'planner', artistSlug: null };
const usage = (tier: PlanUsage['tier'], status: PlanUsage['status'] = 'active'): PlanUsage =>
  ({ tier, name: tier, status, leadLimitMonthly: 15, leadsUsedThisMonth: 0, leadsRemaining: 15, periodEnd: null, trialEndsAt: null, trialAvailable: false });

describe('pricingCta', () => {
  it('signed-out visitors go to artist signup', () => {
    expect(pricingCta('free', null, undefined)).toEqual({ kind: 'link', label: 'Start free', to: '/signup?role=artist' });
    expect(pricingCta('pro', null, undefined)).toEqual({ kind: 'link', label: 'Get Pro', to: '/signup?role=artist' });
  });
  it('planners see no purchase button (plans are for artists)', () =>
    expect(pricingCta('pro', planner, undefined)).toEqual({ kind: 'none' }));
  it('marks the artist’s current paid plan', () =>
    expect(pricingCta('pro', artist, usage('pro'))).toEqual({ kind: 'current', label: 'Current plan' }));
  it('a trial of a tier can be converted to paid', () =>
    expect(pricingCta('pro', artist, usage('pro', 'trial'))).toEqual({ kind: 'subscribe', label: 'Keep Pro after trial' }));
  it('offers upgrade to higher tiers', () =>
    expect(pricingCta('premium', artist, usage('pro'))).toEqual({ kind: 'subscribe', label: 'Upgrade to Premium' }));
  it('offers switching to a lower paid tier', () =>
    expect(pricingCta('pro', artist, usage('premium'))).toEqual({ kind: 'subscribe', label: 'Switch to Pro' }));
  it('free tier is informational for paying artists', () =>
    expect(pricingCta('free', artist, usage('pro'))).toEqual({ kind: 'none' }));
  it('the free plan is called Basic', () =>
    expect(pricingCta('pro', artist, usage('free', 'free'))).toEqual({ kind: 'subscribe', label: 'Upgrade to Pro' }));
  it('free artists see Current plan on Basic', () =>
    expect(pricingCta('free', artist, usage('free', 'free'))).toEqual({ kind: 'current', label: 'Current plan' }));
});
