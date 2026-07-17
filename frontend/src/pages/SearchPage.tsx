import { useState, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Search, SlidersHorizontal, X, ChevronDown, MapPin,
  Star, Crown, BadgeCheck, Heart, MessageCircle, AtSign,
  PlayCircle, ArrowLeft, LayoutGrid, List,
} from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { mockArtists } from '../data/mockArtists';
import type { ArtistType } from '../types/artist';
import { ARTIST_TYPE_LABELS, ARTIST_TYPE_COLORS } from '../types/artist';
import './SearchPage.css';

const CITIES = ['Mumbai', 'Pune', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai'];
const AREAS: Record<string, string[]> = {
  Mumbai: ['Bandra West', 'Andheri West', 'Juhu', 'Powai', 'Lower Parel', 'Dadar', 'Goregaon', 'Malad'],
  Pune: ['Koregaon Park', 'Viman Nagar', 'Hinjewadi', 'Wakad'],
  Delhi: ['South Delhi', 'Connaught Place', 'Hauz Khas', 'Dwarka'],
  Bangalore: ['Indiranagar', 'Koramangala', 'Whitefield', 'HSR Layout'],
  Hyderabad: ['Banjara Hills', 'Jubilee Hills', 'Gachibowli'],
  Chennai: ['T. Nagar', 'Adyar', 'Anna Nagar'],
};

const EVENT_TYPES = ['Birthday', 'Wedding', 'Pre-Wedding', 'Anniversary', 'Corporate', 'House Party'];

const SORT_OPTIONS = [
  { value: 'relevance', label: 'Most Relevant' },
  { value: 'rating', label: 'Highest Rated' },
  { value: 'price_low', label: 'Price: Low to High' },
  { value: 'price_high', label: 'Price: High to Low' },
  { value: 'popular', label: 'Most Popular' },
];

function formatPrice(n: number) {
  return n >= 1000 ? `₹${(n / 1000).toFixed(0)}K` : `₹${n}`;
}

export default function SearchPage() {
  const [searchParams] = useSearchParams();
  const initialCity = searchParams.get('city') || 'Mumbai';

  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [city, setCity] = useState(initialCity);
  const [area, setArea] = useState('');
  const [artistType, setArtistType] = useState<ArtistType | ''>('');
  const [minPrice, setMinPrice] = useState(0);
  const [maxPrice, setMaxPrice] = useState(100000);
  const [minRating, setMinRating] = useState(0);
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [featuredOnly, setFeaturedOnly] = useState(false);
  const [sortBy, setSortBy] = useState('relevance');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());

  const results = useMemo(() => {
    let list = [...mockArtists];
    if (query) {
      const q = query.toLowerCase();
      list = list.filter(
        (a) =>
          a.name.toLowerCase().includes(q) ||
          a.bio.toLowerCase().includes(q) ||
          ARTIST_TYPE_LABELS[a.artistType].toLowerCase().includes(q),
      );
    }
    if (artistType) list = list.filter((a) => a.artistType === artistType);
    if (area) list = list.filter((a) => a.locationArea === area);
    if (verifiedOnly) list = list.filter((a) => a.isVerified);
    if (featuredOnly) list = list.filter((a) => a.isFeatured);
    if (minRating > 0) list = list.filter((a) => a.averageRating >= minRating);
    list = list.filter(
      (a) => a.perEventRateMin <= maxPrice && a.perEventRateMax >= minPrice,
    );
    if (sortBy === 'rating') list.sort((a, b) => b.averageRating - a.averageRating);
    else if (sortBy === 'price_low') list.sort((a, b) => a.perEventRateMin - b.perEventRateMin);
    else if (sortBy === 'price_high') list.sort((a, b) => b.perEventRateMax - a.perEventRateMax);
    else if (sortBy === 'popular') list.sort((a, b) => b.totalReviews - a.totalReviews);
    else {
      // relevance: featured first, then boost score proxy (premium > pro > basic > free)
      const tierOrder = { premium: 4, pro: 3, basic: 2, free: 1 };
      list.sort((a, b) => {
        if (a.isFeatured !== b.isFeatured) return a.isFeatured ? -1 : 1;
        return (tierOrder[b.subscriptionTier] || 0) - (tierOrder[a.subscriptionTier] || 0);
      });
    }
    return list;
  }, [query, artistType, area, verifiedOnly, featuredOnly, minRating, minPrice, maxPrice, sortBy]);

  function toggleFavorite(id: string) {
    setFavorites((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function clearFilters() {
    setArtistType('');
    setArea('');
    setMinPrice(0);
    setMaxPrice(100000);
    setMinRating(0);
    setVerifiedOnly(false);
    setFeaturedOnly(false);
  }

  const hasActiveFilters =
    artistType || area || minPrice > 0 || maxPrice < 100000 || minRating > 0 || verifiedOnly || featuredOnly;

  return (
    <>
      <Navbar />
      <div className="search-page">
        {/* Top Search Bar */}
        <div className="search-topbar">
          <div className="container search-topbar-inner">
            <Link to="/" className="search-back-btn" aria-label="Back to home">
              <ArrowLeft size={18} />
            </Link>
            <div className="search-input-wrap">
              <Search size={18} className="search-input-icon" />
              <input
                type="text"
                className="search-input"
                placeholder="Search magicians, DJs, singers, bands..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Search artists"
              />
              {query && (
                <button className="search-input-clear" onClick={() => setQuery('')} aria-label="Clear search">
                  <X size={16} />
                </button>
              )}
            </div>
            <div className="search-city-select-wrap">
              <MapPin size={16} />
              <select
                value={city}
                onChange={(e) => { setCity(e.target.value); setArea(''); }}
                className="search-city-select"
                aria-label="Select city"
              >
                {CITIES.map((c) => <option key={c}>{c}</option>)}
              </select>
              <ChevronDown size={14} />
            </div>
            <button
              className={`search-filter-toggle${hasActiveFilters ? ' has-filters' : ''}`}
              onClick={() => setFiltersOpen(!filtersOpen)}
              aria-label="Toggle filters"
              aria-expanded={filtersOpen}
            >
              <SlidersHorizontal size={18} />
              Filters
              {hasActiveFilters && <span className="filter-badge" />}
            </button>
          </div>
        </div>

        <div className="container search-body">
          {/* Sidebar */}
          <aside className={`search-sidebar${filtersOpen ? ' open' : ''}`} aria-label="Search filters">
            <div className="sidebar-header">
              <h2 className="sidebar-title">Filters</h2>
              <div className="sidebar-header-actions">
                {hasActiveFilters && (
                  <button className="sidebar-clear-btn" onClick={clearFilters}>Clear all</button>
                )}
                <button className="sidebar-close-btn" onClick={() => setFiltersOpen(false)} aria-label="Close filters">
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* Artist Type */}
            <div className="sidebar-group">
              <h3 className="sidebar-group-title">Artist Type</h3>
              <div className="sidebar-type-grid">
                {(Object.keys(ARTIST_TYPE_LABELS) as ArtistType[]).map((type) => (
                  <button
                    key={type}
                    className={`sidebar-type-btn${artistType === type ? ' active' : ''}`}
                    onClick={() => setArtistType(artistType === type ? '' : type)}
                    style={artistType === type ? { background: ARTIST_TYPE_COLORS[type] } : {}}
                  >
                    {ARTIST_TYPE_LABELS[type]}
                  </button>
                ))}
              </div>
            </div>

            {/* Location Area */}
            <div className="sidebar-group">
              <h3 className="sidebar-group-title">Area in {city}</h3>
              <select
                value={area}
                onChange={(e) => setArea(e.target.value)}
                className="sidebar-select"
                aria-label="Select area"
              >
                <option value="">All Areas</option>
                {(AREAS[city] || []).map((a) => <option key={a}>{a}</option>)}
              </select>
            </div>

            {/* Event Type (informational, no filter logic needed yet) */}
            <div className="sidebar-group">
              <h3 className="sidebar-group-title">Event Type</h3>
              <div className="sidebar-event-chips">
                {EVENT_TYPES.map((e) => (
                  <span key={e} className="sidebar-event-chip">{e}</span>
                ))}
              </div>
            </div>

            {/* Budget Range */}
            <div className="sidebar-group">
              <h3 className="sidebar-group-title">
                Budget Range
                <span className="sidebar-price-display">
                  {formatPrice(minPrice)} – {maxPrice >= 100000 ? '₹1L+' : formatPrice(maxPrice)}
                </span>
              </h3>
              <div className="sidebar-range-wrap">
                <input
                  type="range" min={0} max={100000} step={5000}
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(Number(e.target.value))}
                  className="sidebar-range"
                  aria-label="Maximum budget"
                />
              </div>
              <div className="sidebar-range-labels">
                <span>₹0</span><span>₹1L+</span>
              </div>
            </div>

            {/* Rating */}
            <div className="sidebar-group">
              <h3 className="sidebar-group-title">Minimum Rating</h3>
              <div className="sidebar-rating-btns">
                {[0, 3, 4, 4.5].map((r) => (
                  <button
                    key={r}
                    className={`sidebar-rating-btn${minRating === r ? ' active' : ''}`}
                    onClick={() => setMinRating(r)}
                  >
                    {r === 0 ? 'Any' : `${r}+ ★`}
                  </button>
                ))}
              </div>
            </div>

            {/* Toggles */}
            <div className="sidebar-group">
              <label className="sidebar-toggle">
                <input
                  type="checkbox"
                  checked={verifiedOnly}
                  onChange={(e) => setVerifiedOnly(e.target.checked)}
                />
                <span className="sidebar-toggle-track" />
                <span className="sidebar-toggle-label">
                  <BadgeCheck size={15} /> Verified Artists Only
                </span>
              </label>
              <label className="sidebar-toggle">
                <input
                  type="checkbox"
                  checked={featuredOnly}
                  onChange={(e) => setFeaturedOnly(e.target.checked)}
                />
                <span className="sidebar-toggle-track" />
                <span className="sidebar-toggle-label">
                  <Crown size={15} /> Featured Only
                </span>
              </label>
            </div>
          </aside>

          {/* Main Results */}
          <main className="search-results" aria-label="Search results">
            {/* Results header */}
            <div className="results-header">
              <p className="results-count">
                <strong>{results.length}</strong> artists found
                {artistType && ` · ${ARTIST_TYPE_LABELS[artistType]}`}
                {area && ` · ${area}`}
                {` · ${city}`}
              </p>
              <div className="results-controls">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="results-sort-select"
                  aria-label="Sort results"
                >
                  {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <div className="results-view-toggle" role="group" aria-label="View mode">
                  <button
                    className={`view-btn${viewMode === 'grid' ? ' active' : ''}`}
                    onClick={() => setViewMode('grid')}
                    aria-label="Grid view"
                    aria-pressed={viewMode === 'grid'}
                  >
                    <LayoutGrid size={16} />
                  </button>
                  <button
                    className={`view-btn${viewMode === 'list' ? ' active' : ''}`}
                    onClick={() => setViewMode('list')}
                    aria-label="List view"
                    aria-pressed={viewMode === 'list'}
                  >
                    <List size={16} />
                  </button>
                </div>
              </div>
            </div>

            {/* Results grid/list */}
            {results.length === 0 ? (
              <div className="results-empty">
                <p className="results-empty-title">No artists found</p>
                <p className="results-empty-sub">Try adjusting your filters or search query</p>
                <button className="results-empty-clear" onClick={clearFilters}>Clear Filters</button>
              </div>
            ) : (
              <div className={`results-grid${viewMode === 'list' ? ' list-view' : ''}`}>
                {results.map((artist) => (
                  <article key={artist.artistId} className="result-card">
                    <div className="result-card-image-wrap">
                      <img
                        src={artist.profileImageUrl}
                        alt={artist.name}
                        className="result-card-image"
                        loading="lazy"
                      />
                      <div className={`result-card-status ${artist.availabilityStatus}`} />
                      {artist.isFeatured && (
                        <div className="result-card-featured">
                          <Crown size={11} /> Featured
                        </div>
                      )}
                      <button
                        className={`result-card-fav${favorites.has(artist.artistId) ? ' active' : ''}`}
                        onClick={() => toggleFavorite(artist.artistId)}
                        aria-label={`${favorites.has(artist.artistId) ? 'Remove from' : 'Add to'} favorites`}
                      >
                        <Heart size={16} fill={favorites.has(artist.artistId) ? 'currentColor' : 'none'} />
                      </button>
                    </div>

                    <div className="result-card-body">
                      <div className="result-card-top">
                        <div>
                          <div className="result-card-name-row">
                            <span className="result-card-name">{artist.name}</span>
                            {artist.isVerified && (
                              <BadgeCheck size={16} className="result-card-verified" aria-label="Verified" />
                            )}
                          </div>
                          <div className="result-card-location">
                            <MapPin size={12} />
                            {artist.locationArea}, {artist.locationCity}
                          </div>
                        </div>
                        <div className="result-card-rating">
                          <Star size={13} fill="currentColor" />
                          <span>{artist.averageRating}</span>
                          <span className="result-card-review-count">({artist.totalReviews})</span>
                        </div>
                      </div>

                      <p className="result-card-bio">{artist.bio}</p>

                      <div className="result-card-socials">
                        {artist.instagramHandle && (
                          <a href={`https://instagram.com/${artist.instagramHandle}`} target="_blank" rel="noopener noreferrer" className="result-card-social" aria-label="Instagram">
                            <AtSign size={14} />
                          </a>
                        )}
                        {artist.youtubeChannel && (
                          <a href={`https://youtube.com/@${artist.youtubeChannel}`} target="_blank" rel="noopener noreferrer" className="result-card-social" aria-label="YouTube">
                            <PlayCircle size={14} />
                          </a>
                        )}
                        <span
                          className="result-card-type"
                          style={{ background: ARTIST_TYPE_COLORS[artist.artistType] }}
                        >
                          {ARTIST_TYPE_LABELS[artist.artistType]}
                        </span>
                      </div>

                      <div className="result-card-footer">
                        <div className="result-card-price-block">
                          <div className="result-card-price">
                            {formatPrice(artist.perEventRateMin)} – {formatPrice(artist.perEventRateMax)}
                          </div>
                          <div className="result-card-price-label">per event</div>
                        </div>
                        <div className="result-card-actions">
                          <button className="result-card-msg-btn" aria-label="Message">
                            <MessageCircle size={16} />
                          </button>
                          <Link to={`/profile/${artist.slug}`} className="result-card-view-btn">
                            View Profile
                          </Link>
                          <button className="result-card-contact-btn">
                            Get Contact
                          </button>
                        </div>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </main>
        </div>
      </div>
      <Footer />
    </>
  );
}
