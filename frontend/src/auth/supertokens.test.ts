import { beforeEach, describe, expect, it, vi } from 'vitest';

const pw = vi.hoisted(() => ({ createCode: vi.fn(), consumeCode: vi.fn(), resendCode: vi.fn(), clearLoginAttemptInfo: vi.fn() }));
const tp = vi.hoisted(() => ({ getAuthorisationURLWithQueryParamsAndSetState: vi.fn(), signInAndUp: vi.fn() }));
vi.mock('supertokens-web-js/recipe/passwordless', () => ({ default: { init: vi.fn() }, ...pw }));
vi.mock('supertokens-web-js/recipe/thirdparty', () => ({ default: { init: vi.fn() }, ...tp }));
vi.mock('supertokens-web-js/recipe/session', () => ({ default: { init: vi.fn(), doesSessionExist: vi.fn(), signOut: vi.fn() } }));
vi.mock('supertokens-web-js', () => ({ default: { init: vi.fn() } }));

import { finishGoogle, sendOtp, verifyOtp } from './supertokens';

beforeEach(() => vi.clearAllMocks());

describe('phone OTP', () => {
  it('sends the code to the +91 number', async () => {
    pw.createCode.mockResolvedValue({ status: 'OK' });
    await sendOtp('9820011001');
    expect(pw.createCode).toHaveBeenCalledWith({ phoneNumber: '+919820011001' });
  });

  it('surfaces SIGN_IN_UP_NOT_ALLOWED as an ApiError', async () => {
    pw.createCode.mockResolvedValue({ status: 'SIGN_IN_UP_NOT_ALLOWED', reason: 'Blocked (ERR_CODE_1)' });
    await expect(sendOtp('9820011001')).rejects.toMatchObject({ code: 'sign_in_not_allowed', message: 'Blocked (ERR_CODE_1)' });
  });

  it.each([
    [{ status: 'OK' }, 'ok'],
    [{ status: 'INCORRECT_USER_INPUT_CODE_ERROR', failedCodeInputAttemptCount: 1, maximumCodeInputAttempts: 5 }, 'incorrect'],
    [{ status: 'EXPIRED_USER_INPUT_CODE_ERROR' }, 'expired'],
    [{ status: 'RESTART_FLOW_ERROR' }, 'restart'],
    [{ status: 'SIGN_IN_UP_NOT_ALLOWED', reason: 'x' }, 'restart'],
  ])('maps consumeCode %o to %s', async (response, expected) => {
    pw.consumeCode.mockResolvedValue(response);
    expect(await verifyOtp('123456')).toBe(expected);
    expect(pw.consumeCode).toHaveBeenCalledWith({ userInputCode: '123456' });
  });
});

describe('Google callback', () => {
  it.each([
    [{ status: 'OK' }, 'ok'],
    [{ status: 'NO_EMAIL_GIVEN_BY_PROVIDER' }, 'no_email'],
    [{ status: 'SIGN_IN_UP_NOT_ALLOWED', reason: 'x' }, 'not_allowed'],
  ])('maps signInAndUp %o to %s', async (response, expected) => {
    tp.signInAndUp.mockResolvedValue(response);
    expect(await finishGoogle()).toBe(expected);
  });
});
