export type InquiryStatus = 'pending' | 'responded' | 'confirmed' | 'declined';

export interface Inquiry {
  id: string;
  artistId: string;
  event: string;
  eventDate: string;
  daysToEvent: number;
  budgetMin: number;
  budgetMax: number;
  notes: string;
  status: InquiryStatus;
  contactedAt: string;
}

export const INQUIRIES: Inquiry[] = [
  {
    id: 'inq-1',
    artistId: 'art-001',
    event: 'Wedding Reception',
    eventDate: 'Jan 5, 2026',
    daysToEvent: 12,
    budgetMin: 15000,
    budgetMax: 25000,
    notes: 'Close-up magic for cocktail hour, ~150 guests.',
    status: 'confirmed',
    contactedAt: '3 days ago',
  },
  {
    id: 'inq-2',
    artistId: 'art-002',
    event: 'Sangeet Night',
    eventDate: 'Jan 18, 2026',
    daysToEvent: 25,
    budgetMin: 20000,
    budgetMax: 35000,
    notes: 'Need a Bollywood + EDM mix, 4-hour set.',
    status: 'responded',
    contactedAt: '1 day ago',
  },
  {
    id: 'inq-3',
    artistId: 'art-003',
    event: 'Anniversary Party',
    eventDate: 'Feb 2, 2026',
    daysToEvent: 40,
    budgetMin: 10000,
    budgetMax: 18000,
    notes: 'Live acoustic set for an intimate 40-guest dinner.',
    status: 'pending',
    contactedAt: '5 hours ago',
  },
  {
    id: 'inq-4',
    artistId: 'art-004',
    event: 'Corporate Offsite',
    eventDate: 'Dec 28, 2025',
    daysToEvent: -2,
    budgetMin: 25000,
    budgetMax: 40000,
    notes: '30-minute stand-up set to open the evening.',
    status: 'declined',
    contactedAt: '10 days ago',
  },
  {
    id: 'inq-5',
    artistId: 'art-005',
    event: 'Birthday Party',
    eventDate: 'Jan 10, 2026',
    daysToEvent: 17,
    budgetMin: 30000,
    budgetMax: 50000,
    notes: 'Live band, 2-hour set, outdoor lawn setup.',
    status: 'pending',
    contactedAt: '2 hours ago',
  },
];

export const STATUS_COLORS: Record<InquiryStatus, string> = {
  pending: '#f59e0b',
  responded: '#60a5fa',
  confirmed: '#4ade80',
  declined: '#666',
};

export const SAVED_ARTIST_IDS = ['art-002', 'art-006', 'art-007', 'art-008'];
