import { Link } from 'react-router-dom';
import { AtSign, PlayCircle, Globe, Briefcase } from 'lucide-react';
import './Footer.css';

export default function Footer() {
  return (
    <footer className="footer" id="footer">
      <div className="container">
        <div className="footer-grid">
          {/* Brand Column */}
          <div className="footer-brand">
            <div className="footer-logo">
              <span className="footer-logo-text">prasang</span>
              <span className="footer-logo-hindi">प्रसंग</span>
            </div>
            <p className="footer-tagline">
              Find artists for every prasang. India&apos;s largest artist discovery platform
              connecting performers with event planners.
            </p>
            <div className="footer-social-links">
              <a href="#" className="footer-social-link" aria-label="Instagram">
                <AtSign size={18} />
              </a>
              <a href="#" className="footer-social-link" aria-label="YouTube">
                <PlayCircle size={18} />
              </a>
              <a href="#" className="footer-social-link" aria-label="Twitter">
                <Globe size={18} />
              </a>
              <a href="#" className="footer-social-link" aria-label="LinkedIn">
                <Briefcase size={18} />
              </a>
            </div>
          </div>

          {/* For Artists */}
          <div>
            <h3 className="footer-column-title">For Artists</h3>
            <nav className="footer-links" aria-label="Artist links">
              <Link to="/artist/onboarding" className="footer-link">List Your Profile</Link>
              <Link to="/pricing" className="footer-link">Pricing Plans</Link>
              <Link to="/artist/dashboard" className="footer-link">Artist Dashboard</Link>
            </nav>
          </div>

          {/* For Event Planners */}
          <div>
            <h3 className="footer-column-title">For Event Planners</h3>
            <nav className="footer-links" aria-label="Event planner links">
              <Link to="/search" className="footer-link">Find Artists</Link>
              <Link to="/search" className="footer-link">Browse by Category</Link>
              <Link to="/search" className="footer-link">Browse by Location</Link>
              <Link to="/about" className="footer-link">How It Works</Link>
            </nav>
          </div>

          {/* Company */}
          <div>
            <h3 className="footer-column-title">Company</h3>
            <nav className="footer-links" aria-label="Company links">
              <Link to="/about" className="footer-link">About Us</Link>
              <Link to="/contact" className="footer-link">Contact</Link>
              <Link to="/privacy-policy" className="footer-link">Privacy Policy</Link>
              <Link to="/terms-of-service" className="footer-link">Terms of Service</Link>
              <Link to="/cookie-policy" className="footer-link">Cookie Policy</Link>
            </nav>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="footer-bottom">
          <p className="footer-copyright">
            © 2026 Prasang. Made with ❤️ in Mumbai
          </p>
          <div className="footer-bottom-links">
            <Link to="/privacy-policy" className="footer-bottom-link">Privacy Policy</Link>
            <Link to="/terms-of-service" className="footer-bottom-link">Terms of Service</Link>
            <Link to="/cookie-policy" className="footer-bottom-link">Cookie Policy</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
