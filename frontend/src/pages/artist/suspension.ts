import type { ArtistProfile } from '../../api/types';

export function suspensionMessage(p: Pick<ArtistProfile, 'suspended' | 'suspensionReason'>): string | null {
  if (!p.suspended) return null;
  return p.suspensionReason ? `Your profile is hidden from planners: ${p.suspensionReason}.` : 'Your profile is hidden from planners.';
}
