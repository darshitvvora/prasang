import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import { guardDecision } from './paths';
import FullPageSpinner from '../components/FullPageSpinner';

export default function RequireRole({ role, children }: { role: 'artist' | 'planner'; children: ReactNode }) {
  const { status, user } = useAuth();
  const location = useLocation();
  const decision = guardDecision(status, user, role, location.pathname + location.search);
  if (decision.type === 'loading') return <FullPageSpinner />;
  if (decision.type === 'redirect') return <Navigate to={decision.to} replace />;
  return <>{children}</>;
}
