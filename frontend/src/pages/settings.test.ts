import { describe, expect, it } from 'vitest';
import { ApiError } from '../api/client';
import { reauthStep } from './settings';

describe('reauthStep', () => {
  it('asks phone users for a fresh OTP', () => {
    const err = new ApiError(403, 'reauth_required', 'confirm', { method: 'phone', phone: '9820011111' });
    expect(reauthStep(err)).toEqual({ kind: 'otp', phone: '9820011111' });
  });
  it('sends Google users back through Google', () => {
    const err = new ApiError(403, 'reauth_required', 'confirm', { method: 'google', email: 'a@b.com' });
    expect(reauthStep(err)).toEqual({ kind: 'google', email: 'a@b.com' });
  });
  it('treats anything else as a plain error', () => {
    expect(reauthStep(new ApiError(500, 'internal_error', 'boom'))).toEqual({ kind: 'error', message: 'boom' });
    expect(reauthStep(new Error('offline'))).toEqual({ kind: 'error', message: 'Something went wrong. Please try again.' });
  });
});

describe('sameAccount', () => {
  it('only allows deletion when Google re-confirmed the same account', async () => {
    const { sameAccount } = await import('./settings');
    expect(sameAccount('a@b.com', { email: 'a@b.com' })).toBe(true);
    expect(sameAccount('a@b.com', { email: 'other@b.com' })).toBe(false);
    expect(sameAccount('1', { email: 'a@b.com' })).toBe(false);
    expect(sameAccount(null, { email: 'a@b.com' })).toBe(false);
  });
});
