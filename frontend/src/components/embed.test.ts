import { describe, expect, it } from 'vitest';
import { linkKind, mediaIsEmbed } from './embed';
import type { Media } from '../api/types';

const m = (kind: Media['kind'], embedUrl: string | null): Media => ({ id: '1', kind, url: 'u', embedUrl, thumbnailUrl: null, caption: null, displayOrder: 0 });

describe('embeds', () => {
  it('treats social items with an embed URL as iframes', () => {
    expect(mediaIsEmbed(m('youtube', 'https://www.youtube-nocookie.com/embed/x'))).toBe(true);
    expect(mediaIsEmbed(m('facebook', 'https://www.facebook.com/plugins/video.php?href=x'))).toBe(true);
    expect(mediaIsEmbed(m('image', null))).toBe(false);
    expect(mediaIsEmbed(m('instagram', null))).toBe(false);
  });

  it.each([
    ['https://youtu.be/aqz-KE-bpKQ', 'youtube'],
    ['https://www.instagram.com/reel/C9xYz12AbCd/', 'instagram'],
    ['https://www.facebook.com/arjunmagic/videos/1/', 'facebook'],
    ['https://fb.watch/abc/', 'facebook'],
    ['https://example.com/x', null],
  ])('detects the platform of %s', (url, kind) => expect(linkKind(url)).toBe(kind));
});
