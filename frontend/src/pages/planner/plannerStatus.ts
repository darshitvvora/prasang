import type { InquiryStatus } from '../../types/artist';

export const STATUS_COLORS: Record<InquiryStatus, string> = {
  pending: '#f59e0b',
  responded: '#60a5fa',
  confirmed: '#4ade80',
  declined: '#666',
};
