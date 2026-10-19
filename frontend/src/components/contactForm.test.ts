import { describe, expect, it } from 'vitest';
import { buildLeadRequest, validateContactForm, type ContactFormState } from './contactForm';

const base: ContactFormState = { name: 'Neha Kulkarni', phone: '9920012345', email: '', eventType: 'wedding', eventDate: '', eventCity: 'Mumbai', budgetRange: '15k_25k', notes: '' };

describe('validateContactForm', () => {
  it('accepts a complete form', () => expect(validateContactForm(base)).toEqual({}));
  it('requires a name', () => expect(validateContactForm({ ...base, name: '  ' })).toHaveProperty('name'));
  it('rejects phone numbers that are not Indian mobiles', () => {
    expect(validateContactForm({ ...base, phone: '12345' })).toHaveProperty('phone');
    expect(validateContactForm({ ...base, phone: '5123456789' })).toHaveProperty('phone');
  });
  it('rejects a malformed optional email', () => expect(validateContactForm({ ...base, email: 'neha@' })).toHaveProperty('email'));
  it('rejects event dates in the past', () =>
    expect(validateContactForm({ ...base, eventDate: '2020-01-01' }, new Date('2026-09-29'))).toHaveProperty('eventDate'));
});

describe('buildLeadRequest', () => {
  it('maps the form to the contract, trimming and nulling empties', () => {
    expect(buildLeadRequest('art-001', { ...base, name: ' Neha ', notes: ' ' }, 'profile')).toEqual({
      artistId: 'art-001', plannerName: 'Neha', plannerPhone: '9920012345', plannerEmail: null, eventType: 'wedding',
      eventDate: null, eventCity: 'Mumbai', budgetRange: '15k_25k', notes: null, source: 'profile',
    });
  });
});
