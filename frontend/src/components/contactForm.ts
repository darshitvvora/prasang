// Contact-info (lead) form: client-side validation mirrors the backend's 422 rules.
import type { CreateLeadRequest, LeadSource } from '../api/types';
import type { BudgetRange, EventType } from '../types/artist';

export interface ContactFormState {
  name: string; phone: string; email: string; eventType: EventType; eventDate: string;
  eventCity: string; budgetRange: BudgetRange; notes: string;
}

export type ContactFormErrors = Partial<Record<keyof ContactFormState, string>>;

const INDIAN_MOBILE = /^[6-9]\d{9}$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateContactForm(f: ContactFormState, today: Date = new Date()): ContactFormErrors {
  const errors: ContactFormErrors = {};
  if (!f.name.trim()) errors.name = 'Please enter your name';
  if (!INDIAN_MOBILE.test(f.phone)) errors.phone = 'Enter a valid 10-digit mobile number';
  if (f.email.trim() && !EMAIL.test(f.email.trim())) errors.email = 'Enter a valid email address';
  if (f.eventDate && f.eventDate < today.toISOString().slice(0, 10)) errors.eventDate = 'Event date cannot be in the past';
  return errors;
}

const orNull = (s: string) => (s.trim() ? s.trim() : null);

export function buildLeadRequest(artistId: string, f: ContactFormState, source: LeadSource): CreateLeadRequest {
  return {
    artistId, plannerName: f.name.trim(), plannerPhone: f.phone, plannerEmail: orNull(f.email), eventType: f.eventType,
    eventDate: f.eventDate || null, eventCity: orNull(f.eventCity), budgetRange: f.budgetRange, notes: orNull(f.notes), source,
  };
}
