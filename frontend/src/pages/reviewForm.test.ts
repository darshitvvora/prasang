import { describe, expect, it } from 'vitest';
import { validateReview, validateReply, validateReport } from './reviewForm';

describe('validateReview', () => {
  it('needs a star rating and 20+ characters', () => {
    expect(validateReview({ rating: 0, text: 'ok' })).toEqual({
      rating: 'Choose a rating from 1 to 5 stars', text: 'Please write at least 20 characters',
    });
  });
  it('accepts a complete review', () => {
    expect(validateReview({ rating: 5, text: 'Kept 40 kids spellbound for an hour.' })).toEqual({});
  });
  it('caps the length at 2000 characters', () => {
    expect(validateReview({ rating: 4, text: 'x'.repeat(2001) }).text).toBe('Please keep it under 2000 characters');
  });
});

describe('validateReply / validateReport', () => {
  it('needs some text', () => {
    expect(validateReply('  ')).toBe('Write a reply first');
    expect(validateReply('Thank you!')).toBeNull();
  });
  it('needs a reason of 10+ characters', () => {
    expect(validateReport('fake')).toBe('Tell us why in at least 10 characters');
    expect(validateReport('They never booked me.')).toBeNull();
  });
});
