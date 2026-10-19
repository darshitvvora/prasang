// TanStack Query hooks over endpoints.ts. Query keys live in `keys` so
// mutations can invalidate exactly what they change.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as E from './endpoints';
import type * as T from './types';

export const keys = {
  me: ['me'] as const,
  authProviders: ['auth', 'providers'] as const,
  locations: ['locations'] as const,
  search: (p: T.SearchParams) => ['search', p] as const,
  featured: ['artists', 'featured'] as const,
  artist: (slug: string) => ['artist', slug] as const,
  reviews: (slug: string) => ['artist', slug, 'reviews'] as const,
  similar: (slug: string) => ['artist', slug, 'similar'] as const,
  myArtist: ['artists', 'me'] as const,
  dashboard: ['artists', 'me', 'dashboard'] as const,
  myMedia: ['artists', 'me', 'media'] as const,
  artistLeads: (status: string) => ['leads', 'artist', status] as const,
  plannerInquiries: (status: string) => ['leads', 'planner', status] as const,
  plans: ['plans'] as const,
  mySubscription: ['subscriptions', 'me'] as const,
  siteInfo: ['site-info'] as const,
};

const STATIC = { staleTime: 60 * 60 * 1000 }; // locations/plans rarely change

export const useAuthProviders = () => useQuery({ queryKey: keys.authProviders, queryFn: E.getAuthProviders, ...STATIC });
export const useLocations = () => useQuery({ queryKey: keys.locations, queryFn: E.getLocations, ...STATIC });
export const useSiteInfo = () => useQuery({ queryKey: keys.siteInfo, queryFn: E.getSiteInfo, ...STATIC });
export const usePlans = () => useQuery({ queryKey: keys.plans, queryFn: E.getPlans, ...STATIC });
export const useSearchArtists = (params: T.SearchParams) =>
  useQuery({ queryKey: keys.search(params), queryFn: () => E.searchArtists(params), placeholderData: (prev) => prev });
export const useFeaturedArtists = () => useQuery({ queryKey: keys.featured, queryFn: () => E.getFeaturedArtists() });
export const useArtist = (slug: string) => useQuery({ queryKey: keys.artist(slug), queryFn: () => E.getArtist(slug) });
export const useArtistReviews = (slug: string) => useQuery({ queryKey: keys.reviews(slug), queryFn: () => E.getArtistReviews(slug) });
export const useSimilarArtists = (slug: string) => useQuery({ queryKey: keys.similar(slug), queryFn: () => E.getSimilarArtists(slug) });

export const useMyArtist = (enabled = true) => useQuery({ queryKey: keys.myArtist, queryFn: E.getMyArtist, enabled });
export const useArtistDashboard = () => useQuery({ queryKey: keys.dashboard, queryFn: E.getArtistDashboard });
export const useMyMedia = (enabled = true) => useQuery({ queryKey: keys.myMedia, queryFn: E.getMyMedia, enabled });
export const useArtistLeads = (status: string) =>
  useQuery({ queryKey: keys.artistLeads(status), queryFn: () => E.getArtistLeads(status === 'all' ? undefined : status) });
export const usePlannerInquiries = (status: string) =>
  useQuery({ queryKey: keys.plannerInquiries(status), queryFn: () => E.getPlannerInquiries(status === 'all' ? undefined : status) });
export const useMySubscription = (enabled = true) => useQuery({ queryKey: keys.mySubscription, queryFn: E.getMySubscription, enabled });

// ---- mutations ----
export const useSendContactMessage = () => useMutation({ mutationFn: E.sendContactMessage });

export function useCreateLead() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: E.createLead, onSuccess: () => qc.invalidateQueries({ queryKey: ['leads', 'planner'] }) });
}

export function useUpdateLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string } & T.UpdateLeadRequest) => E.updateLead(id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['leads', 'artist'] });
      qc.invalidateQueries({ queryKey: keys.dashboard });
    },
  });
}

/** What changes when the artist creates/updates their profile: profile, /me (artistSlug) and plan/trial state. */
export const ARTIST_SELF_KEYS: readonly (readonly string[])[] = [['artists', 'me'], keys.me, keys.mySubscription];

function invalidateArtistSelf(qc: ReturnType<typeof useQueryClient>) {
  for (const queryKey of ARTIST_SELF_KEYS) qc.invalidateQueries({ queryKey });
}

export function useCreateArtist() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: E.createArtist, onSuccess: () => invalidateArtistSelf(qc) });
}

export function useUpdateMyArtist() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: E.updateMyArtist, onSuccess: () => invalidateArtistSelf(qc) });
}

function invalidatePlan(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: keys.mySubscription });
  qc.invalidateQueries({ queryKey: keys.dashboard });
  qc.invalidateQueries({ queryKey: ['leads', 'artist'] });
}

export function useStartTrial() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: E.startTrial, onSuccess: () => invalidatePlan(qc) });
}

export function useCreateSubscription() {
  return useMutation({ mutationFn: E.createSubscription });
}

export function useVerifyPayment() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: E.verifyPayment, onSuccess: () => invalidatePlan(qc) });
}

export function useCancelSubscription() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: E.cancelSubscription, onSuccess: () => invalidatePlan(qc) });
}
