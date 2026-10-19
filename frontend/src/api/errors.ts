import { ApiError } from './client';

/** User-facing message for any thrown value (ApiError messages come from the API contract). */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return 'Something went wrong. Please try again.';
}
