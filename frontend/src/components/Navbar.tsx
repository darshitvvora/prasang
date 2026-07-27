import { useState } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Menu, X, Sparkles } from 'lucide-react';
import './Navbar.css';

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const links = [
    { label: 'Home', to: '/', active: true },
    { label: 'Search', to: '/search' },
    { label: 'Pricing', to: '/pricing' },
  ];

  return (
    <nav className="navbar" id="navbar">
      <div className="container navbar-inner">
        {/* Logo */}
        <Link to="/" className="navbar-logo">
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
          <button type="button" className="navbar-location" aria-label="Change location">
            <MapPin size={16} />
            <span>Mumbai, India</span>
          </button>

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

      {/* Mobile Menu */}
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
        <button type="button" className="navbar-location">
          <MapPin size={16} />
          <span>Mumbai, India</span>
        </button>
        <Link to="/artist/onboarding" className="navbar-cta" onClick={() => setMobileOpen(false)}>
          <Sparkles size={16} />
          List Your Art
        </Link>
      </div>
    </nav>
  );
}
