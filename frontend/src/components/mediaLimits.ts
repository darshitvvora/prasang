// Plan limits for portfolio uploads (mirrors the backend: no compression, size caps instead).
import type { MediaQuota } from '../api/types';
import { formatDate } from '../api/format';

const MB = 1024 * 1024;
export const MAX_BYTES = { image: 10 * MB, video: 40 * MB, hd: 200 * MB } as const;

export function uploadProblem(file: { name: string; size: number }, kind: 'image' | 'video', hd: boolean): string | null {
  const max = kind === 'image' ? MAX_BYTES.image : hd ? MAX_BYTES.hd : MAX_BYTES.video;
  return file.size > max ? `${file.name} is too large (max ${max / MB} MB)` : null;
}

const count = (c: { used: number; limit: number }) => (c.limit < 0 ? `${c.used}` : `${c.used}/${c.limit}`);

export function quotaSummary(q: MediaQuota): string {
  if (q.images.limit === 0 && q.videos.limit === 0 && q.hdVideos.limit === 0) return 'Uploads start on the Basic plan';
  const parts = [`Photos ${count(q.images)}`, `Videos ${count(q.videos)}`];
  if (q.hdVideos.limit !== 0) parts.push(`HD videos ${count(q.hdVideos)}`);
  return parts.join(' · ');
}

export const canUseHd = (q: MediaQuota): boolean => q.hdVideos.limit < 0 || q.hdVideos.used < q.hdVideos.limit;

export function deletionNote(deleteAfter: string | null): string | null {
  if (!deleteAfter) return null;
  const ist = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date(deleteAfter));
  return `Hidden — deleted on ${formatDate(ist)} unless you upgrade`;
}
