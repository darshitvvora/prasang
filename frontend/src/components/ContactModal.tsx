// "Get Contact Info" modal: a signed-in planner shares event details (creating a
// lead, which notifies the artist) and in return sees the artist's phone/WhatsApp.
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, MessageCircle, Phone, X } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import { useCreateLead, useLocations } from '../api/queries';
import { trackContactClick } from '../api/endpoints';
import { imageOr } from '../api/format';
import type { ArtistDetail, CreateLeadResponse, LeadSource } from '../api/types';
import type { BudgetRange, EventType } from '../types/artist';
import { BUDGET_RANGE_LABELS, EVENT_TYPE_LABELS } from '../types/artist';
import { buildLeadRequest, validateContactForm, type ContactFormErrors, type ContactFormState } from './contactForm';
import { InlineError } from './QueryState';

interface Props {
  artist: ArtistDetail;
  source: LeadSource;
  onClose: () => void;
}

const formatPhone = (p: string) => `+91 ${p.slice(0, 5)} ${p.slice(5)}`;

export default function ContactModal({ artist, source, onClose }: Props) {
  const navigate = useNavigate();
  const { status, user, signInWithGoogle } = useAuth();
  const locations = useLocations();
  const createLead = useCreateLead();
  const [signingIn, setSigningIn] = useState(false);
  const [signInError, setSignInError] = useState<unknown>(null);
  const [errors, setErrors] = useState<ContactFormErrors>({});
  const [revealed, setRevealed] = useState<CreateLeadResponse['artist'] | null>(null);
  const [form, setForm] = useState<ContactFormState>({
    name: user?.fullName ?? '', phone: user?.phone ?? '', email: user?.email ?? '', eventType: 'birthday',
    eventDate: '', eventCity: artist.locationCity, budgetRange: '10k_15k', notes: '',
  });

  useEffect(() => {
    trackContactClick(artist.slug).catch(() => undefined); // analytics only; never block the planner
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, [artist.slug]);

  // Prefill once the user becomes known (e.g. right after signing in here).
  useEffect(() => {
    if (!user) return;
    setForm((f) => ({ ...f, name: f.name || user.fullName, phone: f.phone || (user.phone ?? ''), email: f.email || (user.email ?? '') }));
  }, [user]);

  const set = <K extends keyof ContactFormState>(key: K, value: ContactFormState[K]) => setForm((f) => ({ ...f, [key]: value }));

  async function handleSignIn() {
    setSigningIn(true);
    setSignInError(null);
    try {
      const result = await signInWithGoogle('planner');
      if (result.status === 'needsProfile') {
        navigate(`/signup?step=profile&role=planner&next=${encodeURIComponent(`/profile/${artist.slug}`)}`);
      }
    } catch (e) {
      setSignInError(e);
    } finally {
      setSigningIn(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const found = validateContactForm(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    const res = await createLead.mutateAsync(buildLeadRequest(artist.artistId, form, source)).catch(() => null);
    if (res) setRevealed(res.artist);
  }

  const cities = locations.data?.cities.map((c) => c.name) ?? [artist.locationCity];

  let content: React.ReactNode;
  if (revealed) {
    const whatsapp = revealed.whatsappNumber ?? revealed.contactPhone;
    content = (
      <div className="contact-revealed">
        <div className="contact-revealed-icon"><CheckCircle size={40} /></div>
        <h2 className="contact-revealed-title">{revealed.name}'s Contact Details</h2>
        <p className="contact-revealed-sub">We've notified {revealed.name} about your interest. They'll reach out soon!</p>
        <div className="contact-revealed-info">
          <div className="contact-info-item">
            <span className="contact-info-label">Phone</span>
            <span className="contact-info-value">{formatPhone(revealed.contactPhone)}</span>
          </div>
          {revealed.instagramHandle && (
            <div className="contact-info-item">
              <span className="contact-info-label">Instagram</span>
              <span className="contact-info-value">@{revealed.instagramHandle}</span>
            </div>
          )}
        </div>
        <div className="contact-revealed-actions">
          <a href={`tel:+91${revealed.contactPhone}`} className="contact-call-btn"><Phone size={18} /> Call Now</a>
          <a href={`https://wa.me/91${whatsapp}`} target="_blank" rel="noopener noreferrer" className="contact-whatsapp-btn">
            <MessageCircle size={18} /> WhatsApp
          </a>
        </div>
        <button className="contact-close-btn" onClick={onClose}>Close</button>
      </div>
    );
  } else if (status === 'loading') {
    content = <p className="contact-modal-sub">Loading…</p>;
  } else if (status !== 'signedIn' || !user) {
    content = (
      <div className="contact-revealed">
        <h2 className="contact-revealed-title">Sign in to see {artist.name}'s contact details</h2>
        <p className="contact-revealed-sub">It's free. We ask so artists get genuine enquiries — and so you can track your inquiries in one place.</p>
        <InlineError error={signInError} />
        <button className="contact-form-submit" onClick={handleSignIn} disabled={signingIn}>
          {signingIn ? 'Signing in...' : 'Continue with Google'}
        </button>
      </div>
    );
  } else if (user.role === 'artist') {
    content = (
      <div className="contact-revealed">
        <h2 className="contact-revealed-title">Contact details are for event planners</h2>
        <p className="contact-revealed-sub">You're signed in as an artist. Sign in with a planner account to contact {artist.name}.</p>
        <button className="contact-close-btn" onClick={onClose}>Close</button>
      </div>
    );
  } else {
    content = (
      <>
        <div className="contact-modal-header">
          <img src={imageOr(artist.profileImageUrl)} alt={artist.name} className="contact-modal-artist-img" />
          <div>
            <h2 className="contact-modal-title">Get {artist.name}'s Contact Details</h2>
            <p className="contact-modal-sub">Share your event details so {artist.name} can prepare for you.</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="contact-form" noValidate>
          <div className="contact-form-row">
            <div className="contact-form-group">
              <label className="contact-form-label" htmlFor="cf-name">Your Name *</label>
              <input id="cf-name" type="text" className="contact-form-input" placeholder="Rahul Sharma" value={form.name}
                onChange={(e) => set('name', e.target.value)} aria-invalid={!!errors.name} />
              {errors.name && <span className="contact-form-error">{errors.name}</span>}
            </div>
            <div className="contact-form-group">
              <label className="contact-form-label" htmlFor="cf-phone">Phone Number *</label>
              <div className="contact-form-phone">
                <span className="phone-prefix">+91</span>
                <input id="cf-phone" type="tel" className="contact-form-input phone-input" placeholder="9876543210" value={form.phone}
                  onChange={(e) => set('phone', e.target.value.replace(/\D/g, '').slice(0, 10))} maxLength={10} aria-invalid={!!errors.phone} />
              </div>
              {errors.phone && <span className="contact-form-error">{errors.phone}</span>}
            </div>
          </div>

          <div className="contact-form-row">
            <div className="contact-form-group">
              <label className="contact-form-label" htmlFor="cf-event-type">Event Type</label>
              <select id="cf-event-type" className="contact-form-select" value={form.eventType} onChange={(e) => set('eventType', e.target.value as EventType)}>
                {(Object.keys(EVENT_TYPE_LABELS) as EventType[]).map((t) => <option key={t} value={t}>{EVENT_TYPE_LABELS[t]}</option>)}
              </select>
            </div>
            <div className="contact-form-group">
              <label className="contact-form-label" htmlFor="cf-date">Event Date</label>
              <input id="cf-date" type="date" className="contact-form-input" value={form.eventDate}
                onChange={(e) => set('eventDate', e.target.value)} min={new Date().toISOString().split('T')[0]} />
              {errors.eventDate && <span className="contact-form-error">{errors.eventDate}</span>}
            </div>
          </div>

          <div className="contact-form-row">
            <div className="contact-form-group">
              <label className="contact-form-label" htmlFor="cf-city">Event City</label>
              <select id="cf-city" className="contact-form-select" value={form.eventCity} onChange={(e) => set('eventCity', e.target.value)}>
                {cities.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="contact-form-group">
              <label className="contact-form-label" htmlFor="cf-email">Email (optional)</label>
              <input id="cf-email" type="email" className="contact-form-input" placeholder="you@example.com" value={form.email}
                onChange={(e) => set('email', e.target.value)} aria-invalid={!!errors.email} />
              {errors.email && <span className="contact-form-error">{errors.email}</span>}
            </div>
          </div>

          <div className="contact-form-group">
            <span className="contact-form-label">Your Budget</span>
            <div className="budget-chips">
              {(Object.keys(BUDGET_RANGE_LABELS) as BudgetRange[]).map((b) => (
                <button type="button" key={b} className={`budget-chip${form.budgetRange === b ? ' active' : ''}`} onClick={() => set('budgetRange', b)}>
                  {BUDGET_RANGE_LABELS[b]}
                </button>
              ))}
            </div>
          </div>

          <div className="contact-form-group">
            <label className="contact-form-label" htmlFor="cf-notes">Special Requirements (optional)</label>
            <textarea id="cf-notes" className="contact-form-textarea" placeholder="E.g. outdoor venue, 200 guests, Bollywood theme..."
              value={form.notes} onChange={(e) => set('notes', e.target.value)} rows={3} maxLength={1000} />
          </div>

          <InlineError error={createLead.error} />
          <button type="submit" className="contact-form-submit" disabled={createLead.isPending}>
            {createLead.isPending ? 'Processing...' : 'View Contact Info'}
          </button>
        </form>
      </>
    );
  }

  return (
    <div className="contact-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="contact-modal" role="dialog" aria-modal="true" aria-label="Get contact info">
        <button className="contact-modal-close" onClick={onClose} aria-label="Close"><X size={20} /></button>
        {content}
      </div>
    </div>
  );
}
