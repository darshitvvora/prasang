import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { getArtist, searchArtists, updateLead, uploadToUrl } from './endpoints';
import { setTokenProvider } from './client';

let calls: [string, RequestInit | undefined][] = [];
beforeEach(() => {
  calls = [];
  setTokenProvider(() => 'mock-artist');
  globalThis.fetch = vi.fn(async (input: string, init?: RequestInit) => {
    calls.push([input, init]);
    return new Response('{}', { status: 200 });
  }) as unknown as typeof fetch;
});
afterEach(() => vi.restoreAllMocks());

it('getArtist URL-encodes the slug', async () => {
  await getArtist('dj krish/x');
  expect(calls[0][0]).toBe('/api/v1/artists/dj%20krish%2Fx');
});

it('searchArtists passes filters as query params', async () => {
  await searchArtists({ artistType: 'dj', city: 'Pune', page: 1 });
  expect(calls[0][0]).toBe('/api/v1/search/artists?artistType=dj&city=Pune&page=1');
});

it('updateLead PATCHes the status', async () => {
  await updateLead('lead-015', { status: 'contacted' });
  expect(calls[0][0]).toBe('/api/v1/leads/lead-015');
  expect(calls[0][1]?.method).toBe('PATCH');
});

it('uploadToUrl PUTs the file to the presigned URL without our bearer token', async () => {
  const file = new Blob(['x'], { type: 'image/jpeg' });
  await uploadToUrl({ uploadUrl: 'https://r2.example/k?sig=1', storageKey: 'k', expiresAt: '', headers: { 'Content-Type': 'image/jpeg' } }, file);
  const [url, init] = calls[0];
  expect(url).toBe('https://r2.example/k?sig=1');
  expect(init?.method).toBe('PUT');
  expect(new Headers(init?.headers).get('Authorization')).toBeNull();
  expect(new Headers(init?.headers).get('Content-Type')).toBe('image/jpeg');
});

it('uploadToUrl rejects when storage refuses the upload', async () => {
  globalThis.fetch = vi.fn(async () => new Response('denied', { status: 403 })) as unknown as typeof fetch;
  const file = new Blob(['x']);
  await expect(uploadToUrl({ uploadUrl: 'https://r2.example/k', storageKey: 'k', expiresAt: '', headers: {} }, file))
    .rejects.toMatchObject({ code: 'upload_failed' });
});
