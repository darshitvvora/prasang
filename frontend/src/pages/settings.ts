// Account deletion: the API asks for a fresh sign-in (403 reauth_required) and says how — OTP or Google.
import { ApiError } from '../api/client';
import type { ReauthDetails } from '../api/types';

export type ReauthStep = { kind: 'otp'; phone: string } | { kind: 'google'; email: string | null } | { kind: 'error'; message: string };

export const CONFIRM_DELETE_KEY = 'prasang.confirmDelete';

export function reauthStep(err: unknown): ReauthStep {
  if (err instanceof ApiError && err.code === 'reauth_required') {
    const d = err.details as unknown as ReauthDetails;
    if (d?.method === 'phone' && d.phone) return { kind: 'otp', phone: d.phone };
    if (d?.method === 'google') return { kind: 'google', email: d.email };
  }
  if (err instanceof ApiError) return { kind: 'error', message: err.message };
  return { kind: 'error', message: 'Something went wrong. Please try again.' };
}

/** After the Google round-trip, delete only if Google confirmed the account that asked (another account could be picked). */
export function sameAccount(expectedEmail: string | null, user: { email: string | null }): boolean {
  return !!expectedEmail && expectedEmail.includes('@') && expectedEmail === user.email;
}
