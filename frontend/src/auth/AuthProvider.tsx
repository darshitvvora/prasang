// Session state for the app. Two modes (VITE_AUTH_MODE):
//  - supertokens: self-hosted SuperTokens — phone OTP or Google, session in httpOnly cookies (fetch is patched by the SDK).
//  - mock:        Mockoon tokens. Login → mock-artist / mock-planner; new account → mock-new. OTP code is 123456.
// Either way the API decides who you are via GET /me; this provider only tracks whether a session exists.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, setTokenProvider, setUnauthorizedHandler } from '../api/client';
import { createMe, getMe } from '../api/endpoints';
import { keys } from '../api/queries';
import type { CreateMeRequest, Me } from '../api/types';
import { createTokenStore } from './authStorage';
import { deriveAuthStatus, type AuthStatus } from './paths';
import { AUTH_MODE, MOCK_OTP } from './mode';
import * as st from './supertokens';

export type SignInResult = { status: 'signedIn'; user: Me } | { status: 'needsProfile' };
export type OtpVerifyResult = SignInResult | { status: 'incorrect' | 'expired' | 'restart' };
type Role = 'artist' | 'planner';

interface AuthContextValue {
  mode: 'mock' | 'supertokens';
  status: AuthStatus;
  user: Me | null;
  signInWithGoogle(role: Role, opts?: { newAccount?: boolean }): Promise<SignInResult>;
  sendOtp(phone10: string): Promise<void>;
  verifyOtp(code: string, role: Role, opts?: { newAccount?: boolean }): Promise<OtpVerifyResult>;
  completeGoogleRedirect(): Promise<SignInResult | { status: 'failed'; reason: string }>;
  completeProfile(req: CreateMeRequest): Promise<Me>;
  intendedRole(): Role | null;
  signOut(): void;
  retry(): void;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const tokens = createTokenStore(window.localStorage);
const ROLE_KEY = 'prasang.intendedRole';

/** GET /me, mapping "signed in but no profile yet" to null instead of an error. */
async function fetchMe(): Promise<Me | null> {
  try {
    return await getMe();
  } catch (e) {
    if (e instanceof ApiError && e.code === 'profile_required') return null;
    throw e;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [token, setToken] = useState<string | null>(() => (AUTH_MODE === 'mock' ? tokens.get() : null));
  const [sessionExists, setSessionExists] = useState<boolean | null>(null); // supertokens mode only; null = checking
  setTokenProvider(() => (AUTH_MODE === 'mock' ? token : null));

  useEffect(() => {
    if (AUTH_MODE === 'supertokens') st.hasSession().then(setSessionExists).catch(() => setSessionExists(false));
  }, []);

  const hasSession = AUTH_MODE === 'mock' ? token !== null : sessionExists === true;
  const me = useQuery({ queryKey: keys.me, queryFn: fetchMe, enabled: hasSession, staleTime: 5 * 60_000 });

  const signOut = useCallback(() => {
    tokens.clear();
    setToken(null);
    setSessionExists(false);
    qc.clear();
    if (AUTH_MODE === 'supertokens') st.endSession().catch(() => undefined);
  }, [qc]);

  // Any request rejected with 401 (expired/revoked session) signs the user out.
  useEffect(() => {
    setUnauthorizedHandler(signOut);
    return () => setUnauthorizedHandler(() => undefined);
  }, [signOut]);

  const errorCode = me.error instanceof ApiError ? me.error.code : me.error ? 'unknown_error' : null;
  const status: AuthStatus = AUTH_MODE === 'supertokens' && sessionExists === null
    ? 'loading'
    : deriveAuthStatus({ hasToken: hasSession, isPending: me.isPending, errorCode, hasUser: !!me.data });

  const afterSignIn = useCallback(async (): Promise<SignInResult> => {
    const user = await qc.fetchQuery({ queryKey: keys.me, queryFn: fetchMe, staleTime: 0 });
    return user ? { status: 'signedIn', user } : { status: 'needsProfile' };
  }, [qc]);

  const signInMock = useCallback(async (role: Role, newAccount: boolean) => {
    await new Promise((r) => setTimeout(r, 300));
    const t = newAccount ? 'mock-new' : `mock-${role}`;
    tokens.set(t);
    setTokenProvider(() => t); // next request uses it before React re-renders
    setToken(t);
    return afterSignIn();
  }, [afterSignIn]);

  const signInWithGoogle = useCallback(async (role: Role, opts?: { newAccount?: boolean }): Promise<SignInResult> => {
    if (AUTH_MODE === 'mock') return signInMock(role, opts?.newAccount ?? false);
    sessionStorage.setItem(ROLE_KEY, role);
    await st.startGoogle(); // navigates away to Google
    return new Promise(() => undefined);
  }, [signInMock]);

  const sendOtp = useCallback(async (phone10: string) => {
    if (AUTH_MODE === 'mock') return;
    await st.sendOtp(phone10);
  }, []);

  const verifyOtp = useCallback(async (code: string, role: Role, opts?: { newAccount?: boolean }): Promise<OtpVerifyResult> => {
    sessionStorage.setItem(ROLE_KEY, role);
    if (AUTH_MODE === 'mock') {
      return code === MOCK_OTP ? signInMock(role, opts?.newAccount ?? false) : { status: 'incorrect' };
    }
    const result = await st.verifyOtp(code);
    if (result !== 'ok') return { status: result };
    setSessionExists(true);
    return afterSignIn();
  }, [afterSignIn, signInMock]);

  const completeGoogleRedirect = useCallback(async () => {
    const result = await st.finishGoogle();
    if (result === 'no_email') return { status: 'failed' as const, reason: 'Your Google account did not share an email address.' };
    if (result === 'not_allowed') return { status: 'failed' as const, reason: 'This Google account cannot sign in right now.' };
    setSessionExists(true);
    return afterSignIn();
  }, [afterSignIn]);

  const completeProfile = useCallback(async (req: CreateMeRequest) => {
    try {
      const user = await createMe(req);
      qc.setQueryData(keys.me, user);
      sessionStorage.removeItem(ROLE_KEY);
      return user;
    } catch (e) {
      // Profile already exists (double submit / other tab): use it instead of getting stuck.
      if (e instanceof ApiError && e.code === 'profile_exists') {
        const existing = await qc.fetchQuery({ queryKey: keys.me, queryFn: fetchMe, staleTime: 0 });
        if (existing) return existing;
      }
      throw e;
    }
  }, [qc]);

  const intendedRole = useCallback((): Role | null => {
    const r = sessionStorage.getItem(ROLE_KEY);
    return r === 'artist' || r === 'planner' ? r : null;
  }, []);

  const retry = useCallback(() => { void me.refetch(); }, [me]);

  const value = useMemo<AuthContextValue>(
    () => ({ mode: AUTH_MODE, status, user: me.data ?? null, signInWithGoogle, sendOtp, verifyOtp, completeGoogleRedirect,
      completeProfile, intendedRole, signOut, retry }),
    [status, me.data, signInWithGoogle, sendOtp, verifyOtp, completeGoogleRedirect, completeProfile, intendedRole, signOut, retry],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
