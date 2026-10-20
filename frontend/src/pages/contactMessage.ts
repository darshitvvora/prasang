// Contact page form: client-side validation mirrors the backend's 422 rules (POST /contact).
import type { ContactRequest, ContactTopic } from '../api/types';

export interface ContactState { name: string; contact: string; topic: ContactTopic; message: string }
export type ContactErrors = Partial<Record<keyof ContactState, string>>;

export const emptyContact: ContactState = { name: '', contact: '', topic: 'general', message: '' };

export const CONTACT_TOPICS: { value: ContactTopic; label: string }[] = [
  { value: 'general', label: 'General question' },
  { value: 'artist_support', label: 'Help with my artist profile' },
  { value: 'payments', label: 'Payments and plans' },
  { value: 'report', label: 'Report a problem or a profile' },
];

const INDIAN_MOBILE = /^[6-9]\d{9}$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateContact(f: ContactState): ContactErrors {
  const errors: ContactErrors = {};
  if (!f.name.trim()) errors.name = 'Please enter your name';
  const contact = f.contact.trim();
  if (!INDIAN_MOBILE.test(contact) && !EMAIL.test(contact)) errors.contact = 'Enter a 10-digit mobile number or an email address';
  if (f.message.trim().length < 10) errors.message = 'Please write at least 10 characters';
  return errors;
}

export function buildContactRequest(f: ContactState): ContactRequest {
  return { name: f.name.trim(), contact: f.contact.trim(), topic: f.topic, message: f.message.trim() };
}
