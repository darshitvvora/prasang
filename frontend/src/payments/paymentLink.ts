// PhonePe payment links: one link per billing period, also emailed and texted to the artist.
// Mock mode: the backend's fake gateway (and Mockoon) return `mock://phonepe/…` links, which count as paid at once.
export const MOCK_LINK_PREFIX = 'mock://phonepe/';

export const isMockLink = (url: string) => url.startsWith(MOCK_LINK_PREFIX);

/** "23 Oct, 3:00 pm" in IST — when the link stops working. */
export function linkDeadline(iso: string): string {
  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
  }).format(new Date(iso));
}
