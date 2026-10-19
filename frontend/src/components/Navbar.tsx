import { useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { Menu, X, Sparkles } from 'lucide-react';
import './Navbar.css';
import { useAuth } from '../auth/AuthProvider';
import { homePathFor } from '../auth/paths';
import { useLocations } from '../api/queries';

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { status, user, signOut } = useAuth();
  const locations = useLocations();
  const city = params.get('city') ?? 'Mumbai';

  const links = [
    { label: 'Home', to: '/' },
    { label: 'Search', to: '/search' },
    { label: 'Pricing', to: '/pricing' },
  ];
  const listYourArtTo = user?.role === 'artist' ? '/artist/onboarding' : '/signup?role=artist';
  const close = () => setMobileOpen(false);

  function chooseCity(name: string) {
    close();
    navigate(`/search?city=${encodeURIComponent(name)}`);
  }

  function handleSignOut() {
    close();
    signOut();
    navigate('/');
  }

  const citySelect = (
    <select className="navbar-location-select" value={city} onChange={(e) => chooseCity(e.target.value)} aria-label="Select location">
      {(locations.data?.cities ?? [{ name: city, areas: [] }]).map((c) => (
        <option key={c.name} value={c.name}>{c.name}, India</option>
      ))}
    </select>
  );

  const accountLinks = status === 'signedIn' && user ? (
    <>
      <Link to={homePathFor(user)} className="navbar-signin" onClick={close}>Dashboard</Link>
      <button type="button" className="navbar-signin navbar-signout" onClick={handleSignOut}>Sign out</button>
    </>
  ) : (
    <Link to="/login" className="navbar-signin" onClick={close}>Sign In</Link>
  );

  return (
    <>
      <nav className="navbar" id="navbar">
        <div className="container navbar-inner">
          <Link to="/" className="navbar-logo" onClick={close}>
            <span className="navbar-logo-text">prasang</span>
            <span className="navbar-logo-hindi">प्रसंग</span>
          </Link>

          <div className="navbar-links">
            {links.map((link) => (
              <Link key={link.label} to={link.to} className={`navbar-link${pathname === link.to ? ' active' : ''}`}>
                {link.label}
              </Link>
            ))}
          </div>

          <div className="navbar-right">
            {citySelect}
            {accountLinks}
            <Link to={listYourArtTo} className="navbar-cta">
              <Sparkles size={16} />
              List Your Art
            </Link>
            <button type="button" className="navbar-mobile-toggle" aria-label="Toggle menu" onClick={() => setMobileOpen(!mobileOpen)}>
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
          <Link key={link.label} to={link.to} className={`navbar-link${pathname === link.to ? ' active' : ''}`} onClick={close}>
            {link.label}
          </Link>
        ))}
        <div className="navbar-mobile-divider" />
        {accountLinks}
        {citySelect}
        <Link to={listYourArtTo} className="navbar-cta" onClick={close}>
          <Sparkles size={16} />
          List Your Art
        </Link>
      </div>
    </>
  );
}
