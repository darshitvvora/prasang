import { expect, it } from 'vitest';
import { isMockLink, linkDeadline } from './paymentLink';

it('recognises mock links from the fake gateway', () => {
  expect(isMockLink('mock://phonepe/PRS-abc')).toBe(true);
  expect(isMockLink('https://phon.pe/pl/x7Lw3t1Z')).toBe(false);
});

it('shows the link deadline in IST', () => {
  expect(linkDeadline('2026-10-23T09:30:00Z')).toMatch(/23 Oct.*3:00\s?pm/i);
});
