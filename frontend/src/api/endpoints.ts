// One typed function per contract endpoint (contracts/README.md).
import { api, ApiError } from './client';
import type * as T from './types';

const slugPath = (slug: string) => `/artists/${encodeURIComponent(slug)}`;
type Items<X> = { items: X[] };

// ---- auth ----
export const getAuthProviders = () => api<T.AuthProvidersResponse>('/auth/providers');

// ---- site ----
export const getSiteInfo = () => api<T.SiteInfo>('/site-info');
export const sendContactMessage = (body: T.ContactRequest) => api<T.ContactResponse>('/contact', { method: 'POST', body });

// ---- booking confirmation ----
export const answerInquiry = (id: string, body: T.PlannerAnswerRequest) =>
  api<T.PlannerInquiry>(`/leads/${encodeURIComponent(id)}/planner-answer`, { method: 'PATCH', body });

// ---- billing ----
export const getMyPayments = () => api<T.BillingHistoryResponse>('/subscriptions/me/payments');

// ---- me ----
export const getMe = () => api<T.Me>('/me');
export const createMe = (body: T.CreateMeRequest) => api<T.Me>('/me', { method: 'POST', body });
export const updateMe = (body: T.UpdateMeRequest) => api<T.Me>('/me', { method: 'PATCH', body });

// ---- public discovery ----
export const getLocations = () => api<T.LocationsResponse>('/locations');
export const searchArtists = (params: T.SearchParams) =>
  api<T.SearchResponse>('/search/artists', { query: { ...params } });
export const getSuggestions = (q: string) => api<Items<T.Suggestion>>('/search/suggestions', { query: { q } });
export const getFeaturedArtists = (size = 12) => api<Items<T.ArtistCard>>('/artists/featured', { query: { size } });
export const getArtist = (slug: string) => api<T.ArtistDetail>(slugPath(slug));
export const getArtistReviews = (slug: string, page = 1) =>
  api<T.Page<T.Review>>(`${slugPath(slug)}/reviews`, { query: { page } });
export const getSimilarArtists = (slug: string, size = 3) =>
  api<Items<T.ArtistCard>>(`${slugPath(slug)}/similar`, { query: { size } });
export const trackContactClick = (slug: string) => api<void>(`${slugPath(slug)}/contact-click`, { method: 'POST' });

// ---- artist self ----
export const createArtist = (body: T.ArtistProfileInput) => api<T.ArtistProfile>('/artists', { method: 'POST', body });
export const getMyArtist = () => api<T.ArtistProfile>('/artists/me');
export const updateMyArtist = (body: Partial<T.ArtistProfileInput> & { isPublished?: boolean }) =>
  api<T.ArtistProfile>('/artists/me', { method: 'PATCH', body });
export const getArtistDashboard = () => api<T.ArtistDashboard>('/artists/me/dashboard');

// ---- media ----
export const getMyMedia = () => api<T.MediaListResponse>('/artists/me/media');
export const requestUploadUrl = (body: T.UploadUrlRequest) =>
  api<T.UploadUrlResponse>('/artists/me/media/upload-url', { method: 'POST', body });
export const createMedia = (body: T.CreateMediaRequest) => api<T.Media>('/artists/me/media', { method: 'POST', body });
export const setAvatar = (storageKey: string) =>
  api<{ profileImageUrl: string }>('/artists/me/avatar', { method: 'POST', body: { storageKey } });
export const deleteMedia = (id: string) => api<void>(`/artists/me/media/${encodeURIComponent(id)}`, { method: 'DELETE' });
export const reorderMedia = (ids: string[]) => api<Items<T.Media>>('/artists/me/media/order', { method: 'PUT', body: { ids } });

/** PUT the file straight to object storage. Presigned URLs carry their own auth, so no bearer token. */
export async function uploadToUrl(target: T.UploadUrlResponse, file: Blob): Promise<void> {
  let res: Response;
  try {
    res = await fetch(target.uploadUrl, { method: 'PUT', headers: target.headers, body: file });
  } catch {
    throw new ApiError(0, 'upload_failed', 'Upload failed. Check your connection and try again.');
  }
  if (!res.ok) throw new ApiError(res.status, 'upload_failed', 'Upload failed. Please try again.');
}

// ---- leads ----
export const createLead = (body: T.CreateLeadRequest) => api<T.CreateLeadResponse>('/leads', { method: 'POST', body });
export const getArtistLeads = (status?: string, page = 1) =>
  api<T.ArtistLeadsResponse>('/leads/artist', { query: { status, page } });
export const updateLead = (id: string, body: T.UpdateLeadRequest) =>
  api<T.ArtistLead>(`/leads/${encodeURIComponent(id)}`, { method: 'PATCH', body });
export const getPlannerInquiries = (status?: string, page = 1) =>
  api<T.PlannerInquiriesResponse>('/leads/planner', { query: { status, page } });

// ---- subscriptions ----
export const getPlans = () => api<Items<T.Plan>>('/subscriptions/plans');
export const getMySubscription = () => api<T.MySubscriptionResponse>('/subscriptions/me');
export const startTrial = (body: T.StartTrialRequest) => api<T.PlanUsage>('/subscriptions/trial', { method: 'POST', body });
export const createSubscription = (body: T.CreateSubscriptionRequest) =>
  api<T.CreateSubscriptionResponse>('/subscriptions', { method: 'POST', body });
export const verifyPayment = (body: T.VerifyPaymentRequest) =>
  api<T.VerifyPaymentResponse>('/subscriptions/verify', { method: 'POST', body });
export const cancelSubscription = () => api<T.MySubscriptionResponse>('/subscriptions/cancel', { method: 'POST' });
