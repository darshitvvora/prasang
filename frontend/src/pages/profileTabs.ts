// Which tabs an artist profile shows: Media only when there is something to show (photos, videos or embedded posts).
export type ProfileTab = 'media' | 'reviews';

export function profileTabs(hasMedia: boolean): { tabs: ProfileTab[]; initial: ProfileTab } {
  return hasMedia ? { tabs: ['media', 'reviews'], initial: 'media' } : { tabs: ['reviews'], initial: 'reviews' };
}
