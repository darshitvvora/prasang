// Account deletion: the API asks for a fresh sign-in (403 reauth_required) and says how — OTP or Google.
import { ApiError } from '../api/client';
import type { ReauthDetails } from '../api/types';

export type ReauthStep = { kind: 'otp'; phone: string } | { kind: 'google' } | { kind: 'error'; message: string };

export const CONFIRM_DELETE_KEY = 'prasang.confirmDelete';

export function reauthStep(err: unknown): ReauthStep {
  if (err instanceof ApiError && err.code === 'reauth_required') {
    const d = err.details as unknown as ReauthDetails;
    if (d?.method === 'phone' && d.phone) return { kind: 'otp', phone: d.phone };
    if (d?.method === 'google') return { kind: 'google' };
  }
  if (err instanceof ApiError) return { kind: 'error', message: err.message };
  return { kind: 'error', message: 'Something went wrong. Please try again.' };
}
