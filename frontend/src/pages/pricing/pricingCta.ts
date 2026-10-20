// What the call-to-action on each pricing card should do for the current viewer.
import type { Me, PlanUsage } from '../../api/types';
import type { SubscriptionTier } from '../../types/artist';

const ORDER: SubscriptionTier[] = ['free', 'pro', 'premium'];
const NAME: Record<SubscriptionTier, string> = { free: 'Basic', pro: 'Pro', premium: 'Premium' }; // 'free' = the Basic plan

export type Cta =
  | { kind: 'link'; label: string; to: string }
  | { kind: 'current'; label: string }
  | { kind: 'subscribe'; label: string }
  | { kind: 'none' };

export function pricingCta(tier: SubscriptionTier, user: Me | null, plan: PlanUsage | undefined): Cta {
  if (!user) return { kind: 'link', label: tier === 'free' ? 'Start free' : `Get ${NAME[tier]}`, to: '/signup?role=artist' };
  if (user.role !== 'artist' || !plan) return { kind: 'none' };
  if (tier === plan.tier) {
    if (plan.status === 'trial') return { kind: 'subscribe', label: `Keep ${NAME[tier]} after trial` };
    return { kind: 'current', label: 'Current plan' };
  }
  if (tier === 'free') return { kind: 'none' };
  return { kind: 'subscribe', label: ORDER.indexOf(tier) > ORDER.indexOf(plan.tier) ? `Upgrade to ${NAME[tier]}` : `Switch to ${NAME[tier]}` };
}
