// Sidebar shared by the artist dashboard and leads pages, with live plan usage.
import { Link } from 'react-router-dom';
import { ArrowRight, Crown, CreditCard, MessageCircle, MessageSquare, Star, TrendingUp } from 'lucide-react';
import { useMySubscription } from '../api/queries';
import { usageNote, usagePct } from '../pages/artist/planUsage';
import '../pages/artist/ArtistPages.css';

type Active = 'dashboard' | 'leads' | 'profile' | 'subscription' | 'reviews';

const NEXT_TIER: Record<string, string | null> = { free: 'Pro', pro: 'Premium', premium: null };

export default function ArtistSidebar({ active }: { active: Active }) {
  const sub = useMySubscription();
  const plan = sub.data?.plan;
  const next = plan ? NEXT_TIER[plan.tier] : null;
  const link = (to: string, key: Active, icon: React.ReactNode, label: string) => (
    <Link to={to} className={`sidebar-link${active === key ? ' active' : ''}`}>{icon} {label}</Link>
  );

  return (
    <aside className="artist-sidebar">
      <Link to="/" className="sidebar-logo">
        <span>prasang</span>
        <span className="sidebar-logo-hindi">प्रसंग</span>
      </Link>
      <nav className="sidebar-nav">
        {link('/artist/dashboard', 'dashboard', <TrendingUp size={18} />, 'Dashboard')}
        {link('/artist/leads', 'leads', <MessageCircle size={18} />, 'Leads')}
        {link('/artist/onboarding', 'profile', <Star size={18} />, 'My Profile')}
        {link('/artist/reviews', 'reviews', <MessageSquare size={18} />, 'Reviews')}
        {link('/artist/subscription', 'subscription', <CreditCard size={18} />, 'My Plan')}
        <Link to="/pricing" className="sidebar-link"><Crown size={18} /> Upgrade</Link>
      </nav>
      {plan && (
        <div className="sidebar-tier-card">
          <div className="sidebar-tier-name">{plan.name} Plan{plan.status === 'trial' ? ' (trial)' : ''}</div>
          <div className="sidebar-tier-note">{usageNote(plan)}</div>
          <div className="sidebar-tier-bar">
            <div className="sidebar-tier-fill" style={{ width: `${usagePct(plan)}%` }} />
          </div>
          {next && (
            <Link to="/pricing" className="sidebar-upgrade-btn">
              Upgrade to {next} <ArrowRight size={14} />
            </Link>
          )}
        </div>
      )}
    </aside>
  );
}
