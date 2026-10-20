// Onboarding / edit-profile form state and its mapping to the API contract.
import type { ArtistProfile, ArtistProfileInput } from '../../api/types';
import type { ArtistType, EventType } from '../../types/artist';

export interface ProfileFormState {
  name: string; artistType: ArtistType | ''; city: string; area: string; bio: string;
  experienceYears: string; rateMin: string; rateMax: string; contactPhone: string; whatsappNumber: string;
  instagram: string; youtube: string; facebook: string; googleMaps: string; eventTypes: EventType[]; languages: string[];
  readyToTravel: boolean;
}

export type ProfileFormErrors = Partial<Record<keyof ProfileFormState, string>>;

export const emptyProfileForm = (): ProfileFormState => ({
  name: '', artistType: '', city: '', area: '', bio: '', experienceYears: '', rateMin: '', rateMax: '',
  contactPhone: '', whatsappNumber: '', instagram: '', youtube: '', facebook: '', googleMaps: '', eventTypes: [], languages: [],
  readyToTravel: false,
});

export function formFromProfile(p: ArtistProfile): ProfileFormState {
  return {
    name: p.name, artistType: p.artistType, city: p.locationCity, area: p.locationArea, bio: p.bio,
    experienceYears: String(p.experienceYears), rateMin: String(p.perEventRateMin), rateMax: String(p.perEventRateMax),
    contactPhone: p.contactPhone, whatsappNumber: p.whatsappNumber ?? '', instagram: p.instagramHandle ?? '',
    youtube: p.youtubeChannel ?? '', facebook: p.facebookUrl ?? '', googleMaps: p.googlePlaceUrl ?? '', eventTypes: p.eventTypesSupported, languages: p.languagesSpoken, readyToTravel: p.readyToTravel,
  };
}

const INDIAN_MOBILE = /^[6-9]\d{9}$/;
const FACEBOOK_URL = /^https?:\/\/(www\.|m\.)?facebook\.com\/\S+$/i;
// Google Maps links: maps.app.goo.gl/goo.gl short links, maps.google.com, or google.com/maps/… (mirrors the backend rule).
const GOOGLE_MAPS_URL = /^https?:\/\/((maps\.app\.)?goo\.gl\/\S+|maps\.google\.com\S*|(www\.)?google\.com\/maps\S*)$/i;
const positiveInt = (s: string) => /^\d+$/.test(s.trim());

export function validateProfileForm(f: ProfileFormState): ProfileFormErrors {
  const e: ProfileFormErrors = {};
  if (!f.name.trim()) e.name = 'Enter your name or stage name';
  if (!f.artistType) e.artistType = 'Pick what kind of artist you are';
  if (!f.city) e.city = 'Select your city';
  if (!f.area.trim()) e.area = 'Enter your area or locality';
  if (!f.bio.trim()) e.bio = 'Write a short bio so planners know what you do';
  if (f.experienceYears && !positiveInt(f.experienceYears)) e.experienceYears = 'Enter whole years';
  if (!positiveInt(f.rateMin)) e.rateMin = 'Enter your starting rate';
  if (!positiveInt(f.rateMax)) e.rateMax = 'Enter your top rate';
  else if (positiveInt(f.rateMin) && Number(f.rateMax) < Number(f.rateMin)) e.rateMax = 'Top rate must be at least the starting rate';
  if (!INDIAN_MOBILE.test(f.contactPhone)) e.contactPhone = 'Enter a valid 10-digit mobile number';
  if (f.whatsappNumber && !INDIAN_MOBILE.test(f.whatsappNumber)) e.whatsappNumber = 'Enter a valid 10-digit WhatsApp number';
  if (f.facebook.trim() && !FACEBOOK_URL.test(f.facebook.trim())) e.facebook = 'Enter your Facebook page link (facebook.com/…)';
  if (f.googleMaps.trim() && !GOOGLE_MAPS_URL.test(f.googleMaps.trim())) e.googleMaps = 'Paste the Google Maps link to your business listing';
  if (f.eventTypes.length === 0) e.eventTypes = 'Pick at least one event type';
  return e;
}

const orNull = (s: string) => (s.trim() ? s.trim() : null);

export function toProfileInput(f: ProfileFormState): ArtistProfileInput {
  return {
    name: f.name.trim(), artistType: f.artistType as ArtistType, locationCity: f.city, locationArea: f.area.trim(), bio: f.bio.trim(),
    experienceYears: Number(f.experienceYears || 0), perEventRateMin: Number(f.rateMin), perEventRateMax: Number(f.rateMax),
    eventTypesSupported: f.eventTypes, languagesSpoken: f.languages, readyToTravel: f.readyToTravel,
    instagramHandle: orNull(f.instagram.replace(/^@/, '')), youtubeChannel: orNull(f.youtube.replace(/^@/, '')), facebookUrl: orNull(f.facebook),
    contactPhone: f.contactPhone, whatsappNumber: orNull(f.whatsappNumber), googlePlaceUrl: orNull(f.googleMaps),
  };
}

/** Map a 422 `details.fields` (API camelCase names) onto form field names. */
export function errorsFromApi(fields: Record<string, string>): ProfileFormErrors {
  const map: Record<string, keyof ProfileFormState> = {
    name: 'name', artistType: 'artistType', locationCity: 'city', locationArea: 'area', bio: 'bio', experienceYears: 'experienceYears',
    perEventRateMin: 'rateMin', perEventRateMax: 'rateMax', contactPhone: 'contactPhone', whatsappNumber: 'whatsappNumber',
    instagramHandle: 'instagram', youtubeChannel: 'youtube', facebookUrl: 'facebook', eventTypesSupported: 'eventTypes', languagesSpoken: 'languages',
    googlePlaceUrl: 'googleMaps',
  };
  const out: ProfileFormErrors = {};
  for (const [k, v] of Object.entries(fields)) if (map[k]) out[map[k]] = v;
  return out;
}
