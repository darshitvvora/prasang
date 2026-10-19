// Search filters live in the URL so results are shareable and survive reloads.
// parseSearch sanitises untrusted query strings into contract SearchParams.
import type { SearchParams, SortOption } from '../../api/types';
import { ARTIST_TYPE_LABELS, EVENT_TYPE_LABELS } from '../../types/artist';
import type { ArtistType, EventType } from '../../types/artist';

export const DEFAULT_CITY = 'Mumbai';
export const MAX_PRICE = 100000; // slider top = "₹1L+" = no upper bound
const SORTS: SortOption[] = ['relevance', 'rating', 'price_low', 'price_high', 'popular', 'newest'];

const num = (v: string | null, min = 0): number | undefined => {
  if (v === null || v.trim() === '') return undefined;
  const n = Number(v);
  return Number.isFinite(n) && n >= min ? n : undefined;
};
const flag = (v: string | null) => (v === 'true' ? true : undefined);
const oneOf = <T extends string>(v: string | null, allowed: readonly T[]) => (v !== null && (allowed as readonly string[]).includes(v) ? (v as T) : undefined);

export function parseSearch(sp: URLSearchParams): SearchParams {
  const raw: SearchParams = {
    q: sp.get('q')?.trim() || undefined,
    city: sp.get('city') || DEFAULT_CITY,
    area: sp.get('area') || undefined,
    artistType: oneOf(sp.get('artistType'), Object.keys(ARTIST_TYPE_LABELS) as ArtistType[]),
    eventType: oneOf(sp.get('eventType'), Object.keys(EVENT_TYPE_LABELS) as EventType[]),
    language: sp.get('language') || undefined,
    readyToTravel: flag(sp.get('readyToTravel')),
    minPrice: num(sp.get('minPrice')),
    maxPrice: num(sp.get('maxPrice')),
    minRating: num(sp.get('minRating')),
    verifiedOnly: flag(sp.get('verifiedOnly')),
    featuredOnly: flag(sp.get('featuredOnly')),
    sort: oneOf(sp.get('sort'), SORTS) ?? 'relevance',
    page: Math.floor(num(sp.get('page'), 1) ?? 1),
  };
  return Object.fromEntries(Object.entries(raw).filter(([, v]) => v !== undefined)) as SearchParams;
}

function isDefault(key: string, value: unknown): boolean {
  if (value === undefined || value === '' || value === false || value === 0) return true;
  if (key === 'city') return value === DEFAULT_CITY;
  if (key === 'sort') return value === 'relevance';
  if (key === 'page') return value === 1;
  if (key === 'maxPrice') return (value as number) >= MAX_PRICE;
  return false;
}

// Canonical key order keeps URLs stable regardless of how params were merged.
const KEY_ORDER: (keyof SearchParams)[] = [
  'q', 'city', 'area', 'artistType', 'eventType', 'language', 'readyToTravel', 'minPrice', 'maxPrice',
  'minRating', 'verifiedOnly', 'featuredOnly', 'sort', 'page', 'size',
];

export function toSearchString(params: SearchParams): string {
  const sp = new URLSearchParams();
  for (const key of KEY_ORDER) {
    const value = params[key];
    if (!isDefault(key, value)) sp.set(key, String(value));
  }
  return sp.toString();
}

/** Apply filter changes on top of the *latest* URL (use inside a functional setSearchParams). Resets to page 1. */
export function mergeSearch(latest: URLSearchParams, changes: Partial<SearchParams>): string {
  return toSearchString({ ...parseSearch(latest), page: 1, ...changes });
}

/** Number of sidebar filters in effect (q/city/sort/page are not sidebar filters). */
export function activeFilterCount(params: SearchParams): number {
  const keys: (keyof SearchParams)[] = ['area', 'artistType', 'eventType', 'language', 'readyToTravel', 'minPrice', 'maxPrice', 'minRating', 'verifiedOnly', 'featuredOnly'];
  return keys.filter((k) => !isDefault(k, params[k])).length;
}
