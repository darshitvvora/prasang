// Client-side checks mirroring the backend's review rules (contracts/README.md).
export interface ReviewDraft { rating: number; text: string }
export type ReviewErrors = Partial<Record<keyof ReviewDraft, string>>;

export function validateReview(d: ReviewDraft): ReviewErrors {
  const errors: ReviewErrors = {};
  if (!Number.isInteger(d.rating) || d.rating < 1 || d.rating > 5) errors.rating = 'Choose a rating from 1 to 5 stars';
  const len = d.text.trim().length;
  if (len < 20) errors.text = 'Please write at least 20 characters';
  else if (len > 2000) errors.text = 'Please keep it under 2000 characters';
  return errors;
}

export const validateReply = (text: string): string | null => (text.trim() ? null : 'Write a reply first');
export const validateReport = (reason: string): string | null =>
  reason.trim().length >= 10 ? null : 'Tell us why in at least 10 characters';
