import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Search, SlidersHorizontal, X, ChevronDown, MapPin,
  Star, Crown, BadgeCheck, AtSign,
  PlayCircle, ArrowLeft, LayoutGrid, List, Plane,
} from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import QueryState from '../components/QueryState';
import { useLocations, useSearchArtists } from '../api/queries';
import { formatPrice, imageOr } from '../api/format';
import type { SearchParams, SortOption } from '../api/types';
import type { ArtistType, EventType } from '../types/artist';
import { ARTIST_TYPE_LABELS, ARTIST_TYPE_COLORS, EVENT_TYPE_LABELS, LANGUAGES } from '../types/artist';
import { MAX_PRICE, activeFilterCount, mergeSearch, parseSearch, toSearchString } from './search/searchUrl';
import './SearchPage.css';

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'relevance', label: 'Most Relevant' },
  { value: 'rating', label: 'Highest Rated' },
  { value: 'price_low', label: 'Price: Low to High' },
  { value: 'price_high', label: 'Price: High to Low' },
  { value: 'popular', label: 'Most Popular' },
];

const PAGE_SIZE = 20;

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = parseSearch(searchParams);
  const locations = useLocations();
  const cities = locations.data?.cities ?? [];
  const results = useSearchArtists({ ...params, size: PAGE_SIZE });

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [filtersOpen, setFiltersOpen] = useState(false);

  // The text box updates the URL 300 ms after typing stops.
  const [query, setQuery] = useState(params.q ?? '');
  useEffect(() => {
    if ((params.q ?? '') === query.trim()) return;
    const t = setTimeout(() => update({ q: query.trim() || undefined }), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  /** Merge changes into the URL; any filter change goes back to page 1. */
  function update(changes: Partial<SearchParams>) {
    // Functional update: a debounced call must merge onto the newest URL, not a stale render's.
    setSearchParams((latest) => mergeSearch(latest, changes), { replace: true });
  }

  const city = params.city ?? 'Mumbai';
  const area = params.area ?? '';
  const artistType = params.artistType ?? '';
  const eventTypeFilter = params.eventType ?? '';
  const languageFilter = params.language ?? '';
  const travelOnly = params.readyToTravel ?? false;
  const minPrice = params.minPrice ?? 0;
  const maxPrice = params.maxPrice ?? MAX_PRICE;
  const minRating = params.minRating ?? 0;
  const verifiedOnly = params.verifiedOnly ?? false;
  const featuredOnly = params.featuredOnly ?? false;
  const sortBy = params.sort ?? 'relevance';
  const page = params.page ?? 1;

  const setCity = (v: string) => update({ city: v, area: undefined });
  const setArea = (v: string) => update({ area: v || undefined });
  const setArtistType = (v: ArtistType | '') => update({ artistType: v || undefined });
  const setEventTypeFilter = (v: EventType | '') => update({ eventType: v || undefined });
  const setLanguageFilter = (v: string) => update({ language: v || undefined });
  const setTravelOnly = (v: boolean) => update({ readyToTravel: v || undefined });
  const setMaxPrice = (v: number) => update({ maxPrice: v >= MAX_PRICE ? undefined : v });
  const setMinRating = (v: number) => update({ minRating: v || undefined });
  const setVerifiedOnly = (v: boolean) => update({ verifiedOnly: v || undefined });
  const setFeaturedOnly = (v: boolean) => update({ featuredOnly: v || undefined });
  const setSortBy = (v: SortOption) => update({ sort: v });
  const goToPage = (n: number) => {
    setSearchParams(toSearchString({ ...params, page: n }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  function clearFilters() {
    setSearchParams(toSearchString({ q: params.q, city: params.city, sort: params.sort }), { replace: true });
  }

  const hasActiveFilters = activeFilterCount(params) > 0;
  const areas = cities.find((c) => c.name === city)?.areas ?? [];
  const total = results.data?.total ?? 0;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

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
                onChange={(e) => setCity(e.target.value)}
                className="search-city-select"
                aria-label="Select city"
              >
                {(cities.length ? cities.map((c) => c.name) : [city]).map((c) => <option key={c}>{c}</option>)}
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
          {/* Backdrop for mobile filter drawer */}
          {filtersOpen && (
            <div
              className="search-sidebar-backdrop"
              onClick={() => setFiltersOpen(false)}
              aria-hidden="true"
            />
          )}

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
                {areas.map((a) => <option key={a}>{a}</option>)}
              </select>
            </div>

            {/* Event Type Filter */}
            <div className="sidebar-group">
              <h3 className="sidebar-group-title">Event Type</h3>
              <div className="sidebar-event-chips">
                {(Object.keys(EVENT_TYPE_LABELS) as EventType[]).map((et) => (
                  <button
                    key={et}
                    className={`sidebar-event-chip${eventTypeFilter === et ? ' active' : ''}`}
                    onClick={() => setEventTypeFilter(eventTypeFilter === et ? '' : et)}
                  >
                    {EVENT_TYPE_LABELS[et]}
                  </button>
                ))}
              </div>
            </div>

            {/* Language Filter */}
            <div className="sidebar-group">
              <h3 className="sidebar-group-title">Language</h3>
              <select
                value={languageFilter}
                onChange={(e) => setLanguageFilter(e.target.value)}
                className="sidebar-select"
                aria-label="Filter by language"
              >
                <option value="">All Languages</option>
                {LANGUAGES.map((lang) => <option key={lang} value={lang}>{lang}</option>)}
              </select>
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
                  checked={travelOnly}
                  onChange={(e) => setTravelOnly(e.target.checked)}
                />
                <span className="sidebar-toggle-track" />
                <span className="sidebar-toggle-label">
                  <Plane size={15} /> Ready to Travel
                </span>
              </label>
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
                <strong>{total}</strong> artists found
                {artistType && ` · ${ARTIST_TYPE_LABELS[artistType]}`}
                {area && ` · ${area}`}
                {` · ${city}`}
              </p>
              <div className="results-controls">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
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
            <QueryState
              query={results}
              isEmpty={(d) => d.items.length === 0}
              empty={
                <div className="results-empty">
                  <p className="results-empty-title">No artists found</p>
                  <p className="results-empty-sub">Try adjusting your filters or search query</p>
                  <button className="results-empty-clear" onClick={clearFilters}>Clear Filters</button>
                </div>
              }
            >
              {(data) => (
                <>
                  <div className={`results-grid${viewMode === 'list' ? ' list-view' : ''}`}>
                    {data.items.map((artist) => (
                      <article key={artist.artistId} className="result-card">
                        <div className="result-card-image-wrap">
                          <img
                            src={imageOr(artist.profileImageUrl)}
                            alt={artist.name}
                            className="result-card-image"
                            loading="lazy"
                          />
                          {/* <div className={`result-card-status ${artist.availabilityStatus}`} />
                          {artist.isFeatured && (
                            <div className="result-card-featured">
                              <Crown size={11} /> Featured
                            </div>
                          )} */}

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
                              {/* <button className="result-card-msg-btn" aria-label="Message">
                                <MessageCircle size={16} />
                              </button> */}
                              <Link to={`/profile/${artist.slug}`} className="result-card-view-btn">
                                View Profile
                              </Link>
                              {/* <button className="result-card-contact-btn">
                                Get Contact
                              </button> */}
                            </div>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                  {lastPage > 1 && (
                    <nav className="results-pagination" aria-label="Pagination">
                      <button className="results-page-btn" disabled={page <= 1} onClick={() => goToPage(page - 1)}>Previous</button>
                      <span className="results-page-info">Page {page} of {lastPage}</span>
                      <button className="results-page-btn" disabled={page >= lastPage} onClick={() => goToPage(page + 1)}>Next</button>
                    </nav>
                  )}
                </>
              )}
            </QueryState>
          </main>
        </div>
      </div>
      <Footer />
    </>
  );
}
