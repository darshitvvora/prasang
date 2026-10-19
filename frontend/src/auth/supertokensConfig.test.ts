import { expect, it } from 'vitest';
import { supertokensAppInfo } from './supertokensConfig';

it('defaults to the page origin (same-origin /api proxy)', () => {
  expect(supertokensAppInfo({}, 'http://localhost:5173')).toEqual({
    appInfo: { appName: 'Prasang', apiDomain: 'http://localhost:5173', apiBasePath: '/api/v1/auth' }, sessionTokenBackendDomain: undefined });
});

it('supports a separate API host with a shared cookie domain', () => {
  expect(supertokensAppInfo({ VITE_API_DOMAIN: 'https://api.prasang.in', VITE_SESSION_DOMAIN: '.prasang.in' }, 'https://prasang.in')).toEqual({
    appInfo: { appName: 'Prasang', apiDomain: 'https://api.prasang.in', apiBasePath: '/api/v1/auth' }, sessionTokenBackendDomain: '.prasang.in' });
});
