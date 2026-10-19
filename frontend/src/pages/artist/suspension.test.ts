import { describe, expect, it } from 'vitest';
import { suspensionMessage } from './suspension';

describe('suspensionMessage', () => {
  it('is null for visible profiles', () => {
    expect(suspensionMessage({ suspended: false, suspensionReason: null })).toBeNull();
  });
  it('explains the reason when suspended', () => {
    expect(suspensionMessage({ suspended: true, suspensionReason: 'Profile photo is not you' }))
      .toBe('Your profile is hidden from planners: Profile photo is not you.');
  });
  it('has a fallback when no reason was given', () => {
    expect(suspensionMessage({ suspended: true, suspensionReason: null })).toBe('Your profile is hidden from planners.');
  });
});
