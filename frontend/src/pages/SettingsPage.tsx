import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { useAuth } from '../auth/AuthProvider';
import { deleteMe } from '../api/endpoints';
import { CONFIRM_DELETE_KEY, reauthStep, sameAccount, type ReauthStep } from './settings';
import './legal/LegalPages.css';
import './site.css';

type Phase = 'idle' | 'confirm' | 'otp' | 'working' | 'deleted';

export default function SettingsPage() {
  const { status, user, sendOtp, verifyOtp, signInWithGoogle, signOut } = useAuth();
  const [phase, setPhase] = useState<Phase>(() => (sessionStorage.getItem(CONFIRM_DELETE_KEY) ? 'confirm' : 'idle'));
  const [step, setStep] = useState<ReauthStep | null>(null);
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => sessionStorage.removeItem(CONFIRM_DELETE_KEY), []);

  const attemptDelete = async () => {
    setPhase('working');
    setError(null);
    const expected = sessionStorage.getItem(CONFIRM_DELETE_KEY);
    if (expected && user && !sameAccount(expected, user)) {
      sessionStorage.removeItem(CONFIRM_DELETE_KEY);
      setError(`You confirmed with a different Google account (${user.email ?? 'unknown'}). Nothing was deleted — sign in with the account you want to delete.`);
      setPhase('idle');
      return;
    }
    try {
      await deleteMe();
      sessionStorage.removeItem(CONFIRM_DELETE_KEY);
      setPhase('deleted');
      signOut();
    } catch (err) {
      const next = reauthStep(err);
      setStep(next);
      if (next.kind === 'otp') {
        await sendOtp(next.phone);
        setPhase('otp');
      } else if (next.kind === 'google' && user) {
        sessionStorage.setItem(CONFIRM_DELETE_KEY, next.email ?? '');
        await signInWithGoogle(user.role === 'artist' ? 'artist' : 'planner');
      } else {
        setError(next.kind === 'error' ? next.message : 'Something went wrong. Please try again.');
        setPhase('confirm');
      }
    }
  };

  const submitCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    const result = await verifyOtp(code.trim(), user.role === 'artist' ? 'artist' : 'planner');
    if (result.status === 'incorrect') return setError('That code is not right. Check the SMS and try again.');
    if (result.status === 'expired' || result.status === 'restart') return setError('That code has expired. Start again.');
    await attemptDelete();
  };

  if (phase === 'deleted') {
    return (
      <>
        <Navbar />
        <main className="legal-page-container">
          <h1 className="legal-page-title">Your account has been deleted</h1>
          <p>Your personal details have been removed from Prasang. You can sign up again any time.</p>
          <Link to="/">Back to Prasang</Link>
        </main>
        <Footer />
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="legal-page-container">
        <div className="legal-page-header"><h1 className="legal-page-title">Account settings</h1></div>
        {status !== 'signedIn' || !user ? (
          <p><Link to="/login">Sign in</Link> to manage your account.</p>
        ) : (
          <div className="legal-page-content">
            <h2>Your account</h2>
            <ul className="site-contact-details">
              <li>Name: {user.fullName}</li>
              {user.phone && <li>Mobile: +91 {user.phone}</li>}
              {user.email && <li>Email: {user.email}</li>}
              <li>Account type: {user.role === 'artist' ? 'Artist' : 'Event planner'}</li>
            </ul>

            <h2>Delete my account</h2>
            <p>This happens immediately and can't be undone.</p>
            <ul>
              <li>Your name, phone number and email are removed.</li>
              {user.role === 'artist' && <li>Your profile is taken down, your photos and videos are deleted and any paid plan is cancelled straight away.</li>}
              {user.role === 'planner' && <li>Artists you contacted will see "Deleted user"; your reviews stay up as "Former user".</li>}
              <li>We keep payment records (amounts and dates, no contact details) because the law requires it.</li>
            </ul>
            {phase === 'idle' && (
              <button type="button" className="site-contact-submit settings-danger" onClick={() => setPhase('confirm')}>Delete my account</button>
            )}
            {(phase === 'confirm' || phase === 'working') && (
              <div className="settings-confirm">
                <p>To confirm, we'll ask you to sign in again{step?.kind === 'google' ? ' with Google' : ''}.</p>
                <button type="button" className="site-contact-submit settings-danger" disabled={phase === 'working'} onClick={attemptDelete}>
                  {phase === 'working' ? 'Working…' : 'Yes, delete my account'}
                </button>
                <button type="button" className="settings-cancel" onClick={() => { sessionStorage.removeItem(CONFIRM_DELETE_KEY); setPhase('idle'); }}>Cancel</button>
              </div>
            )}
            {phase === 'otp' && step?.kind === 'otp' && (
              <form className="site-contact-form" onSubmit={submitCode}>
                <label>Enter the code we sent to +91 {step.phone}
                  <input inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} />
                </label>
                <button type="submit" className="site-contact-submit settings-danger">Confirm and delete</button>
              </form>
            )}
            {error && <p className="contact-form-error" role="alert">{error}</p>}
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
