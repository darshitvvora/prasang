// The warning shown before an artist moves to a plan that holds fewer photos/videos/embeds.
import type { DowngradePreview } from '../../api/types';

const NAME = { free: 'Basic', pro: 'Pro', premium: 'Premium' } as const; // tier key 'free' is the Basic plan
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export function downgradeWarning(p: DowngradePreview): string | null {
  const parts = [
    p.photos && plural(p.photos, 'photo', 'photos'),
    p.videos && plural(p.videos, 'video', 'videos'),
    p.hdVideos && plural(p.hdVideos, 'HD video', 'HD videos'),
    p.embeds && plural(p.embeds, 'embedded post', 'embedded posts'),
  ].filter(Boolean) as string[];
  if (parts.length === 0) return null;
  const list = parts.length === 1 ? parts[0] : `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}`;
  return `Moving to ${NAME[p.tier]} will remove ${list} from your profile. They are deleted after 7 days unless you upgrade again.`;
}
