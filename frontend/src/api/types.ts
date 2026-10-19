// API contract types — single TS source of truth. Mirrors contracts/README.md.
import type { ArtistType, EventType, SubscriptionTier, BudgetRange, LeadStatus, InquiryStatus } from '../types/artist';

export interface ApiErrorBody { error: { code: string; message: string; details?: Record<string, unknown> } }
export interface Page<T> { items: T[]; total: number; page: number; size: number }

export type Role = 'artist' | 'planner' | 'admin';
export interface AuthProvidersResponse { google: boolean; phoneOtp: boolean }
export interface Me { id: string; email: string | null; fullName: string; phone: string | null; role: Role; avatarUrl: string | null; artistSlug: string | null; createdAt: string }
export interface CreateMeRequest { role: 'artist' | 'planner'; fullName: string; phone?: string }
export interface UpdateMeRequest { fullName?: string; phone?: string }

export interface City { name: string; areas: string[] }
export interface LocationsResponse { cities: City[] }

export interface ArtistCard {
  artistId: string; slug: string; name: string; artistType: ArtistType; profileImageUrl: string | null; bio: string;
  locationCity: string; locationArea: string; perEventRateMin: number; perEventRateMax: number;
  averageRating: number; totalReviews: number; isVerified: boolean; isFeatured: boolean; subscriptionTier: SubscriptionTier;
  instagramHandle: string | null; youtubeChannel: string | null; facebookUrl: string | null; experienceYears: number;
  eventTypesSupported: EventType[]; languagesSpoken: string[]; readyToTravel: boolean;
}
export type MediaKind = 'image' | 'video' | 'youtube' | 'instagram' | 'facebook';
/** `url`: public file URL (image/video) or the original social link. `embedUrl`: iframe src for social kinds, else null. */
export interface Media { id: string; kind: MediaKind; url: string; embedUrl: string | null; thumbnailUrl: string | null; caption: string | null; displayOrder: number }
/** Profile-level widget built from the artist's social links. `embedUrl` null = show as a link only. */
export interface SocialWidget { platform: 'instagram' | 'youtube' | 'facebook'; profileUrl: string; embedUrl: string | null }
export interface ArtistDetail extends ArtistCard { media: Media[]; socialWidgets: SocialWidget[] }
export interface Review { id: string; reviewerName: string; rating: number; eventType: EventType; eventMonth: string; text: string; createdAt: string; verified: boolean; artistReply: string | null }

export interface ArtistProfileInput {
  name: string; artistType: ArtistType; locationCity: string; locationArea: string; bio: string; experienceYears: number;
  perEventRateMin: number; perEventRateMax: number; eventTypesSupported: EventType[]; languagesSpoken: string[];
  readyToTravel: boolean; instagramHandle: string | null; youtubeChannel: string | null; facebookUrl: string | null;
  contactPhone: string; whatsappNumber: string | null; googlePlaceUrl: string | null;
}
export interface CompletenessItem { key: 'basic_info' | 'photo' | 'bio' | 'media' | 'instagram' | 'review'; label: string; done: boolean }
export interface ProfileCompleteness { percent: number; items: CompletenessItem[] }
export interface ArtistProfile extends ArtistDetail { contactPhone: string; whatsappNumber: string | null; isPublished: boolean; completeness: ProfileCompleteness; suspended: boolean; suspensionReason: string | null; googlePlaceUrl: string | null }

export interface PlanUsage {
  tier: SubscriptionTier; name: string; status: 'free' | 'trial' | 'active' | 'cancelling' | 'halted';
  leadLimitMonthly: number; leadsUsedThisMonth: number; leadsRemaining: number | null;
  periodEnd: string | null; trialEndsAt: string | null; trialAvailable: boolean;
}
export interface Metric { value: number; changePct: number | null }
export interface LeadSourceStat { source: LeadSource; label: string; pct: number }
export interface ArtistDashboard {
  greetingName: string; isPublished: boolean; plan: PlanUsage;
  metrics: { profileViews: Metric; contactClicks: Metric; leadsThisMonth: Metric; averageRating: { value: number; totalReviews: number } };
  recentLeads: ArtistLead[]; leadSources: LeadSourceStat[]; completeness: ProfileCompleteness;
}

export interface MediaQuota { images: { used: number; limit: number }; videos: { used: number; limit: number } }
export interface MediaListResponse { items: Media[]; quota: MediaQuota }
export interface UploadUrlRequest { kind: 'image' | 'video' | 'avatar'; contentType: string; sizeBytes: number }
export interface UploadUrlResponse { uploadUrl: string; storageKey: string; expiresAt: string; headers: Record<string, string> }
export type CreateMediaRequest = { kind: 'image' | 'video'; storageKey: string; caption?: string } | { kind: 'youtube' | 'instagram' | 'facebook'; url: string; caption?: string };

export type SortOption = 'relevance' | 'rating' | 'price_low' | 'price_high' | 'popular' | 'newest';
export interface SearchParams {
  q?: string; city?: string; area?: string; artistType?: ArtistType; eventType?: EventType; language?: string;
  readyToTravel?: boolean; minPrice?: number; maxPrice?: number; minRating?: number;
  verifiedOnly?: boolean; featuredOnly?: boolean; sort?: SortOption; page?: number; size?: number;
}
export interface FacetBucket { value: string; count: number }
export interface SearchResponse extends Page<ArtistCard> { facets: { artistType: FacetBucket[]; city: FacetBucket[] } }
export interface Suggestion { type: 'artist' | 'artistType' | 'area'; label: string; value: string; slug: string | null }

export type LeadSource = 'search' | 'profile' | 'featured' | 'direct_link';
export interface CreateLeadRequest {
  artistId: string; plannerName: string; plannerPhone: string; plannerEmail: string | null; eventType: EventType;
  eventDate: string | null; eventCity: string | null; budgetRange: BudgetRange; notes: string | null; source: LeadSource;
}
export interface CreateLeadResponse { leadId: string; artist: { name: string; contactPhone: string; whatsappNumber: string | null; instagramHandle: string | null } }
export interface ArtistLead {
  id: string; plannerName: string; plannerPhone: string | null; plannerEmail: string | null; eventType: EventType; eventTitle: string;
  eventDate: string | null; eventCity: string | null; budgetMin: number; budgetMax: number | null; notes: string | null;
  status: LeadStatus; isLocked: boolean; createdAt: string;
}
export interface ArtistLeadsResponse extends Page<ArtistLead> { counts: Record<'all' | LeadStatus, number>; plan: PlanUsage }
export interface UpdateLeadRequest { status: 'contacted' | 'converted' | 'declined' }
export interface PlannerInquiry {
  id: string; artist: { artistId: string; slug: string; name: string; artistType: ArtistType; profileImageUrl: string | null };
  eventType: EventType; eventTitle: string; eventDate: string | null; daysToEvent: number | null;
  budgetMin: number; budgetMax: number | null; notes: string | null; status: InquiryStatus; contactedAt: string;
  bookingConfirmed: boolean; plannerAnswer: PlannerAnswer | null; canReview: boolean; reviewId: string | null;
}
export type PlannerAnswer = 'booked' | 'not_booked' | 'deciding';
export interface PlannerAnswerRequest { answer: PlannerAnswer }
export interface PlannerInquiriesResponse extends Page<PlannerInquiry> {
  counts: Record<'all' | InquiryStatus, number>;
  summary: { artistsContacted: number; responsesReceived: number; confirmedBookings: number;
    upcoming: { inquiryId: string; eventTitle: string; artistName: string; eventDate: string; daysToEvent: number } | null };
}

export type BillingCycle = 'monthly' | 'annual';
export interface PlanFeature { label: string; value: boolean | string }
export interface Plan {
  tier: SubscriptionTier; name: string; tagline: string; monthlyPrice: number; annualPrice: number; annualMonthlyEquivalent: number;
  leadLimitMonthly: number; maxImages: number; maxVideos: number; popular: boolean; features: PlanFeature[];
}
export interface SubscriptionSummary { id: string; tier: SubscriptionTier; billingCycle: BillingCycle; status: 'created' | 'active' | 'halted' | 'cancelled' | 'completed' | 'expired'; currentPeriodEnd: string | null; cancelAtPeriodEnd: boolean }
export interface MySubscriptionResponse { plan: PlanUsage; subscription: SubscriptionSummary | null }
export interface CreateSubscriptionRequest { tier: Exclude<SubscriptionTier, 'free'>; billingCycle: BillingCycle }
export interface CreateSubscriptionResponse { subscriptionId: string; checkout: { keyId: string; razorpaySubscriptionId: string; name: string; description: string; prefill: { name: string; email: string | null; contact: string | null } } }
export interface VerifyPaymentRequest { razorpayPaymentId: string; razorpaySubscriptionId: string; razorpaySignature: string }
export interface VerifyPaymentResponse { status: 'active' | 'pending_activation'; plan: PlanUsage }
export interface BillingItem {
  id: string; paidAt: string; tier: Exclude<SubscriptionTier, 'free'>; billingCycle: BillingCycle; amount: number; currency: string;
  status: 'paid' | 'failed'; receiptUrl: string | null;
}
export interface BillingHistoryResponse { items: BillingItem[] }
export interface CreateReviewRequest { leadId: string; rating: number; text: string }
export interface UpdateReviewRequest { rating?: number; text?: string }
export interface ReviewReplyRequest { text: string }
export interface ReviewReportRequest { reason: string }
export interface GoogleReviewItem { author: string; rating: number; relativeTime: string; text: string }
export interface GoogleReviewsResponse { rating: number | null; count: number; mapsUrl: string | null; items: GoogleReviewItem[] }
export interface SiteInfo { supportEmail: string | null; supportPhone: string | null; businessAddress: string | null }
export type ContactTopic = 'general' | 'artist_support' | 'payments' | 'report';
export interface ContactRequest { name: string; contact: string; topic: ContactTopic; message: string }
export interface ContactResponse { id: string }
export interface StartTrialRequest { tier: Exclude<SubscriptionTier, 'free'> }
