export type ArtistType =
  | 'magician'
  | 'dj'
  | 'singer'
  | 'comedian'
  | 'bubble_artist'
  | 'band'
  | 'body_double'
  | 'anchor'
  | 'other';

export type SubscriptionTier = 'free' | 'basic' | 'pro' | 'premium';

export type AvailabilityStatus = 'available' | 'busy' | 'unavailable';

export interface Artist {
  artistId: string;
  name: string;
  slug: string;
  artistType: ArtistType;
  profileImageUrl: string;
  bio: string;
  locationCity: string;
  locationArea: string;
  perEventRateMin: number;
  perEventRateMax: number;
  averageRating: number;
  totalReviews: number;
  isVerified: boolean;
  isFeatured: boolean;
  subscriptionTier: SubscriptionTier;
  instagramHandle?: string;
  youtubeChannel?: string;
  experienceYears: number;
  availabilityStatus: AvailabilityStatus;
}

export const ARTIST_TYPE_LABELS: Record<ArtistType, string> = {
  magician: 'Magician',
  dj: 'DJ',
  singer: 'Singer',
  comedian: 'Comedian',
  bubble_artist: 'Bubble Artist',
  band: 'Band',
  body_double: 'Body Double',
  anchor: 'Anchor',
  other: 'Other',
};

export const ARTIST_TYPE_COLORS: Record<ArtistType, string> = {
  magician: '#8b5cf6',
  dj: '#3b82f6',
  singer: '#ec4899',
  comedian: '#f59e0b',
  bubble_artist: '#06b6d4',
  band: '#ef4444',
  body_double: '#6366f1',
  anchor: '#10b981',
  other: '#6b7280',
};
