import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, setTokenProvider } from './client';

type FetchArgs = [input: string, init?: RequestInit];
let calls: FetchArgs[] = [];

function mockFetch(response: Response | Error) {
  calls = [];
  globalThis.fetch = vi.fn(async (input: string, init?: RequestInit) => {
    calls.push([input, init]);
    if (response instanceof Error) throw response;
    return response;
  }) as unknown as typeof fetch;
}

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

beforeEach(() => setTokenProvider(() => null));
afterEach(() => vi.restoreAllMocks());

describe('api()', () => {
  it('parses a JSON 200 body', async () => {
    mockFetch(json(200, { items: [1, 2] }));
    await expect(api<{ items: number[] }>('/artists/featured')).resolves.toEqual({ items: [1, 2] });
    expect(calls[0][0]).toBe('/api/v1/artists/featured');
  });

  it('returns undefined for 204', async () => {
    mockFetch(new Response(null, { status: 204 }));
    await expect(api('/artists/x/contact-click', { method: 'POST' })).resolves.toBeUndefined();
  });

  it('throws ApiError carrying the contract error code', async () => {
    mockFetch(json(404, { error: { code: 'artist_not_found', message: 'No artist found', details: {} } }));
    const err = await api('/artists/nope').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 404, code: 'artist_not_found', message: 'No artist found' });
  });

  it('maps non-JSON error responses to http_<status>', async () => {
    mockFetch(new Response('<html>Bad Gateway</html>', { status: 502 }));
    await expect(api('/me')).rejects.toMatchObject({ status: 502, code: 'http_502' });
  });

  it('maps network failures to network_error with status 0', async () => {
    mockFetch(new TypeError('Failed to fetch'));
    await expect(api('/me')).rejects.toMatchObject({ status: 0, code: 'network_error' });
  });

  it('sends the bearer token from the token provider', async () => {
    setTokenProvider(() => 'mock-artist');
    mockFetch(json(200, {}));
    await api('/me');
    expect(new Headers(calls[0][1]?.headers).get('Authorization')).toBe('Bearer mock-artist');
  });

  it('omits Authorization when there is no token', async () => {
    mockFetch(json(200, {}));
    await api('/me');
    expect(new Headers(calls[0][1]?.headers).has('Authorization')).toBe(false);
  });

  it('serialises query params, skipping undefined and empty values', async () => {
    mockFetch(json(200, {}));
    await api('/search/artists', { query: { city: 'Mumbai', area: '', artistType: undefined, verifiedOnly: true, page: 2 } });
    expect(calls[0][0]).toBe('/api/v1/search/artists?city=Mumbai&verifiedOnly=true&page=2');
  });

  it('JSON-encodes the body and sets Content-Type', async () => {
    mockFetch(json(201, { ok: true }));
    await api('/leads', { method: 'POST', body: { artistId: 'art-001' } });
    const init = calls[0][1]!;
    expect(init.method).toBe('POST');
    expect(init.body).toBe('{"artistId":"art-001"}');
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json');
  });
});

import { setUnauthorizedHandler } from './client';

describe('api() auth hooks (review fixes)', () => {
  it('awaits an async token provider (Supabase refreshes tokens asynchronously)', async () => {
    setTokenProvider(async () => 'fresh-token');
    mockFetch(json(200, {}));
    await api('/me');
    expect(new Headers(calls[0][1]?.headers).get('Authorization')).toBe('Bearer fresh-token');
  });

  it('calls the unauthorized handler when any request gets 401 unauthenticated', async () => {
    const seen: string[] = [];
    setUnauthorizedHandler(() => seen.push('signed-out'));
    mockFetch(json(401, { error: { code: 'unauthenticated', message: 'Please sign in', details: {} } }));
    await expect(api('/leads/artist')).rejects.toMatchObject({ code: 'unauthenticated' });
    expect(seen).toEqual(['signed-out']);
    setUnauthorizedHandler(() => undefined);
  });

  it('does not call the unauthorized handler for other errors', async () => {
    const seen: string[] = [];
    setUnauthorizedHandler(() => seen.push('x'));
    mockFetch(json(403, { error: { code: 'forbidden', message: 'No', details: {} } }));
    await api('/leads/artist').catch(() => undefined);
    expect(seen).toEqual([]);
    setUnauthorizedHandler(() => undefined);
  });
});
