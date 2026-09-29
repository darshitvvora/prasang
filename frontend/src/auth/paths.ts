// Pure routing decisions for auth, kept out of components so they are unit-tested.
import type { Me, Role } from '../api/types';

export type AuthStatus = 'loading' | 'signedOut' | 'needsProfile' | 'signedIn' | 'error';

/** Only a 401 means "signed out"; outages keep the session and surface as 'error'. */
export function deriveAuthStatus(s: { hasToken: boolean; isPending: boolean; errorCode: string | null; hasUser: boolean }): AuthStatus {
  if (!s.hasToken) return 'signedOut';
  if (s.errorCode === 'unauthenticated') return 'signedOut';
  if (s.errorCode) return 'error';
  if (s.isPending) return 'loading';
  return s.hasUser ? 'signedIn' : 'needsProfile';
}

export function homePathFor(user: Me): string {
  if (user.role === 'artist') return user.artistSlug ? '/artist/dashboard' : '/artist/onboarding';
  return '/planner/dashboard';
}

export type GuardDecision = { type: 'loading' } | { type: 'error' } | { type: 'allow' } | { type: 'redirect'; to: string };

export function guardDecision(status: AuthStatus, user: Me | null, role: Exclude<Role, 'admin'>, currentPath: string): GuardDecision {
  if (status === 'loading') return { type: 'loading' };
  if (status === 'error') return { type: 'error' };
  const next = encodeURIComponent(currentPath);
  if (status === 'signedOut') return { type: 'redirect', to: `/login?next=${next}` };
  if (status === 'needsProfile' || !user) return { type: 'redirect', to: `/signup?step=profile&next=${next}` };
  if (user.role === 'artist' && role === 'artist' && !user.artistSlug && !currentPath.startsWith('/artist/onboarding')) {
    return { type: 'redirect', to: '/artist/onboarding' };
  }
  if (user.role === role || user.role === 'admin') return { type: 'allow' };
  return { type: 'redirect', to: homePathFor(user) };
}
