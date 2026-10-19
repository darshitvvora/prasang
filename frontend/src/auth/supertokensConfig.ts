// Where the SuperTokens SDK sends auth calls. Default: same origin (Vite proxy locally, /api proxy in production).
// For a split deploy (prasang.in + api.prasang.in) set VITE_API_DOMAIN and VITE_SESSION_DOMAIN=.prasang.in.
export interface AuthEnv { VITE_API_DOMAIN?: string; VITE_SESSION_DOMAIN?: string }

export function supertokensAppInfo(env: AuthEnv, origin: string) {
  return {
    appInfo: { appName: 'Prasang', apiDomain: env.VITE_API_DOMAIN || origin, apiBasePath: '/api/v1/auth' },
    sessionTokenBackendDomain: env.VITE_SESSION_DOMAIN || undefined,
  };
}
