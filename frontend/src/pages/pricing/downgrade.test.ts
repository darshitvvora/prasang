import { describe, expect, it } from 'vitest';
import { downgradeWarning } from './downgrade';

describe('downgradeWarning', () => {
  it('is null when nothing would be removed', () => {
    expect(downgradeWarning({ tier: 'pro', photos: 0, videos: 0, hdVideos: 0, embeds: 0 })).toBeNull();
  });
  it('lists what goes, in plain words', () => {
    expect(downgradeWarning({ tier: 'basic', photos: 15, videos: 2, hdVideos: 0, embeds: 0 }))
      .toBe('Moving to Basic will remove 15 photos and 2 videos from your profile. They are deleted after 7 days unless you upgrade again.');
    expect(downgradeWarning({ tier: 'free', photos: 1, videos: 0, hdVideos: 1, embeds: 3 }))
      .toBe('Moving to Free will remove 1 photo, 1 HD video and 3 embedded posts from your profile. They are deleted after 7 days unless you upgrade again.');
  });
});
