// Dev only: give /profile/<slug> the artist's link-preview tags, like production does (nginx → API /profile/<slug>).
// Fetches the tags from the API and swaps them into the marked block of index.html; on any failure the page is unchanged.
import type { Plugin } from 'vite';

const START = '<!--og:start-->';
const END = '<!--og:end-->';

export function injectHead(html: string, head: string): string {
  const start = html.indexOf(START);
  const end = html.indexOf(END);
  if (start < 0 || end < start) return html;
  return html.slice(0, start + START.length) + head + html.slice(end);
}

export function profileSlug(url: string | undefined): string | null {
  const match = /^\/profile\/([^/?#]+)/.exec(url ?? '');
  return match ? match[1] : null;
}

export function profileMeta(apiOrigin: string): Plugin {
  return {
    name: 'prasang-profile-meta',
    apply: 'serve',
    async transformIndexHtml(html, ctx) {
      const slug = profileSlug(ctx.originalUrl);
      if (!slug) return html;
      try {
        const res = await fetch(`${apiOrigin}/api/v1/artists/${slug}/share-head`, { signal: AbortSignal.timeout(1500) });
        return res.ok ? injectHead(html, await res.text()) : html;
      } catch {
        return html;
      }
    },
  };
}
