import { useNavigate } from 'react-router-dom';
import {
  MapPin,
  Star,
  MessageCircle,
  BadgeCheck,
  Crown,
  AtSign,
  PlayCircle,
} from 'lucide-react';
import type { Artist } from '../types/artist';
import { ARTIST_TYPE_LABELS, ARTIST_TYPE_COLORS } from '../types/artist';
import './ArtistCard.css';

interface ArtistCardProps {
  artist: Artist;
}

function formatPrice(amount: number): string {
  if (amount >= 1000) {
    const k = amount / 1000;
    return `₹${k % 1 === 0 ? k : k.toFixed(1)}K`;
  }
  return `₹${amount}`;
}

export default function ArtistCard({ artist }: ArtistCardProps) {
  const navigate = useNavigate();

  function goToProfile() {
    navigate(`/profile/${artist.slug}`);
  }

  return (
    <article
      className="artist-card"
      id={`artist-${artist.slug}`}
      role="link"
      tabIndex={0}
      onClick={goToProfile}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          goToProfile();
        }
      }}
    >
      {/* Image */}
      <div className="artist-card-image-wrapper">
        <img
          src={artist.profileImageUrl}
          alt={`${artist.name} — ${ARTIST_TYPE_LABELS[artist.artistType]}`}
          className="artist-card-image"
          loading="lazy"
        />

        {/* Status indicator */}
        {/* <div
          className={`artist-card-status ${artist.availabilityStatus}`}
          title={
            artist.availabilityStatus === 'available'
              ? 'Available for bookings'
              : artist.availabilityStatus === 'busy'
                ? 'Busy — limited availability'
                : 'Currently unavailable'
          }
        /> */}

        {/* Featured badge */}
        {artist.isFeatured && (
          <div className="artist-card-featured">
            <Crown size={12} />
            Featured
          </div>
        )}
      </div>

      {/* Body */}
      <div className="artist-card-body">
        {/* Name + Rating */}
        <div className="artist-card-name-row">
          <div className="artist-card-name-group">
            <span className="artist-card-name">{artist.name}</span>
            {artist.isVerified && (
              <BadgeCheck className="artist-card-verified" aria-label="Verified artist" />
            )}
          </div>
          <div className="artist-card-rating">
            <Star size={14} fill="currentColor" />
            <span>{artist.averageRating}</span>
            <span className="artist-card-reviews">({artist.totalReviews})</span>
          </div>
        </div>

        {/* Location */}
        <div className="artist-card-location">
          <MapPin size={13} />
          <span>{artist.locationArea}, {artist.locationCity}</span>
        </div>

        {/* Social links */}
        <div className="artist-card-socials">
          {artist.instagramHandle && (
            <a
              href={`https://instagram.com/${artist.instagramHandle}`}
              className="artist-card-social"
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`${artist.name} on Instagram`}
              onClick={(e) => e.stopPropagation()}
            >
              <AtSign size={15} />
            </a>
          )}
          {artist.youtubeChannel && (
            <a
              href={`https://youtube.com/@${artist.youtubeChannel}`}
              className="artist-card-social"
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`${artist.name} on YouTube`}
              onClick={(e) => e.stopPropagation()}
            >
              <PlayCircle size={15} />
            </a>
          )}
        </div>

        {/* Type badge + Price */}
        <div className="artist-card-meta">
          <span
            className="artist-card-type"
            style={{ background: ARTIST_TYPE_COLORS[artist.artistType] }}
          >
            {ARTIST_TYPE_LABELS[artist.artistType]}
          </span>
          <div className="artist-card-price-label">
            <div className="artist-card-price">
              {formatPrice(artist.perEventRateMin)} – {formatPrice(artist.perEventRateMax)}
            </div>
            per event
          </div>
        </div>

        {/* Actions */}
        {/* <div className="artist-card-actions">
          <div className="artist-card-action-icons">
            <button type="button" className="artist-card-icon-btn" aria-label="Send message" onClick={(e) => e.stopPropagation()}>
              <MessageCircle size={18} />
            </button>
            <button type="button" className="artist-card-icon-btn favorite" aria-label="Save to favorites" onClick={(e) => e.stopPropagation()}>
              <Heart size={18} />
            </button>
          </div>
          <button
            type="button"
            className="artist-card-contact-btn"
            id={`contact-${artist.slug}`}
            onClick={(e) => e.stopPropagation()}
          >
            Get Contact Info
          </button>
        </div> */}
      </div>
    </article>
  );
}
