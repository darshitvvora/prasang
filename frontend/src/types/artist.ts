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

export type EventType =
  | 'birthday'
  | 'wedding'
  | 'pre_wedding'
  | 'anniversary'
  | 'corporate'
  | 'house_party'
  | 'other';

export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  birthday: 'Birthday',
  wedding: 'Wedding',
  pre_wedding: 'Pre-Wedding',
  anniversary: 'Anniversary',
  corporate: 'Corporate',
  house_party: 'House Party',
  other: 'Other',
};

export const LANGUAGES = [
  'Hindi',
  'English',
  'Marathi',
  'Gujarati',
  'Tamil',
  'Telugu',
  'Kannada',
  'Bengali',
  'Punjabi',
  'Other',
] as const;

export type Language = typeof LANGUAGES[number];

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

export type BudgetRange = '5k_10k' | '10k_15k' | '15k_25k' | '25k_50k' | '50k_plus';
export const BUDGET_RANGE_LABELS: Record<BudgetRange, string> = {
  '5k_10k': '₹5K–10K', '10k_15k': '₹10K–15K', '15k_25k': '₹15K–25K', '25k_50k': '₹25K–50K', '50k_plus': '₹50K+',
};
export type LeadStatus = 'new' | 'contacted' | 'converted' | 'declined' | 'expired';
export type InquiryStatus = 'pending' | 'responded' | 'confirmed' | 'declined';
