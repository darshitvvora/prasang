// What the planner sees on an inquiry: the "did you book?" question, a booking label, and the review action.
import type { PlannerInquiry } from '../../api/types';

type BookingFields = Pick<PlannerInquiry, 'bookingConfirmed' | 'plannerAnswer' | 'canReview' | 'reviewId'>;
export type ReviewAction = 'none' | 'after-event' | 'write' | 'written';
export interface InquiryActions { ask: boolean; label: string | null; review: ReviewAction }

export function inquiryActions(i: BookingFields): InquiryActions {
  if (i.bookingConfirmed) {
    const review: ReviewAction = i.reviewId ? 'written' : i.canReview ? 'write' : 'after-event';
    return { ask: false, label: 'Booking confirmed', review };
  }
  if (i.plannerAnswer === 'not_booked') return { ask: false, label: 'Not booked', review: 'none' };
  return { ask: true, label: i.plannerAnswer === 'deciding' ? 'Still deciding' : null, review: 'none' };
}

export function afterAnswer(updated: BookingFields): 'review' | 'stay' {
  return updated.canReview && !updated.reviewId ? 'review' : 'stay';
}
