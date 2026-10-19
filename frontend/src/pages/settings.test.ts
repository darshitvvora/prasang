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
    expect(reauthStep(err)).toEqual({ kind: 'google' });
  });
  it('treats anything else as a plain error', () => {
    expect(reauthStep(new ApiError(500, 'internal_error', 'boom'))).toEqual({ kind: 'error', message: 'boom' });
    expect(reauthStep(new Error('offline'))).toEqual({ kind: 'error', message: 'Something went wrong. Please try again.' });
  });
});
