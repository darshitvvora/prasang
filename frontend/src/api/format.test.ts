import { describe, expect, it } from 'vitest';
import { formatBudget, formatDate, formatPrice, relativeTime } from './format';

describe('formatPrice', () => {
  it('abbreviates thousands', () => expect(formatPrice(15000)).toBe('₹15K'));
  it('keeps small amounts', () => expect(formatPrice(800)).toBe('₹800'));
  it('keeps one decimal for lakhs-ish odd thousands', () => expect(formatPrice(12500)).toBe('₹12.5K'));
});

describe('formatBudget', () => {
  it('formats a closed range', () => expect(formatBudget(15000, 25000)).toBe('₹15K – ₹25K'));
  it('formats an open-ended range', () => expect(formatBudget(50000, null)).toBe('₹50K+'));
});

describe('relativeTime', () => {
  const now = new Date('2026-09-29T12:00:00Z');
  it('minutes', () => expect(relativeTime('2026-09-29T11:55:00Z', now)).toBe('5 minutes ago'));
  it('hours', () => expect(relativeTime('2026-09-29T07:00:00Z', now)).toBe('5 hours ago'));
  it('singular day', () => expect(relativeTime('2026-09-28T11:00:00Z', now)).toBe('1 day ago'));
  it('days', () => expect(relativeTime('2026-09-26T12:00:00Z', now)).toBe('3 days ago'));
  it('just now', () => expect(relativeTime('2026-09-29T11:59:40Z', now)).toBe('just now'));
});

describe('formatDate', () => {
  it('formats YYYY-MM-DD without timezone drift', () => expect(formatDate('2026-01-05')).toBe('Jan 5, 2026'));
});
