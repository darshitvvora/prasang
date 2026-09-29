// Pure routing decisions for auth, kept out of components so they are unit-tested.
import type { Me, Role } from '../api/types';

export type AuthStatus = 'loading' | 'signedOut' | 'needsProfile' | 'signedIn';

export function homePathFor(user: Me): string {
  if (user.role === 'artist') return user.artistSlug ? '/artist/dashboard' : '/artist/onboarding';
  return '/planner/dashboard';
}

export type GuardDecision = { type: 'loading' } | { type: 'allow' } | { type: 'redirect'; to: string };

export function guardDecision(status: AuthStatus, user: Me | null, role: Exclude<Role, 'admin'>, currentPath: string): GuardDecision {
  if (status === 'loading') return { type: 'loading' };
  if (status === 'signedOut') return { type: 'redirect', to: `/login?next=${encodeURIComponent(currentPath)}` };
  if (status === 'needsProfile' || !user) return { type: 'redirect', to: '/signup?step=profile' };
  if (user.role === role || user.role === 'admin') return { type: 'allow' };
  return { type: 'redirect', to: homePathFor(user) };
}
