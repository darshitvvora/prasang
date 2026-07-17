import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Phone, ArrowLeft, RefreshCw } from 'lucide-react';
import './AuthPages.css';

type Role = 'artist' | 'buyer';
type AuthTab = 'google' | 'otp';
type OtpStep = 'phone' | 'verify';

export default function SignupPage() {
  const [role, setRole] = useState<Role | null>(null);
  const [tab, setTab] = useState<AuthTab>('google');
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [otpStep, setOtpStep] = useState<OtpStep>('phone');
  const [countdown, setCountdown] = useState(0);
  const [loading, setLoading] = useState(false);

  function startCountdown() {
    setCountdown(60);
    const t = setInterval(() => {
      setCountdown((c) => { if (c <= 1) { clearInterval(t); return 0; } return c - 1; });
    }, 1000);
  }

  async function handleSendOTP(e: React.FormEvent) {
    e.preventDefault();
    if (!role || !/^[6-9]\d{9}$/.test(phone)) return;
    setLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    setLoading(false);
    setOtpStep('verify');
    startCountdown();
  }

  async function handleVerifyOTP(e: React.FormEvent) {
    e.preventDefault();
    if (otp.length < 6) return;
    setLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    setLoading(false);
    window.location.href = role === 'artist' ? '/artist/onboarding' : '/planner/dashboard';
  }

  async function handleGoogleSignup() {
    if (!role) return;
    setLoading(true);
    await new Promise((r) => setTimeout(r, 600));
    window.location.href = role === 'artist' ? '/artist/onboarding' : '/planner/dashboard';
  }

  return (
    <div className="auth-page">
      <div className="auth-bg" aria-hidden="true" />

      <div className="auth-card">
        {/* Logo */}
        <Link to="/" className="auth-logo">
          <span className="auth-logo-text">prasang</span>
          <span className="auth-logo-hindi">प्रसंग</span>
        </Link>

        <h1 className="auth-title">Create account</h1>
        <p className="auth-subtitle">Join India's largest artist discovery platform</p>

        {/* Role selection */}
        <div className="auth-role-grid">
          <button
            className={`auth-role-card${role === 'artist' ? ' selected' : ''}`}
            onClick={() => setRole('artist')}
          >
            <span className="auth-role-icon">🎤</span>
            <span className="auth-role-label">I'm an Artist</span>
            <span className="auth-role-desc">List my services & get discovered</span>
          </button>
          <button
            className={`auth-role-card${role === 'buyer' ? ' selected' : ''}`}
            onClick={() => setRole('buyer')}
          >
            <span className="auth-role-icon">🎉</span>
            <span className="auth-role-label">I'm Planning</span>
            <span className="auth-role-desc">Find artists for my event</span>
          </button>
        </div>

        {!role && (
          <p className="auth-role-select-hint">Select your role to continue</p>
        )}

        {/* Tab switch */}
        <div className="auth-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={tab === 'google'}
            className={`auth-tab${tab === 'google' ? ' active' : ''}`}
            onClick={() => setTab('google')}
          >
            Google
          </button>
          <button
            role="tab"
            aria-selected={tab === 'otp'}
            className={`auth-tab${tab === 'otp' ? ' active' : ''}`}
            onClick={() => setTab('otp')}
          >
            <Phone size={16} /> Mobile OTP
          </button>
        </div>

        {/* Google Signup */}
        {tab === 'google' && (
          <div className="auth-google-section">
            <button
              className="auth-google-btn"
              onClick={handleGoogleSignup}
              disabled={loading || !role}
            >
              <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                <path fill="none" d="M0 0h48v48H0z"/>
              </svg>
              {loading ? 'Creating account...' : 'Continue with Google'}
            </button>
            <p className="auth-google-note">
              Free to sign up. No credit card required.
            </p>
          </div>
        )}

        {/* Mobile OTP */}
        {tab === 'otp' && (
          <>
            {otpStep === 'phone' ? (
              <form onSubmit={handleSendOTP} className="auth-form">
                <div className="auth-form-group">
                  <label className="auth-label">Mobile Number</label>
                  <div className="auth-phone-input">
                    <span className="auth-phone-code">+91</span>
                    <input
                      type="tel"
                      className="auth-input phone-field"
                      placeholder="9876543210"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                      maxLength={10}
                      required
                      autoFocus
                    />
                  </div>
                  <p className="auth-field-hint">We'll send a 6-digit OTP to this number</p>
                </div>
                <button
                  type="submit"
                  className="auth-submit-btn"
                  disabled={loading || phone.length !== 10 || !role}
                >
                  {loading ? 'Sending...' : 'Send OTP'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleVerifyOTP} className="auth-form">
                <div className="auth-otp-back">
                  <button
                    type="button"
                    className="auth-otp-back-btn"
                    onClick={() => { setOtpStep('phone'); setOtp(''); }}
                  >
                    <ArrowLeft size={16} /> +91 {phone}
                  </button>
                </div>
                <div className="auth-form-group">
                  <label className="auth-label">Enter OTP</label>
                  <input
                    type="text"
                    className="auth-input otp-input"
                    placeholder="000000"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    maxLength={6}
                    autoFocus
                    required
                  />
                  <div className="auth-otp-actions">
                    <button
                      type="button"
                      className="auth-resend-btn"
                      disabled={countdown > 0}
                      onClick={() => { setOtp(''); startCountdown(); }}
                    >
                      <RefreshCw size={14} />
                      {countdown > 0 ? `Resend in ${countdown}s` : 'Resend OTP'}
                    </button>
                  </div>
                </div>
                <button
                  type="submit"
                  className="auth-submit-btn"
                  disabled={loading || otp.length < 6}
                >
                  {loading ? 'Verifying...' : 'Create Account'}
                </button>
              </form>
            )}
          </>
        )}

        <div className="auth-divider">
          <span>Already have an account?</span>
        </div>

        <Link to="/login" className="auth-switch-btn">Sign in</Link>

        <p className="auth-terms">
          By creating an account, you agree to our{' '}
          <Link to="/terms" className="auth-terms-link">Terms of Service</Link> and{' '}
          <Link to="/privacy" className="auth-terms-link">Privacy Policy</Link>.
        </p>
      </div>
    </div>
  );
}
