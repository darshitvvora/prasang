// Session state for the app. Two modes (VITE_AUTH_MODE):
//  - mock:     Mockoon tokens. Login → mock-artist / mock-planner; new account → mock-new.
//  - supabase: Google Identity Services → supabase.auth.signInWithIdToken (Plan B, E6).
// Either way the API decides who you are via GET /me; this provider only holds the token.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, setTokenProvider } from '../api/client';
import { createMe, getMe } from '../api/endpoints';
import { keys } from '../api/queries';
import type { CreateMeRequest, Me } from '../api/types';
import { createTokenStore } from './authStorage';
import type { AuthStatus } from './paths';

export type SignInResult = { status: 'signedIn'; user: Me } | { status: 'needsProfile' };

interface AuthContextValue {
  status: AuthStatus;
  user: Me | null;
  signInWithGoogle(role: 'artist' | 'planner', opts?: { newAccount?: boolean }): Promise<SignInResult>;
  completeProfile(req: CreateMeRequest): Promise<Me>;
  signOut(): void;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const tokens = createTokenStore(window.localStorage);
const AUTH_MODE = (import.meta.env.VITE_AUTH_MODE as string | undefined) ?? 'mock';

/** GET /me, mapping "signed in but no profile yet" to null instead of an error. */
async function fetchMe(): Promise<Me | null> {
  try {
    return await getMe();
  } catch (e) {
    if (e instanceof ApiError && e.code === 'profile_required') return null;
    throw e;
  }
}

async function obtainToken(role: 'artist' | 'planner', newAccount: boolean): Promise<string> {
  if (AUTH_MODE !== 'mock') {
    throw new ApiError(0, 'auth_not_configured', 'Google sign-in is not configured yet.');
  }
  await new Promise((r) => setTimeout(r, 400)); // feels like a popup round-trip
  return newAccount ? 'mock-new' : `mock-${role}`;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [token, setToken] = useState<string | null>(() => tokens.get());
  setTokenProvider(() => token);

  const me = useQuery({ queryKey: keys.me, queryFn: fetchMe, enabled: token !== null, retry: false, staleTime: 5 * 60_000 });

  const signOut = useCallback(() => {
    tokens.clear();
    setToken(null);
    qc.clear();
  }, [qc]);

  // An expired/invalid token behaves as signed out.
  const expired = me.error instanceof ApiError && me.error.code === 'unauthenticated';
  useEffect(() => {
    if (expired) signOut();
  }, [expired, signOut]);

  let status: AuthStatus;
  if (token === null || me.isError) status = 'signedOut';
  else if (me.isPending) status = 'loading';
  else status = me.data ? 'signedIn' : 'needsProfile';

  const signInWithGoogle = useCallback(async (role: 'artist' | 'planner', opts?: { newAccount?: boolean }): Promise<SignInResult> => {
    const t = await obtainToken(role, opts?.newAccount ?? false);
    tokens.set(t);
    setTokenProvider(() => t); // make the next request use it before React re-renders
    setToken(t);
    const user = await qc.fetchQuery({ queryKey: keys.me, queryFn: fetchMe, staleTime: 0 });
    return user ? { status: 'signedIn', user } : { status: 'needsProfile' };
  }, [qc]);

  const completeProfile = useCallback(async (req: CreateMeRequest) => {
    const user = await createMe(req);
    qc.setQueryData(keys.me, user);
    return user;
  }, [qc]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user: me.data ?? null, signInWithGoogle, completeProfile, signOut }),
    [status, me.data, signInWithGoogle, completeProfile, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
