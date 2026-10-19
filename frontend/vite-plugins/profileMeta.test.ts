import { describe, expect, it } from 'vitest';
import { injectHead, profileSlug } from './profileMeta.ts';

describe('profileSlug', () => {
  it('reads the slug from profile URLs only', () => {
    expect(profileSlug('/profile/arjun-dj')).toBe('arjun-dj');
    expect(profileSlug('/profile/arjun-dj?ref=ig')).toBe('arjun-dj');
    expect(profileSlug('/search')).toBeNull();
    expect(profileSlug(undefined)).toBeNull();
  });
});

describe('injectHead', () => {
  it('replaces only the marked block', () => {
    expect(injectHead('<head><!--og:start--><title>x</title><!--og:end--></head>', '<title>y</title>'))
      .toBe('<head><!--og:start--><title>y</title><!--og:end--></head>');
    expect(injectHead('<head></head>', '<title>y</title>')).toBe('<head></head>');
  });
});
