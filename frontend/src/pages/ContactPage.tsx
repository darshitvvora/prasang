import { useState } from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { useSendContactMessage, useSiteInfo } from '../api/queries';
import { ApiError } from '../api/client';
import type { SiteInfo } from '../api/types';
import { buildContactRequest, CONTACT_TOPICS, emptyContact, validateContact, type ContactErrors, type ContactState } from './contactMessage';
import './legal/LegalPages.css';
import './site.css';

export function SiteContactDetails({ info }: { info: SiteInfo }) {
  if (!info.supportEmail && !info.supportPhone && !info.businessAddress) return null;
  return (
    <ul className="site-contact-details">
      {info.supportEmail && <li>Email: <a href={`mailto:${info.supportEmail}`}>{info.supportEmail}</a></li>}
      {info.supportPhone && <li>Phone: <a href={`tel:+91${info.supportPhone}`}>+91 {info.supportPhone}</a></li>}
      {info.businessAddress && <li>Address: {info.businessAddress}</li>}
    </ul>
  );
}

export default function ContactPage() {
  const site = useSiteInfo();
  const send = useSendContactMessage();
  const [form, setForm] = useState<ContactState>(emptyContact);
  const [errors, setErrors] = useState<ContactErrors>({});
  const set = <K extends keyof ContactState>(k: K, v: ContactState[K]) => setForm((f) => ({ ...f, [k]: v }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const found = validateContact(form);
    setErrors(found);
    if (Object.keys(found).length === 0) send.mutate(buildContactRequest(form));
  };
  const serverError = send.error instanceof ApiError ? send.error.message : send.error ? 'Something went wrong. Please try again.' : null;

  return (
    <>
      <Navbar />
      <main className="legal-page-container">
        <div className="legal-page-header">
          <h1 className="legal-page-title">Contact us</h1>
          <p className="legal-page-date">Questions, payment issues or something to report — we read every message.</p>
        </div>
        <div className="legal-page-content">
          {site.data && <SiteContactDetails info={site.data} />}
          {send.isSuccess ? (
            <p className="site-contact-success" role="status">Thanks — we'll get back to you within 2 working days.</p>
          ) : (
            <form className="site-contact-form" onSubmit={submit} noValidate>
              <label>Your name
                <input value={form.name} onChange={(e) => set('name', e.target.value)} maxLength={120} />
                {errors.name && <span className="contact-form-error">{errors.name}</span>}
              </label>
              <label>Mobile number or email
                <input value={form.contact} onChange={(e) => set('contact', e.target.value)} maxLength={255} />
                {errors.contact && <span className="contact-form-error">{errors.contact}</span>}
              </label>
              <label>Topic
                <select value={form.topic} onChange={(e) => set('topic', e.target.value as ContactState['topic'])}>
                  {CONTACT_TOPICS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </label>
              <label>Message
                <textarea value={form.message} onChange={(e) => set('message', e.target.value)} rows={6} maxLength={4000} />
                {errors.message && <span className="contact-form-error">{errors.message}</span>}
              </label>
              {serverError && <p className="contact-form-error" role="alert">{serverError}</p>}
              <button type="submit" className="site-contact-submit" disabled={send.isPending}>
                {send.isPending ? 'Sending…' : 'Send message'}
              </button>
            </form>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}
