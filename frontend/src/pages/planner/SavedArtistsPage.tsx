import { Link } from 'react-router-dom';
import { LayoutDashboard, MessageCircle, Heart, Search, MapPin, Star, BadgeCheck, ChevronRight } from 'lucide-react';
import { mockArtists } from '../../data/mockArtists';
import { SAVED_ARTIST_IDS } from '../../data/mockPlannerActivity';
import { ARTIST_TYPE_LABELS, ARTIST_TYPE_COLORS } from '../../types/artist';
import './PlannerPages.css';

function formatPrice(n: number) {
  return n >= 1000 ? `₹${(n / 1000).toFixed(0)}K` : `₹${n}`;
}

export default function SavedArtistsPage() {
  const savedArtists = mockArtists.filter((a) => SAVED_ARTIST_IDS.includes(a.artistId));

  return (
    <div className="planner-layout">
      <aside className="planner-sidebar">
        <Link to="/" className="planner-sidebar-logo">
          <span>prasang</span>
          <span className="planner-sidebar-logo-hindi">प्रसंग</span>
        </Link>
        <nav className="planner-sidebar-nav">
          <Link to="/planner/dashboard" className="planner-sidebar-link">
            <LayoutDashboard size={18} /> Dashboard
          </Link>
          <Link to="/planner/inquiries" className="planner-sidebar-link">
            <MessageCircle size={18} /> My Inquiries
          </Link>
          <Link to="/planner/saved" className="planner-sidebar-link active">
            <Heart size={18} /> Saved Artists
          </Link>
          <Link to="/search" className="planner-sidebar-link">
            <Search size={18} /> Browse Artists
          </Link>
        </nav>
        <div className="planner-promo-card">
          <div className="planner-promo-title">Looking for more artists?</div>
          <div className="planner-promo-note">Search magicians, DJs, singers and more near you.</div>
          <Link to="/search" className="planner-promo-btn">
            Browse Artists <ChevronRight size={14} />
          </Link>
        </div>
      </aside>

      <main className="planner-main">
        <header className="planner-topbar">
          <div>
            <h1 className="planner-page-title">Saved Artists</h1>
            <p className="planner-page-sub">Artists you've favorited while browsing</p>
          </div>
        </header>

        {savedArtists.length === 0 ? (
          <div className="planner-saved-empty">
            You haven't saved any artists yet.
            <div>
              <Link to="/search" className="planner-saved-browse-cta">
                <Search size={16} /> Browse Artists
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="planner-saved-grid">
              {savedArtists.map((artist) => (
                <Link to={`/profile/${artist.slug}`} key={artist.artistId} className="planner-saved-card">
                  <div className="planner-saved-card-img-wrap">
                    <img src={artist.profileImageUrl} alt={artist.name} className="planner-saved-card-img" />
                    {artist.isVerified && (
                      <span className="planner-saved-card-verified">
                        <BadgeCheck size={16} />
                      </span>
                    )}
                  </div>
                  <div className="planner-saved-card-body">
                    <div className="planner-saved-card-name-row">
                      <span className="planner-saved-card-name">{artist.name}</span>
                      <span className="planner-saved-card-rating">
                        <Star size={13} fill="currentColor" /> {artist.averageRating}
                      </span>
                    </div>
                    <div className="planner-saved-card-location">
                      <MapPin size={12} /> {artist.locationArea}, {artist.locationCity}
                    </div>
                    <div className="planner-saved-card-footer">
                      <span
                        className="planner-saved-card-type"
                        style={{ background: ARTIST_TYPE_COLORS[artist.artistType] }}
                      >
                        {ARTIST_TYPE_LABELS[artist.artistType]}
                      </span>
                      <span className="planner-saved-card-price">
                        {formatPrice(artist.perEventRateMin)}–{formatPrice(artist.perEventRateMax)}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
            <Link to="/search" className="planner-saved-browse-cta">
              <Search size={16} /> Browse more artists
            </Link>
          </>
        )}
      </main>
    </div>
  );
}
