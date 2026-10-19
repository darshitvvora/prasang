// Thin fetch wrapper for the Prasang API. Every non-2xx response becomes an
// ApiError carrying the contract error `code` (see contracts/README.md).
import type { ApiErrorBody } from './types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type TokenProvider = () => string | null | Promise<string | null>;
let tokenProvider: TokenProvider = () => null;
let onUnauthorized: () => void = () => undefined;

/** Registered by AuthProvider so every request carries the current session token.
 *  May be async (Supabase refreshes access tokens before handing them out). */
export function setTokenProvider(fn: TokenProvider): void {
  tokenProvider = fn;
}

/** Called when any request is rejected with 401 `unauthenticated` (expired/revoked session). */
export function setUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn;
}

type QueryValue = string | number | boolean | undefined | null;

export interface ApiInit {
  method?: string;
  body?: unknown;
  query?: Record<string, QueryValue>;
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === '') continue;
    params.append(key, String(value));
  }
  const qs = params.toString();
  return `${BASE_URL}${path}${qs ? `?${qs}` : ''}`;
}

export async function api<T>(path: string, init: ApiInit = {}): Promise<T> {
  const headers = new Headers({ Accept: 'application/json' });
  const token = await tokenProvider();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let body: string | undefined;
  if (init.body !== undefined) {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(init.body);
  }

  let res: Response;
  try {
    res = await fetch(buildUrl(path, init.query), { method: init.method ?? 'GET', headers, body });
  } catch {
    throw new ApiError(0, 'network_error', 'Could not reach Prasang. Check your connection and try again.');
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text ? JSON.parse(text) : undefined;
  } catch {
    parsed = undefined;
  }

  if (!res.ok) {
    const err = (parsed as ApiErrorBody | undefined)?.error;
    if (err?.code === 'unauthenticated') onUnauthorized();
    if (err?.code) throw new ApiError(res.status, err.code, err.message, err.details);
    throw new ApiError(res.status, `http_${res.status}`, 'Something went wrong. Please try again.');
  }
  return parsed as T;
}
