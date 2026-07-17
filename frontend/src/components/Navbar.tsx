import { useState } from 'react';
import { MapPin, Bell, Menu, X, Sparkles } from 'lucide-react';
import './Navbar.css';

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const links = [
    { label: 'Home', href: '#', active: true },
    { label: 'Search', href: '#search' },
    { label: 'For Artists', href: '#artists' },
    { label: 'Pricing', href: '#pricing' },
  ];

  return (
    <nav className="navbar" id="navbar">
      <div className="container navbar-inner">
        {/* Logo */}
        <a href="/" className="navbar-logo">
          <span className="navbar-logo-text">prasang</span>
          <span className="navbar-logo-hindi">प्रसंग</span>
        </a>

        {/* Desktop Links */}
        <div className="navbar-links">
          {links.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className={`navbar-link${link.active ? ' active' : ''}`}
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* Right Section */}
        <div className="navbar-right">
          <button type="button" className="navbar-location" aria-label="Change location">
            <MapPin size={16} />
            <span>Mumbai, India</span>
          </button>

          <button type="button" className="navbar-bell" aria-label="Notifications">
            <Bell size={20} />
          </button>

          <a href="#list" className="navbar-cta">
            <Sparkles size={16} />
            List Your Art
          </a>

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
          <a
            key={link.label}
            href={link.href}
            className={`navbar-link${link.active ? ' active' : ''}`}
            onClick={() => setMobileOpen(false)}
          >
            {link.label}
          </a>
        ))}
        <div className="navbar-mobile-divider" />
        <button type="button" className="navbar-location">
          <MapPin size={16} />
          <span>Mumbai, India</span>
        </button>
        <a href="#list" className="navbar-cta" onClick={() => setMobileOpen(false)}>
          <Sparkles size={16} />
          List Your Art
        </a>
      </div>
    </nav>
  );
}
