import { Link } from 'react-router-dom';
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

          {/* Stats */}
          {/* <div className="hero-stats">
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
          </div> */}
        </div>

        {/* Right Card */}
        <Link to="/about" className="hero-card" aria-label="See how Prasang works">
          <div className="hero-card-text">
            See how
            <br />
            it&apos;s done
          </div>
        </Link>
      </div>
    </section>
  );
}
