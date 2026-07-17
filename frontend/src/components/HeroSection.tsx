import { Search, SlidersHorizontal } from 'lucide-react';
import './HeroSection.css';

export default function HeroSection() {
  return (
    <section className="hero" id="hero">
      {/* Background decorations */}
      <div className="hero-bg-glow hero-bg-glow--accent" aria-hidden="true" />
      <div className="hero-bg-glow hero-bg-glow--purple" aria-hidden="true" />

      <div className="container hero-inner">
        {/* Left Content */}
        <div className="hero-content">
          <h1 className="hero-heading">
            Find artists
            <br />
            for every
            <br />
            <span className="accent">prasang</span>
          </h1>

          {/* Avatar stack */}
          <div className="hero-avatars" aria-hidden="true">
            <img src="/artists/singer.png" alt="" className="hero-avatar" />
            <img src="/artists/dj.png" alt="" className="hero-avatar" />
            <img src="/artists/comedian.png" alt="" className="hero-avatar" />
            <img src="/artists/band.png" alt="" className="hero-avatar" />
          </div>

          {/* Search bar */}
          <div className="hero-search">
            <input
              type="text"
              className="hero-search-input"
              placeholder="Search magicians, DJs, singers..."
              id="hero-search-input"
              aria-label="Search for artists"
            />
            <button type="button" className="hero-search-filter" aria-label="Open filters">
              <SlidersHorizontal size={18} />
            </button>
            <button type="button" className="hero-search-btn" aria-label="Search">
              <Search size={18} />
            </button>
          </div>

          {/* Stats */}
          <div className="hero-stats">
            <div className="hero-stat">
              <div className="hero-stat-value">12,500+</div>
              <div className="hero-stat-label">Artists Listed</div>
            </div>
            <div className="hero-stat">
              <div className="hero-stat-value">8,200+</div>
              <div className="hero-stat-label">Events Booked</div>
            </div>
            <div className="hero-stat">
              <div className="hero-stat-value">50+</div>
              <div className="hero-stat-label">Cities</div>
            </div>
          </div>
        </div>

        {/* Right Card */}
        <div className="hero-card" role="presentation">
          <div className="hero-card-text">
            See how
            <br />
            it&apos;s done
          </div>
        </div>
      </div>
    </section>
  );
}
