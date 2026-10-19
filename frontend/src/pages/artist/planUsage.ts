// Wording for plan usage shown in the artist sidebar and lead banners.
import type { PlanUsage } from '../../api/types';
import { formatDate } from '../../api/format';

const unlimited = (p: PlanUsage) => p.leadLimitMonthly < 0;

export function usageNote(p: PlanUsage): string {
  if (p.status === 'trial' && p.trialEndsAt) return `Trial ends ${formatDate(p.trialEndsAt)} · ${p.leadsUsedThisMonth} leads this month`;
  if (unlimited(p)) return `Unlimited leads · ${p.leadsUsedThisMonth} this month`;
  return `${p.leadLimitMonthly} leads/month · ${p.leadsUsedThisMonth} used`;
}

export function usagePct(p: PlanUsage): number {
  if (unlimited(p) || p.leadLimitMonthly === 0) return 0;
  return Math.min(100, Math.round((p.leadsUsedThisMonth / p.leadLimitMonthly) * 100));
}

export function leadBanner(p: PlanUsage): { strong: string; rest: string } | null {
  if (unlimited(p)) return null;
  if ((p.leadsRemaining ?? 0) <= 0) {
    return { strong: `You've used all ${p.leadLimitMonthly} leads this month.`, rest: 'New leads are locked until you upgrade.' };
  }
  return { strong: `You have ${p.leadsRemaining} leads remaining this month.`, rest: 'Upgrade to Pro for unlimited leads.' };
}
