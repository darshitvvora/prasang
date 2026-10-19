// SuperTokens (self-hosted) for the web app: phone OTP + Google, sessions in httpOnly cookies.
// supertokens-web-js patches window.fetch, so our API client needs no token handling in this mode.
import SuperTokens from 'supertokens-web-js';
import Session from 'supertokens-web-js/recipe/session';
import Passwordless, { consumeCode, createCode, resendCode } from 'supertokens-web-js/recipe/passwordless';
import ThirdParty, { getAuthorisationURLWithQueryParamsAndSetState, signInAndUp } from 'supertokens-web-js/recipe/thirdparty';
import { ApiError } from '../api/client';

export const AUTH_API_BASE_PATH = '/api/v1/auth';

export function initSupertokens(): void {
  SuperTokens.init({
    appInfo: { appName: 'Prasang', apiDomain: window.location.origin, apiBasePath: AUTH_API_BASE_PATH },
    recipeList: [Session.init(), Passwordless.init(), ThirdParty.init()],
  });
}

export const hasSession = (): Promise<boolean> => Session.doesSessionExist();
export const endSession = (): Promise<void> => Session.signOut();

/** SuperTokens "general errors" carry a user-facing message from our backend (e.g. OTP rate limits). */
function asApiError(err: unknown, code: string): unknown {
  const e = err as { isSuperTokensGeneralError?: boolean; message?: string };
  return e?.isSuperTokensGeneralError ? new ApiError(429, code, e.message ?? 'Please try again later.') : err;
}

export async function sendOtp(phone10: string): Promise<void> {
  const res = await createCode({ phoneNumber: `+91${phone10}` }).catch((err) => { throw asApiError(err, 'otp_rate_limited'); });
  if (res.status === 'SIGN_IN_UP_NOT_ALLOWED') throw new ApiError(403, 'sign_in_not_allowed', res.reason);
}

export async function resendOtp(): Promise<'ok' | 'restart'> {
  const res = await resendCode().catch((err) => { throw asApiError(err, 'otp_rate_limited'); });
  return res.status === 'OK' ? 'ok' : 'restart';
}

export type OtpResult = 'ok' | 'incorrect' | 'expired' | 'restart';

export async function verifyOtp(code: string): Promise<OtpResult> {
  const res = await consumeCode({ userInputCode: code });
  switch (res.status) {
    case 'OK': return 'ok';
    case 'INCORRECT_USER_INPUT_CODE_ERROR': return 'incorrect';
    case 'EXPIRED_USER_INPUT_CODE_ERROR': return 'expired';
    default: return 'restart';
  }
}

/** Redirects the browser to Google. Comes back to /auth/callback/google. */
export async function startGoogle(): Promise<void> {
  const url = await getAuthorisationURLWithQueryParamsAndSetState({
    thirdPartyId: 'google',
    frontendRedirectURI: `${window.location.origin}/auth/callback/google`,
  });
  window.location.assign(url);
}

export async function finishGoogle(): Promise<'ok' | 'no_email' | 'not_allowed'> {
  const res = await signInAndUp();
  if (res.status === 'OK') return 'ok';
  if (res.status === 'NO_EMAIL_GIVEN_BY_PROVIDER') return 'no_email';
  return 'not_allowed';
}
