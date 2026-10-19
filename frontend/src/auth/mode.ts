/** VITE_AUTH_MODE: `supertokens` (real sign-in) or `mock` (Mockoon tokens; OTP code below). */
export const AUTH_MODE: 'mock' | 'supertokens' = import.meta.env.VITE_AUTH_MODE === 'supertokens' ? 'supertokens' : 'mock';
export const MOCK_OTP = '123456';
