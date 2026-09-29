import { describe, expect, it } from 'vitest';
import { emptyProfileForm, formFromProfile, toProfileInput, validateProfileForm, type ProfileFormState } from './profileForm';
import profile from '../../../../contracts/examples/artists/me.response.json';
import type { ArtistProfile } from '../../api/types';

const filled: ProfileFormState = {
  ...emptyProfileForm(), name: 'Arjun Malhotra', artistType: 'magician', city: 'Mumbai', area: 'Bandra West',
  bio: 'Close-up magician', experienceYears: '8', rateMin: '15000', rateMax: '25000', contactPhone: '9820011001',
  whatsappNumber: '', instagram: '@arjunmagic', youtube: '', eventTypes: ['wedding'], languages: ['Hindi'], readyToTravel: true,
};

describe('validateProfileForm', () => {
  it('accepts a complete form', () => expect(validateProfileForm(filled)).toEqual({}));
  it('flags every missing required field on an empty form', () => {
    expect(Object.keys(validateProfileForm(emptyProfileForm())).sort()).toEqual(
      ['area', 'artistType', 'bio', 'city', 'contactPhone', 'eventTypes', 'name', 'rateMax', 'rateMin'].sort());
  });
  it('rejects a max rate below the min rate', () =>
    expect(validateProfileForm({ ...filled, rateMin: '30000', rateMax: '20000' })).toHaveProperty('rateMax'));
  it('rejects a malformed WhatsApp number when given', () =>
    expect(validateProfileForm({ ...filled, whatsappNumber: '123' })).toHaveProperty('whatsappNumber'));
});

describe('toProfileInput', () => {
  it('converts strings to numbers, strips @ and nulls empty optionals', () => {
    expect(toProfileInput(filled)).toEqual({
      name: 'Arjun Malhotra', artistType: 'magician', locationCity: 'Mumbai', locationArea: 'Bandra West', bio: 'Close-up magician',
      experienceYears: 8, perEventRateMin: 15000, perEventRateMax: 25000, eventTypesSupported: ['wedding'], languagesSpoken: ['Hindi'],
      readyToTravel: true, instagramHandle: 'arjunmagic', youtubeChannel: null, contactPhone: '9820011001', whatsappNumber: null,
    });
  });
});

describe('formFromProfile', () => {
  it('round-trips the example profile back to the same input', () => {
    const p = profile as unknown as ArtistProfile;
    const input = toProfileInput(formFromProfile(p));
    expect(input.name).toBe(p.name);
    expect(input.perEventRateMax).toBe(p.perEventRateMax);
    expect(input.eventTypesSupported).toEqual(p.eventTypesSupported);
    expect(input.whatsappNumber).toBe(p.whatsappNumber);
  });
});
