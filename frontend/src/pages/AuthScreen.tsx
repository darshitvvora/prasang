// Shared sign-in / sign-up screen. Login and Signup differ only in copy and in
// whether Google sign-in creates a new account. After Google, users without a
// Prasang profile finish a one-step profile (name + role), then land on their home.
import { useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { Phone } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import { homePathFor } from '../auth/paths';
import { InlineError } from '../components/QueryState';
import './AuthPages.css';

type Role = 'artist' | 'planner';
type Mode = 'login' | 'signup';

const COPY: Record<Mode, { title: string; subtitle: string; google: string; busy: string; note: string; switchText: string; switchLink: string; switchTo: string }> = {
  login: { title: 'Welcome back', subtitle: 'Sign in to your Prasang account', google: 'Continue with Google', busy: 'Signing in...',
    note: '90%+ of artists use Google sign-in. Fast, secure, and free.', switchText: 'New to Prasang?', switchLink: 'Create an account', switchTo: '/signup' },
  signup: { title: 'Create account', subtitle: "Join India's largest artist discovery platform", google: 'Continue with Google', busy: 'Creating account...',
    note: 'Free to sign up. No credit card required.', switchText: 'Already have an account?', switchLink: 'Sign in', switchTo: '/login' },
};

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
      <path fill="none" d="M0 0h48v48H0z"/>
    </svg>
  );
}

export default function AuthScreen({ mode }: { mode: Mode }) {
  const copy = COPY[mode];
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get('next');
  const { status, user, signInWithGoogle, completeProfile } = useAuth();

  const initialRole = params.get('role');
  const [role, setRole] = useState<Role | null>(initialRole === 'artist' || initialRole === 'planner' ? initialRole : null);
  const [tab, setTab] = useState<'google' | 'otp'>('google');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');

  if (status === 'signedIn' && user) return <Navigate to={next ?? homePathFor(user)} replace />;
  const profileStep = status === 'needsProfile';

  async function handleGoogle() {
    if (!role) return;
    setLoading(true);
    setError(null);
    try {
      const result = await signInWithGoogle(role, { newAccount: mode === 'signup' });
      if (result.status === 'signedIn') navigate(next ?? homePathFor(result.user), { replace: true });
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!role || !fullName.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const created = await completeProfile({ role, fullName: fullName.trim(), ...(phone ? { phone } : {}) });
      navigate(role === 'planner' && next ? next : homePathFor(created), { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-bg" aria-hidden="true" />

      <div className="auth-card">
        <Link to="/" className="auth-logo">
          <span className="auth-logo-text">prasang</span>
          <span className="auth-logo-hindi">प्रसंग</span>
        </Link>

        <h1 className="auth-title">{profileStep ? 'One last step' : copy.title}</h1>
        <p className="auth-subtitle">{profileStep ? 'Tell us who you are so we can set things up' : copy.subtitle}</p>

        <div className="auth-role-grid">
          <button type="button" className={`auth-role-card${role === 'artist' ? ' selected' : ''}`} onClick={() => setRole('artist')}>
            <span className="auth-role-icon">🎤</span>
            <span className="auth-role-label">I'm an Artist</span>
            <span className="auth-role-desc">List my services & get discovered</span>
          </button>
          <button type="button" className={`auth-role-card${role === 'planner' ? ' selected' : ''}`} onClick={() => setRole('planner')}>
            <span className="auth-role-icon">🎉</span>
            <span className="auth-role-label">I'm Planning</span>
            <span className="auth-role-desc">Find artists for my event</span>
          </button>
        </div>

        {!role && <p className="auth-role-select-hint">Select your role to continue</p>}
        {status === 'error' && <p className="auth-role-select-hint">We couldn't reach Prasang. Check your connection and try again.</p>}
        <InlineError error={error} />

        {profileStep ? (
          <form onSubmit={handleProfile} className="auth-form">
            <div className="auth-form-group">
              <label className="auth-label" htmlFor="auth-full-name">{role === 'artist' ? 'Full name / Stage name' : 'Your name'}</label>
              <input id="auth-full-name" className="auth-input" placeholder="Rahul Sharma" value={fullName}
                onChange={(e) => setFullName(e.target.value)} required autoFocus />
            </div>
            <div className="auth-form-group">
              <label className="auth-label" htmlFor="auth-phone">Mobile number (optional)</label>
              <div className="auth-phone-input">
                <span className="auth-phone-code">+91</span>
                <input id="auth-phone" type="tel" className="auth-input phone-field" placeholder="9876543210" value={phone}
                  onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))} maxLength={10} />
              </div>
              <p className="auth-field-hint">Used to pre-fill enquiries. Never shown publicly.</p>
            </div>
            <button type="submit" className="auth-submit-btn" disabled={loading || !role || !fullName.trim() || (phone.length > 0 && phone.length !== 10)}>
              {loading ? 'Saving...' : 'Continue'}
            </button>
          </form>
        ) : (
          <>
            <div className="auth-tabs" role="tablist">
              <button role="tab" aria-selected={tab === 'google'} className={`auth-tab${tab === 'google' ? ' active' : ''}`} onClick={() => setTab('google')}>
                Google
              </button>
              <button role="tab" aria-selected={tab === 'otp'} className={`auth-tab${tab === 'otp' ? ' active' : ''}`} onClick={() => setTab('otp')}>
                <Phone size={16} /> Mobile OTP
              </button>
            </div>

            {tab === 'google' ? (
              <div className="auth-google-section">
                <button className="auth-google-btn" onClick={handleGoogle} disabled={loading || !role}>
                  <GoogleIcon />
                  {loading ? copy.busy : copy.google}
                </button>
                <p className="auth-google-note">{copy.note}</p>
              </div>
            ) : (
              <div className="auth-google-section">
                <p className="auth-google-note">Mobile OTP sign-in is coming soon. Please continue with Google for now.</p>
              </div>
            )}

            <div className="auth-divider"><span>{copy.switchText}</span></div>
            <Link to={copy.switchTo + (role ? `?role=${role}` : '')} className="auth-switch-btn">{copy.switchLink}</Link>
          </>
        )}

        <p className="auth-terms">
          By continuing, you agree to our{' '}
          <Link to="/terms-of-service" className="auth-terms-link">Terms of Service</Link> and{' '}
          <Link to="/privacy-policy" className="auth-terms-link">Privacy Policy</Link>.
        </p>
      </div>
    </div>
  );
}
