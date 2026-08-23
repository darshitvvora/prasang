import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, MapPin, Star, BadgeCheck, Crown, AtSign,
  PlayCircle, Heart, Share2, Phone, MessageCircle, Calendar,
  Clock, ChevronRight, X, CheckCircle,
} from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { mockArtists } from '../data/mockArtists';
import { ARTIST_TYPE_LABELS, ARTIST_TYPE_COLORS } from '../types/artist';
import './ArtistProfilePage.css';

const MOCK_REVIEWS = [
  { id: 1, name: 'Rahul Mehta', rating: 5, date: 'Dec 2025', event: 'Wedding', text: 'Absolutely phenomenal! The crowd went wild. Best decision we made for our wedding.' },
  { id: 2, name: 'Sneha Patel', rating: 5, date: 'Nov 2025', event: 'Corporate Event', text: 'Very professional, arrived early, took briefing seriously. Our team loved every moment.' },
  { id: 3, name: 'Ankit Sharma', rating: 4, date: 'Oct 2025', event: 'Birthday Party', text: 'Great performer! Kept the energy up the entire evening. Will book again for sure.' },
];

const SIMILAR_ARTISTS_IDS = ['art-002', 'art-003', 'art-005'];

const EVENT_TYPES = ['Birthday', 'Wedding', 'Pre-Wedding', 'Anniversary', 'Corporate', 'House Party', 'Other'];
const BUDGET_RANGES = ['₹5K–10K', '₹10K–15K', '₹15K–25K', '₹25K–50K', '₹50K+'];

function Stars({ rating }: { rating: number }) {
  return (
    <div className="stars-row" aria-label={`${rating} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          size={14}
          fill={i <= Math.round(rating) ? '#f59e0b' : 'none'}
          color={i <= Math.round(rating) ? '#f59e0b' : '#d1d5db'}
        />
      ))}
    </div>
  );
}

export default function ArtistProfilePage() {
  const { slug } = useParams<{ slug: string }>();
  const artist = mockArtists.find((a) => a.slug === slug) ?? mockArtists[0];
  const similar = mockArtists.filter((a) => SIMILAR_ARTISTS_IDS.includes(a.artistId) && a.artistId !== artist.artistId).slice(0, 3);

  const [isFavorited, setIsFavorited] = useState(false);
  const [contactOpen, setContactOpen] = useState(false);
  const [contactStep, setContactStep] = useState<'form' | 'revealed'>('form');
  const [form, setForm] = useState({ name: '', phone: '', email: '', eventType: 'Birthday', eventDate: '', budget: '₹10K–15K', notes: '' });
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<'media' | 'reviews'>('media');

  function openContact() {
    setContactOpen(true);
    setContactStep('form');
    document.body.style.overflow = 'hidden';
  }

  function closeContact() {
    setContactOpen(false);
    setContactStep('form');
    document.body.style.overflow = '';
  }

  async function handleContactSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.phone.trim()) return;
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 1000)); // simulate API call
    setSubmitting(false);
    setContactStep('revealed');
  }

  return (
    <>
      <Navbar />
      <div className="profile-page">
        {/* Back + breadcrumb */}
        <div className="profile-breadcrumb container">
          <Link to="/search" className="profile-back-btn">
            <ArrowLeft size={16} /> Back to Search
          </Link>
          <span className="profile-breadcrumb-sep">/</span>
          <span className="profile-breadcrumb-type">{ARTIST_TYPE_LABELS[artist.artistType]}</span>
          <span className="profile-breadcrumb-sep">/</span>
          <span className="profile-breadcrumb-name">{artist.name}</span>
        </div>

        <div className="container profile-body">
          {/* ---- Left: Main Content ---- */}
          <main className="profile-main">
            {/* Hero Card */}
            <div className="profile-hero-card">
              <div className="profile-hero-image-wrap">
                <img
                  src={artist.profileImageUrl}
                  alt={artist.name}
                  className="profile-hero-image"
                />
                {artist.isFeatured && (
                  <div className="profile-featured-badge">
                    <Crown size={13} /> Featured
                  </div>
                )}
                {/* <div className={`profile-status-dot ${artist.availabilityStatus}`} /> */}
              </div>

              <div className="profile-hero-info">
                <div className="profile-hero-top">
                  <div>
                    <div className="profile-name-row">
                      <h1 className="profile-name">{artist.name}</h1>
                      {artist.isVerified && (
                        <BadgeCheck className="profile-verified-icon" aria-label="Verified artist" />
                      )}
                    </div>
                    <div className="profile-type-location">
                      <span
                        className="profile-type-badge"
                        style={{ background: ARTIST_TYPE_COLORS[artist.artistType] }}
                      >
                        {ARTIST_TYPE_LABELS[artist.artistType]}
                      </span>
                      <span className="profile-location">
                        <MapPin size={14} />
                        {artist.locationArea}, {artist.locationCity}
                      </span>
                    </div>
                  </div>
                  <div className="profile-hero-actions">
                    <button
                      className={`profile-fav-btn${isFavorited ? ' active' : ''}`}
                      onClick={() => setIsFavorited(!isFavorited)}
                      aria-label={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
                    >
                      <Heart size={20} fill={isFavorited ? 'currentColor' : 'none'} />
                    </button>
                    <button className="profile-share-btn" aria-label="Share profile">
                      <Share2 size={18} />
                    </button>
                  </div>
                </div>

                <div className="profile-rating-row">
                  <Stars rating={artist.averageRating} />
                  <span className="profile-rating-num">{artist.averageRating}</span>
                  <span className="profile-review-count">({artist.totalReviews} reviews)</span>
                  <span className="profile-experience">{artist.experienceYears} yrs exp.</span>
                </div>

                <p className="profile-bio">{artist.bio}</p>

                <div className="profile-social-row">
                  {artist.instagramHandle && (
                    <a href={`https://instagram.com/${artist.instagramHandle}`} target="_blank" rel="noopener noreferrer" className="profile-social-link">
                      <AtSign size={18} /> @{artist.instagramHandle}
                    </a>
                  )}
                  {artist.youtubeChannel && (
                    <a href={`https://youtube.com/@${artist.youtubeChannel}`} target="_blank" rel="noopener noreferrer" className="profile-social-link">
                      <PlayCircle size={18} /> {artist.youtubeChannel}
                    </a>
                  )}
                </div>

                <div className="profile-stats-row">
                  <div className="profile-stat">
                    <span className="profile-stat-val">{artist.totalReviews}+</span>
                    <span className="profile-stat-lbl">Events Done</span>
                  </div>
                  <div className="profile-stat">
                    <span className="profile-stat-val">{artist.experienceYears}+</span>
                    <span className="profile-stat-lbl">Years Active</span>
                  </div>
                  <div className="profile-stat">
                    <span className="profile-stat-val">{artist.averageRating}</span>
                    <span className="profile-stat-lbl">Avg Rating</span>
                  </div>
                  {/* <div className="profile-stat">
                    <span className={`profile-avail-dot ${artist.availabilityStatus}`} />
                    <span className="profile-stat-lbl">
                      {artist.availabilityStatus === 'available' ? 'Available' : artist.availabilityStatus === 'busy' ? 'Busy' : 'Unavailable'}
                    </span>
                  </div> */}
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="profile-tabs" role="tablist">
              {(['media', 'reviews'] as const).map((tab) => (
                <button
                  key={tab}
                  className={`profile-tab${activeTab === tab ? ' active' : ''}`}
                  role="tab"
                  aria-selected={activeTab === tab}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  {tab === 'reviews' && <span className="profile-tab-badge">{MOCK_REVIEWS.length}</span>}
                </button>
              ))}
            </div>

            {/* Tab: About */}
            {/* {activeTab === 'about' && (
              <div className="profile-tab-content" role="tabpanel">
                <section className="profile-section">
                  <h2 className="profile-section-title">About</h2>
                  <p className="profile-about-text">{artist.bio} They bring professionalism, energy, and creativity to every event, ensuring an unforgettable experience for your guests.</p>
                </section>

                <section className="profile-section">
                  <h2 className="profile-section-title">Performance Details</h2>
                  <div className="profile-details-grid">
                    <div className="profile-detail-item">
                      <Calendar size={16} className="profile-detail-icon" />
                      <div>
                        <div className="profile-detail-label">Availability</div>
                        <div className="profile-detail-value capitalize">{artist.availabilityStatus}</div>
                      </div>
                    </div>
                    <div className="profile-detail-item">
                      <Clock size={16} className="profile-detail-icon" />
                      <div>
                        <div className="profile-detail-label">Experience</div>
                        <div className="profile-detail-value">{artist.experienceYears} years</div>
                      </div>
                    </div>
                    <div className="profile-detail-item">
                      <MapPin size={16} className="profile-detail-icon" />
                      <div>
                        <div className="profile-detail-label">Base Location</div>
                        <div className="profile-detail-value">{artist.locationArea}, {artist.locationCity}</div>
                      </div>
                    </div>
                    <div className="profile-detail-item">
                      <Star size={16} className="profile-detail-icon" />
                      <div>
                        <div className="profile-detail-label">Artist Type</div>
                        <div className="profile-detail-value">{ARTIST_TYPE_LABELS[artist.artistType]}</div>
                      </div>
                    </div>
                  </div>
                </section>

                <section className="profile-section">
                  <h2 className="profile-section-title">What's Included</h2>
                  <ul className="profile-includes-list">
                    {['Professional performance for agreed duration', 'Own equipment and setup', 'Prior event consultation call', 'Customisation based on event theme', 'Backup plan for technical issues'].map((item) => (
                      <li key={item} className="profile-include-item">
                        <CheckCircle size={16} className="profile-check-icon" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </section>
              </div>
            )} */}

            {/* Tab: Media */}
            {activeTab === 'media' && (
              <div className="profile-tab-content" role="tabpanel">
                <div className="profile-media-grid">
                  {[1, 2, 3, 4, 5, 6].map((i) => (
                    <div key={i} className="profile-media-item">
                      <img
                        src={artist.profileImageUrl}
                        alt={`${artist.name} performance ${i}`}
                        className="profile-media-img"
                        loading="lazy"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tab: Reviews */}
            {activeTab === 'reviews' && (
              <div className="profile-tab-content" role="tabpanel">
                <div className="reviews-summary">
                  <div className="reviews-summary-score">
                    <span className="reviews-big-score">{artist.averageRating}</span>
                    <Stars rating={artist.averageRating} />
                    <span className="reviews-total">{artist.totalReviews} reviews</span>
                  </div>
                </div>

                <div className="reviews-list">
                  {MOCK_REVIEWS.map((r) => (
                    <div key={r.id} className="review-card">
                      <div className="review-card-header">
                        <div className="review-avatar">{r.name[0]}</div>
                        <div>
                          <div className="review-name">{r.name}</div>
                          <div className="review-meta">{r.event} · {r.date}</div>
                        </div>
                        <Stars rating={r.rating} />
                      </div>
                      <p className="review-text">{r.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Similar Artists */}
            {similar.length > 0 && (
              <section className="profile-section profile-similar-section">
                <div className="profile-similar-header">
                  <h2 className="profile-section-title">Similar Artists You Might Like</h2>
                  <Link to="/search" className="profile-similar-see-all">See all <ChevronRight size={15} /></Link>
                </div>
                <div className="profile-similar-grid">
                  {similar.map((a) => (
                    <Link to={`/profile/${a.slug}`} key={a.artistId} className="similar-card">
                      <img src={a.profileImageUrl} alt={a.name} className="similar-card-img" loading="lazy" />
                      <div className="similar-card-body">
                        <div className="similar-card-name">{a.name}</div>
                        <div className="similar-card-type" style={{ color: ARTIST_TYPE_COLORS[a.artistType] }}>
                          {ARTIST_TYPE_LABELS[a.artistType]}
                        </div>
                        <div className="similar-card-rating">
                          <Star size={12} fill="#f59e0b" color="#f59e0b" /> {a.averageRating}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </main>

          {/* ---- Right: Sticky Booking Card ---- */}
          <aside className="profile-sidebar">
            <div className="profile-booking-card">
              <div className="booking-price-row">
                <div>
                  <div className="booking-price">
                    ₹{(artist.perEventRateMin / 1000).toFixed(0)}K – ₹{(artist.perEventRateMax / 1000).toFixed(0)}K
                  </div>
                  <div className="booking-price-label">per event</div>
                </div>
                {artist.isVerified && (
                  <span className="booking-verified-chip">
                    <BadgeCheck size={13} /> Verified
                  </span>
                )}
              </div>

              <button className="booking-contact-btn" onClick={openContact}>
                <Phone size={18} /> Get Contact Info
              </button>

              <a
                href={`https://wa.me/919876543210`}
                target="_blank"
                rel="noopener noreferrer"
                className="booking-whatsapp-btn"
              >
                <MessageCircle size={18} /> WhatsApp
              </a>

              <div className="booking-note">
                <CheckCircle size={14} />
                {artist.name} will be notified instantly when you request contact info.
              </div>

              <div className="booking-divider" />

              <ul className="booking-features">
                <li><CheckCircle size={14} /> No booking fees — pay artist directly</li>
                <li><CheckCircle size={14} /> Free to contact and negotiate</li>
                <li><CheckCircle size={14} /> {artist.totalReviews}+ verified reviews</li>
              </ul>
            </div>
          </aside>
        </div>
      </div>

      {/* ---- Contact Modal ---- */}
      {contactOpen && (
        <div className="contact-modal-overlay" onClick={(e) => e.target === e.currentTarget && closeContact()}>
          <div className="contact-modal" role="dialog" aria-modal="true" aria-label="Get contact info">
            <button className="contact-modal-close" onClick={closeContact} aria-label="Close">
              <X size={20} />
            </button>

            {contactStep === 'form' ? (
              <>
                <div className="contact-modal-header">
                  <img src={artist.profileImageUrl} alt={artist.name} className="contact-modal-artist-img" />
                  <div>
                    <h2 className="contact-modal-title">Get {artist.name}'s Contact Details</h2>
                    <p className="contact-modal-sub">Share your event details so {artist.name} can prepare for you.</p>
                  </div>
                </div>

                <form onSubmit={handleContactSubmit} className="contact-form">
                  <div className="contact-form-row">
                    <div className="contact-form-group">
                      <label className="contact-form-label">Your Name *</label>
                      <input
                        type="text"
                        className="contact-form-input"
                        placeholder="Rahul Sharma"
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        required
                      />
                    </div>
                    <div className="contact-form-group">
                      <label className="contact-form-label">Phone Number *</label>
                      <div className="contact-form-phone">
                        <span className="phone-prefix">+91</span>
                        <input
                          type="tel"
                          className="contact-form-input phone-input"
                          placeholder="9876543210"
                          value={form.phone}
                          onChange={(e) => setForm({ ...form, phone: e.target.value.replace(/\D/g, '').slice(0, 10) })}
                          maxLength={10}
                          required
                        />
                      </div>
                    </div>
                  </div>

                  <div className="contact-form-row">
                    <div className="contact-form-group">
                      <label className="contact-form-label">Event Type</label>
                      <select
                        className="contact-form-select"
                        value={form.eventType}
                        onChange={(e) => setForm({ ...form, eventType: e.target.value })}
                      >
                        {EVENT_TYPES.map((t) => <option key={t}>{t}</option>)}
                      </select>
                    </div>
                    <div className="contact-form-group">
                      <label className="contact-form-label">Event Date</label>
                      <input
                        type="date"
                        className="contact-form-input"
                        value={form.eventDate}
                        onChange={(e) => setForm({ ...form, eventDate: e.target.value })}
                        min={new Date().toISOString().split('T')[0]}
                      />
                    </div>
                  </div>

                  <div className="contact-form-group">
                    <label className="contact-form-label">Your Budget</label>
                    <div className="budget-chips">
                      {BUDGET_RANGES.map((b) => (
                        <button
                          type="button"
                          key={b}
                          className={`budget-chip${form.budget === b ? ' active' : ''}`}
                          onClick={() => setForm({ ...form, budget: b })}
                        >
                          {b}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="contact-form-group">
                    <label className="contact-form-label">Special Requirements (optional)</label>
                    <textarea
                      className="contact-form-textarea"
                      placeholder="E.g. outdoor venue, 200 guests, Bollywood theme..."
                      value={form.notes}
                      onChange={(e) => setForm({ ...form, notes: e.target.value })}
                      rows={3}
                    />
                  </div>

                  <button type="submit" className="contact-form-submit" disabled={submitting}>
                    {submitting ? 'Processing...' : 'View Contact Info'}
                  </button>
                </form>
              </>
            ) : (
              <div className="contact-revealed">
                <div className="contact-revealed-icon">
                  <CheckCircle size={40} />
                </div>
                <h2 className="contact-revealed-title">{artist.name}'s Contact Details</h2>
                <p className="contact-revealed-sub">We've notified {artist.name} about your interest. They'll reach out soon!</p>

                <div className="contact-revealed-info">
                  <div className="contact-info-item">
                    <span className="contact-info-label">Phone</span>
                    <span className="contact-info-value">+91 98765 43210</span>
                  </div>
                  {artist.instagramHandle && (
                    <div className="contact-info-item">
                      <span className="contact-info-label">Instagram</span>
                      <span className="contact-info-value">@{artist.instagramHandle}</span>
                    </div>
                  )}
                </div>

                <div className="contact-revealed-actions">
                  <a href="tel:+919876543210" className="contact-call-btn">
                    <Phone size={18} /> Call Now
                  </a>
                  <a href="https://wa.me/919876543210" target="_blank" rel="noopener noreferrer" className="contact-whatsapp-btn">
                    <MessageCircle size={18} /> WhatsApp
                  </a>
                </div>
                <button className="contact-close-btn" onClick={closeContact}>Close</button>
              </div>
            )}
          </div>
        </div>
      )}

      <Footer />
    </>
  );
}
