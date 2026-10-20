import { describe, expect, it } from 'vitest';
import { profileTabs } from './profileTabs';

describe('profileTabs', () => {
  it('Free profiles only have reviews', () => {
    expect(profileTabs('free')).toEqual({ tabs: ['reviews'], initial: 'reviews' });
  });
  it('paid profiles open on media, with reviews next to it', () => {
    for (const tier of ['basic', 'pro', 'premium'] as const) {
      expect(profileTabs(tier)).toEqual({ tabs: ['media', 'reviews'], initial: 'media' });
    }
  });
});
