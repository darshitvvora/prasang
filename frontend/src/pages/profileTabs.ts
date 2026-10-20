// Which tabs an artist profile shows (2026-10-20 plans): Free has no media, so only Reviews.
import type { SubscriptionTier } from '../types/artist';

export type ProfileTab = 'media' | 'reviews';

export function profileTabs(tier: SubscriptionTier): { tabs: ProfileTab[]; initial: ProfileTab } {
  return tier === 'free' ? { tabs: ['reviews'], initial: 'reviews' } : { tabs: ['media', 'reviews'], initial: 'media' };
}
