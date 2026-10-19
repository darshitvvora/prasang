import type { Media } from '../api/types';

/** Social items (YouTube/Instagram/Facebook) render as iframes using the server-validated embedUrl. */
export const mediaIsEmbed = (m: Media): boolean => m.kind !== 'image' && m.kind !== 'video' && !!m.embedUrl;

/** Which platform a pasted link belongs to (the server re-validates). */
export function linkKind(url: string): 'youtube' | 'instagram' | 'facebook' | null {
  if (/^https?:\/\/(www\.|m\.)?(youtube\.com|youtu\.be)\//i.test(url)) return 'youtube';
  if (/^https?:\/\/(www\.)?instagram\.com\//i.test(url)) return 'instagram';
  if (/^https?:\/\/((www|m|web)\.)?facebook\.com\/|^https?:\/\/fb\.watch\//i.test(url)) return 'facebook';
  return null;
}

/** Sandbox for third-party embeds: scripts (players need them) but no top navigation or form submission. */
export const EMBED_SANDBOX = 'allow-scripts allow-same-origin allow-popups allow-presentation';
export const EMBED_ALLOW = 'encrypted-media; picture-in-picture; fullscreen';
