import { describe, expect, it } from 'vitest';
import { afterAnswer, inquiryActions } from './bookingAnswer';
import type { PlannerInquiry } from '../../api/types';

const base = {
  bookingConfirmed: false, plannerAnswer: null, canReview: false, reviewId: null,
} as Pick<PlannerInquiry, 'bookingConfirmed' | 'plannerAnswer' | 'canReview' | 'reviewId'>;

describe('inquiryActions', () => {
  it('asks the booking question while nothing is known', () => {
    expect(inquiryActions(base)).toEqual({ ask: true, label: null, review: 'none' });
  });
  it('keeps asking after "still deciding"', () => {
    expect(inquiryActions({ ...base, plannerAnswer: 'deciding' })).toEqual({ ask: true, label: 'Still deciding', review: 'none' });
  });
  it('shows booked and waits for the event before reviewing', () => {
    expect(inquiryActions({ ...base, bookingConfirmed: true })).toEqual({ ask: false, label: 'Booking confirmed', review: 'after-event' });
  });
  it('offers the review once allowed', () => {
    expect(inquiryActions({ ...base, bookingConfirmed: true, canReview: true })).toEqual({ ask: false, label: 'Booking confirmed', review: 'write' });
  });
  it('shows the review once written', () => {
    expect(inquiryActions({ ...base, bookingConfirmed: true, reviewId: 'r1' })).toEqual({ ask: false, label: 'Booking confirmed', review: 'written' });
  });
  it('stops asking after "not booked"', () => {
    expect(inquiryActions({ ...base, plannerAnswer: 'not_booked' })).toEqual({ ask: false, label: 'Not booked', review: 'none' });
  });
});

describe('afterAnswer', () => {
  it('goes to the review form when the answer made a review possible', () => {
    expect(afterAnswer({ ...base, bookingConfirmed: true, canReview: true })).toBe('review');
    expect(afterAnswer({ ...base, bookingConfirmed: true })).toBe('stay');
    expect(afterAnswer({ ...base, plannerAnswer: 'not_booked' })).toBe('stay');
  });
});
