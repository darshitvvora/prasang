import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, MapPin, Star, BadgeCheck, Crown, AtSign,
  PlayCircle, Share2, Phone, MessageCircle,
  ChevronRight, CheckCircle, Plane, Globe, CalendarDays,
} from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import ContactModal from '../components/ContactModal';
import QueryState from '../components/QueryState';
import FullPageSpinner from '../components/FullPageSpinner';
import NotFoundPage from './NotFoundPage';
import { EMBED_ALLOW, EMBED_SANDBOX, mediaIsEmbed } from '../components/embed';
import { ApiError } from '../api/client';
import { useArtist, useArtistReviews, useSimilarArtists } from '../api/queries';
import { formatPrice, imageOr } from '../api/format';
import type { ArtistDetail } from '../api/types';
import { ARTIST_TYPE_LABELS, ARTIST_TYPE_COLORS, EVENT_TYPE_LABELS } from '../types/artist';
import './ArtistProfilePage.css';

const WIDGET_LABELS = { instagram: 'Instagram', youtube: 'YouTube', facebook: 'Facebook' } as const;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const formatMonth = (ym: string) => { const [y, m] = ym.split('-').map(Number); return `${MONTHS[m - 1]} ${y}`; };

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
  const { slug = '' } = useParams<{ slug: string }>();
  const artist = useArtist(slug);
  if (artist.isPending) return <><Navbar /><FullPageSpinner /></>;
  if (artist.error instanceof ApiError && artist.error.status === 404) {
    return <NotFoundPage title="Artist not found" message="This profile link doesn't match any artist on Prasang." />;
  }
  return (
    <QueryState query={artist} loading={<FullPageSpinner />}>
      {(data) => <ArtistProfile key={data.slug} artist={data} />}
    </QueryState>
  );
}

function ArtistProfile({ artist }: { artist: ArtistDetail }) {
  const reviews = useArtistReviews(artist.slug);
  const similarQuery = useSimilarArtists(artist.slug);
  const similar = (similarQuery.data?.items ?? []).filter((a) => a.artistId !== artist.artistId).slice(0, 3);
  const [contactOpen, setContactOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'media' | 'reviews'>('media');
  const media = artist.media.length > 0
    ? artist.media
    : [{ id: 'profile', kind: 'image' as const, url: imageOr(artist.profileImageUrl), thumbnailUrl: null, caption: null, displayOrder: 0 }];
  const openContact = () => setContactOpen(true);

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
                  src={imageOr(artist.profileImageUrl)}
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
                </div>

                {/* Performance Details */}
                <div className="profile-performance-details">
                  {artist.eventTypesSupported.length > 0 && (
                    <div className="profile-detail-row">
                      <span className="profile-detail-row-label">
                        <CalendarDays size={14} /> Events :
                      </span>
                      <span className="profile-detail-text">
                        &nbsp; {artist.eventTypesSupported.map((et) => EVENT_TYPE_LABELS[et]).join(', ')}
                      </span>
                    </div>
                  )}
                  {artist.languagesSpoken.length > 0 && (
                    <div className="profile-detail-row">
                      <span className="profile-detail-row-label">
                        <Globe size={14} /> Languages :
                      </span>
                      <span className="profile-detail-text">
                        &nbsp; {artist.languagesSpoken.join(', ')}
                      </span>
                    </div>
                  )}
                  <div className="profile-detail-row">
                    <span className="profile-detail-row-label">
                      <Plane size={14} /> Travel :
                    </span>
                    <span className="profile-detail-text">
                      &nbsp; {artist.readyToTravel ? 'Yes' : 'No'}
                    </span>
                  </div>
                </div>

                {/* <div className="profile-stat">
                    <span className={`profile-avail-dot ${artist.availabilityStatus}`} />
                    <span className="profile-stat-lbl">
                      {artist.availabilityStatus === 'available' ? 'Available' : artist.availabilityStatus === 'busy' ? 'Busy' : 'Unavailable'}
                    </span>
                  </div> */}
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
                  {tab === 'reviews' && <span className="profile-tab-badge">{reviews.data?.total ?? artist.totalReviews}</span>}
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
                  {media.map((m) => (
                    <div key={m.id} className="profile-media-item">
                      {m.kind === 'image' ? (
                        <img src={m.url} alt={m.caption ?? `${artist.name} performance`} className="profile-media-img" loading="lazy" />
                      ) : mediaIsEmbed(m) ? (
                        <iframe src={m.embedUrl ?? undefined} title={m.caption ?? `${artist.name} on ${m.kind}`} className="profile-media-iframe"
                          sandbox={EMBED_SANDBOX} allow={EMBED_ALLOW} allowFullScreen loading="lazy" />
                      ) : m.kind === 'video' ? (
                        <video src={m.url} className="profile-media-img" controls preload="metadata" />
                      ) : (
                        <a href={m.url} target="_blank" rel="noopener noreferrer" className="profile-media-embed">
                          <img src={imageOr(m.thumbnailUrl ?? artist.profileImageUrl)} alt={m.caption ?? `${artist.name} video`} className="profile-media-img" loading="lazy" />
                          <PlayCircle size={40} className="profile-media-play" />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Social widgets: Instagram profile, YouTube channel, Facebook page */}
            {activeTab === 'media' && artist.socialWidgets.length > 0 && (
              <section className="profile-section profile-widgets">
                <h2 className="profile-section-title">On social media</h2>
                <div className="profile-widgets-grid">
                  {artist.socialWidgets.map((w) => (
                    <div key={w.platform} className={`profile-widget ${w.platform}`}>
                      <a href={w.profileUrl} target="_blank" rel="noopener noreferrer" className="profile-widget-link">
                        {WIDGET_LABELS[w.platform]} ↗
                      </a>
                      {w.embedUrl && (
                        <iframe src={w.embedUrl} title={`${artist.name} on ${WIDGET_LABELS[w.platform]}`} className="profile-widget-frame"
                          sandbox={EMBED_SANDBOX} allow={EMBED_ALLOW} allowFullScreen loading="lazy" />
                      )}
                    </div>
                  ))}
                </div>
              </section>
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

                <QueryState
                  query={reviews}
                  isEmpty={(d) => d.items.length === 0}
                  empty={<p className="review-text">No reviews yet. Be the first to book {artist.name}!</p>}
                >
                  {(data) => (
                    <div className="reviews-list">
                      {data.items.map((r) => (
                        <div key={r.id} className="review-card">
                          <div className="review-card-header">
                            <div className="review-avatar">{r.reviewerName[0]}</div>
                            <div>
                              <div className="review-name">{r.reviewerName}</div>
                              <div className="review-meta">{EVENT_TYPE_LABELS[r.eventType]} · {formatMonth(r.eventMonth)}</div>
                            </div>
                            <Stars rating={r.rating} />
                          </div>
                          <p className="review-text">{r.text}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </QueryState>
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
                      <img src={imageOr(a.profileImageUrl)} alt={a.name} className="similar-card-img" loading="lazy" />
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
                    {formatPrice(artist.perEventRateMin)} – {formatPrice(artist.perEventRateMax)}
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

              <button type="button" className="booking-whatsapp-btn" onClick={openContact}>
                <MessageCircle size={18} /> WhatsApp
              </button>

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

      {contactOpen && <ContactModal artist={artist} source="profile" onClose={() => setContactOpen(false)} />}

      <Footer />
    </>
  );
}
