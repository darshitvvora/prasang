import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Menu, X, Sparkles } from 'lucide-react';
import './Navbar.css';
import indianCities from '../data/indian_cities.json';

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [city, setCity] = useState('Mumbai, India');
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(() => {
        // Placeholder: could reverse geocode to city name; fallback to default.
      });
    }
  }, []);
  const links = [
    { label: 'Home', to: '/', active: true },
    { label: 'Search', to: '/search' },
    { label: 'Pricing', to: '/pricing' },
  ];

  return (
    <>
      <nav className="navbar" id="navbar">
        <div className="container navbar-inner">
          {/* Logo */}
          <Link to="/" className="navbar-logo" onClick={() => setMobileOpen(false)}>
            <span className="navbar-logo-text">prasang</span>
            <span className="navbar-logo-hindi">प्रसंग</span>
          </Link>

          {/* Desktop Links */}
          <div className="navbar-links">
            {links.map((link) => (
              <Link
                key={link.label}
                to={link.to}
                className={`navbar-link${link.active ? ' active' : ''}`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Right Section */}
          <div className="navbar-right">
            <select className="navbar-location-select" value={city} onChange={(e) => setCity(e.target.value)} aria-label="Select location">
              {indianCities.map((c) => (
                <option key={c.name} value={`${c.name}, India`}>{c.name}, India</option>
              ))}
            </select>

            <Link to="/login" className="navbar-signin">
              Sign In
            </Link>

            <Link to="/artist/onboarding" className="navbar-cta">
              <Sparkles size={16} />
              List Your Art
            </Link>

            {/* Mobile toggle */}
            <button
              type="button"
              className="navbar-mobile-toggle"
              aria-label="Toggle menu"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              {mobileOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile Menu — rendered outside <nav> so its position:fixed isn't
          confined by the navbar's backdrop-filter (which otherwise becomes
          the containing block for fixed descendants and collapses this to
          the navbar's own height). */}
      <div className={`navbar-mobile-menu${mobileOpen ? ' open' : ''}`}>
        {links.map((link) => (
          <Link
            key={link.label}
            to={link.to}
            className={`navbar-link${link.active ? ' active' : ''}`}
            onClick={() => setMobileOpen(false)}
          >
            {link.label}
          </Link>
        ))}
        <div className="navbar-mobile-divider" />
        <Link to="/login" className="navbar-link" onClick={() => setMobileOpen(false)}>
          Sign In
        </Link>
            <select className="navbar-location-select" value={city} onChange={(e) => setCity(e.target.value)} aria-label="Select location">
              {indianCities.map((c) => (
                <option key={c.name} value={`${c.name}, India`}>{c.name}, India</option>
              ))}
            </select>
        <Link to="/artist/onboarding" className="navbar-cta" onClick={() => setMobileOpen(false)}>
          <Sparkles size={16} />
          List Your Art
        </Link>
      </div>
    </>
  );
}
