import { describe, expect, it } from 'vitest';
import { createTokenStore } from './authStorage';
import { guardDecision, homePathFor } from './paths';
import type { Me } from '../api/types';

function memoryStorage(): Storage {
  const m = new Map<string, string>();
  return {
    get length() { return m.size; },
    clear: () => m.clear(),
    getItem: (k) => m.get(k) ?? null,
    key: (i) => [...m.keys()][i] ?? null,
    removeItem: (k) => { m.delete(k); },
    setItem: (k, v) => { m.set(k, v); },
  };
}

const user = (over: Partial<Me>): Me => ({
  id: 'u1', email: null, fullName: 'X', phone: null, role: 'planner', avatarUrl: null, artistSlug: null, createdAt: '2026-09-29T00:00:00Z', ...over,
});

describe('token store', () => {
  it('round-trips and clears the token', () => {
    const s = createTokenStore(memoryStorage());
    expect(s.get()).toBeNull();
    s.set('mock-artist');
    expect(s.get()).toBe('mock-artist');
    s.clear();
    expect(s.get()).toBeNull();
  });
});

describe('homePathFor', () => {
  it('sends an artist without a profile to onboarding', () =>
    expect(homePathFor(user({ role: 'artist', artistSlug: null }))).toBe('/artist/onboarding'));
  it('sends an artist with a profile to the dashboard', () =>
    expect(homePathFor(user({ role: 'artist', artistSlug: 'a' }))).toBe('/artist/dashboard'));
  it('sends a planner to the planner dashboard', () =>
    expect(homePathFor(user({ role: 'planner' }))).toBe('/planner/dashboard'));
});

describe('guardDecision', () => {
  const at = '/artist/leads';
  it('waits while auth is loading', () =>
    expect(guardDecision('loading', null, 'artist', at)).toEqual({ type: 'loading' }));
  it('redirects signed-out users to login with next', () =>
    expect(guardDecision('signedOut', null, 'artist', at)).toEqual({ type: 'redirect', to: '/login?next=%2Fartist%2Fleads' }));
  it('sends users without a profile to finish signup', () =>
    expect(guardDecision('needsProfile', null, 'artist', at)).toEqual({ type: 'redirect', to: '/signup?step=profile&next=%2Fartist%2Fleads' }));
  it('bounces the wrong role to its own home', () =>
    expect(guardDecision('signedIn', user({ role: 'planner' }), 'artist', at)).toEqual({ type: 'redirect', to: '/planner/dashboard' }));
  it('allows the right role', () =>
    expect(guardDecision('signedIn', user({ role: 'artist', artistSlug: 'a' }), 'artist', at)).toEqual({ type: 'allow' }));
  it('allows admins everywhere', () =>
    expect(guardDecision('signedIn', user({ role: 'admin' }), 'planner', '/planner/dashboard')).toEqual({ type: 'allow' }));
});

import { deriveAuthStatus } from './paths';

describe('deriveAuthStatus (review fix: outages are not sign-outs)', () => {
  it('no token → signedOut', () => expect(deriveAuthStatus({ hasToken: false, isPending: false, errorCode: null, hasUser: false })).toBe('signedOut'));
  it('fetching → loading', () => expect(deriveAuthStatus({ hasToken: true, isPending: true, errorCode: null, hasUser: false })).toBe('loading'));
  it('401 unauthenticated → signedOut', () => expect(deriveAuthStatus({ hasToken: true, isPending: false, errorCode: 'unauthenticated', hasUser: false })).toBe('signedOut'));
  it('5xx / network error → error, not signedOut', () => {
    expect(deriveAuthStatus({ hasToken: true, isPending: false, errorCode: 'http_502', hasUser: false })).toBe('error');
    expect(deriveAuthStatus({ hasToken: true, isPending: false, errorCode: 'network_error', hasUser: false })).toBe('error');
  });
  it('no profile → needsProfile', () => expect(deriveAuthStatus({ hasToken: true, isPending: false, errorCode: null, hasUser: false })).toBe('needsProfile'));
  it('user → signedIn', () => expect(deriveAuthStatus({ hasToken: true, isPending: false, errorCode: null, hasUser: true })).toBe('signedIn'));
});

describe('guardDecision (review fixes)', () => {
  it('shows an error state instead of redirecting when /me failed', () =>
    expect(guardDecision('error', null, 'artist', '/artist/leads')).toEqual({ type: 'error' }));
  it('sends an artist without a profile to onboarding from other artist pages', () =>
    expect(guardDecision('signedIn', user({ role: 'artist', artistSlug: null }), 'artist', '/artist/dashboard')).toEqual({ type: 'redirect', to: '/artist/onboarding' }));
  it('lets an artist without a profile use onboarding', () =>
    expect(guardDecision('signedIn', user({ role: 'artist', artistSlug: null }), 'artist', '/artist/onboarding')).toEqual({ type: 'allow' }));
  it('keeps next when sending users to finish their profile', () =>
    expect(guardDecision('needsProfile', null, 'planner', '/planner/inquiries')).toEqual({ type: 'redirect', to: '/signup?step=profile&next=%2Fplanner%2Finquiries' }));
});
