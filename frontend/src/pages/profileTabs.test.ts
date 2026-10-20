import { describe, expect, it } from 'vitest';
import { profileTabs } from './profileTabs';

describe('profileTabs', () => {
  it('profiles without any photos, videos or embedded posts only have reviews', () => {
    expect(profileTabs(false)).toEqual({ tabs: ['reviews'], initial: 'reviews' });
  });
  it('profiles with media open on media, with reviews next to it', () => {
    expect(profileTabs(true)).toEqual({ tabs: ['media', 'reviews'], initial: 'media' });
  });
});
