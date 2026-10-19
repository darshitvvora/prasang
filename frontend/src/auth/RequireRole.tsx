import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import { guardDecision } from './paths';
import FullPageSpinner from '../components/FullPageSpinner';

export default function RequireRole({ role, children }: { role: 'artist' | 'planner'; children: ReactNode }) {
  const { status, user, retry } = useAuth();
  const location = useLocation();
  const decision = guardDecision(status, user, role, location.pathname + location.search);
  if (decision.type === 'loading') return <FullPageSpinner />;
  if (decision.type === 'error') {
    return (
      <div className="qs-fullpage" role="alert">
        <span className="qs-error-title">We couldn't reach Prasang</span>
        <span className="qs-label">Check your connection — you're still signed in.</span>
        <button type="button" className="qs-retry" onClick={retry}>Try again</button>
      </div>
    );
  }
  if (decision.type === 'redirect') return <Navigate to={decision.to} replace />;
  return <>{children}</>;
}
