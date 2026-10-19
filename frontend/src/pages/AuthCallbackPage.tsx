// Google sends the user back here (/auth/callback/google). Finish the SuperTokens sign-in, then route them on.
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { homePathFor } from '../auth/paths';
import FullPageSpinner from '../components/FullPageSpinner';
import { errorMessage } from '../api/errors';
import '../components/QueryState.css';

export default function AuthCallbackPage() {
  const { completeGoogleRedirect } = useAuth();
  const navigate = useNavigate();
  const [failure, setFailure] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // StrictMode runs effects twice; the OAuth code can only be used once
    started.current = true;
    completeGoogleRedirect()
      .then((result) => {
        if (result.status === 'signedIn') navigate(homePathFor(result.user), { replace: true });
        else if (result.status === 'needsProfile') navigate('/signup?step=profile', { replace: true });
        else setFailure(result.reason);
      })
      .catch((e) => setFailure(errorMessage(e)));
  }, [completeGoogleRedirect, navigate]);

  if (!failure) return <FullPageSpinner label="Signing you in…" />;
  return (
    <div className="qs-fullpage" role="alert">
      <span className="qs-error-title">Google sign-in didn't complete</span>
      <span className="qs-label">{failure}</span>
      <Link to="/login" className="qs-retry">Back to sign in</Link>
    </div>
  );
}
