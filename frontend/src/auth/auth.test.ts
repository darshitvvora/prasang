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
    expect(guardDecision('needsProfile', null, 'artist', at)).toEqual({ type: 'redirect', to: '/signup?step=profile' }));
  it('bounces the wrong role to its own home', () =>
    expect(guardDecision('signedIn', user({ role: 'planner' }), 'artist', at)).toEqual({ type: 'redirect', to: '/planner/dashboard' }));
  it('allows the right role', () =>
    expect(guardDecision('signedIn', user({ role: 'artist', artistSlug: 'a' }), 'artist', at)).toEqual({ type: 'allow' }));
  it('allows admins everywhere', () =>
    expect(guardDecision('signedIn', user({ role: 'admin' }), 'planner', '/planner/dashboard')).toEqual({ type: 'allow' }));
});
