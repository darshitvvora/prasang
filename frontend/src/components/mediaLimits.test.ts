import { describe, expect, it } from 'vitest';
import { canUseHd, deletionNote, quotaSummary, uploadProblem } from './mediaLimits';
import type { MediaQuota } from '../api/types';

const MB = 1024 * 1024;
const q = (img: [number, number], vid: [number, number], hd: [number, number]): MediaQuota => ({
  images: { used: img[0], limit: img[1] }, videos: { used: vid[0], limit: vid[1] }, hdVideos: { used: hd[0], limit: hd[1] },
});

describe('uploadProblem', () => {
  it('caps photos at 10 MB, videos at 40 MB and HD at 200 MB', () => {
    expect(uploadProblem({ name: 'a.jpg', size: 11 * MB }, 'image', false)).toBe('a.jpg is too large (max 10 MB)');
    expect(uploadProblem({ name: 'v.mp4', size: 41 * MB }, 'video', false)).toBe('v.mp4 is too large (max 40 MB)');
    expect(uploadProblem({ name: 'v.mp4', size: 41 * MB }, 'video', true)).toBeNull();
    expect(uploadProblem({ name: 'v.mp4', size: 201 * MB }, 'video', true)).toBe('v.mp4 is too large (max 200 MB)');
  });
});

describe('quotaSummary', () => {
  it('lists what the plan allows', () => {
    expect(quotaSummary(q([3, 5], [0, 1], [0, 0]))).toBe('Photos 3/5 · Videos 0/1');
    expect(quotaSummary(q([3, 50], [1, 8], [1, 2]))).toBe('Photos 3/50 · Videos 1/8 · HD videos 1/2');
  });
  it('explains the Free plan', () => {
    expect(quotaSummary(q([0, 0], [0, 0], [0, 0]))).toBe('Uploads start on the Basic plan');
  });
});

describe('canUseHd', () => {
  it('is only offered while HD slots are left', () => {
    expect(canUseHd(q([0, 50], [0, 8], [1, 2]))).toBe(true);
    expect(canUseHd(q([0, 50], [0, 8], [2, 2]))).toBe(false);
    expect(canUseHd(q([0, 20], [0, 3], [0, 0]))).toBe(false);
  });
});

describe('deletionNote', () => {
  it('warns about items scheduled for deletion', () => {
    expect(deletionNote('2026-10-27T05:00:00Z')).toBe('Hidden — deleted on Oct 27, 2026 unless you upgrade');
    expect(deletionNote(null)).toBeNull();
  });
});
