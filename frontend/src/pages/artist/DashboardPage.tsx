import { Link } from 'react-router-dom';
import { Eye, MessageCircle, TrendingUp, Star, Crown, ChevronRight } from 'lucide-react';
import ArtistSidebar from '../../components/ArtistSidebar';
import QueryState from '../../components/QueryState';
import { useArtistDashboard, useMyArtist } from '../../api/queries';
import { suspensionMessage } from './suspension';
import { useAuth } from '../../auth/AuthProvider';
import { formatDate } from '../../api/format';
import type { ArtistDashboard, Metric } from '../../api/types';
import './ArtistPages.css';

function greeting(now = new Date()) {
  const h = now.getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

const change = (m: Metric) => (m.changePct === null ? 'New' : `${m.changePct >= 0 ? '+' : ''}${m.changePct}% this month`);
const budgetK = (min: number, max: number | null) => `₹${(min / 1000).toFixed(0)}k${max === null ? '+' : `–${(max / 1000).toFixed(0)}k`}`;

function Dashboard({ data }: { data: ArtistDashboard }) {
  const { metrics } = data;
  const cards = [
    { label: 'Profile Views', value: metrics.profileViews.value.toLocaleString('en-IN'), note: change(metrics.profileViews), up: (metrics.profileViews.changePct ?? 0) >= 0, icon: <Eye size={20} /> },
    { label: 'Contact Clicks', value: metrics.contactClicks.value.toLocaleString('en-IN'), note: change(metrics.contactClicks), up: (metrics.contactClicks.changePct ?? 0) >= 0, icon: <MessageCircle size={20} /> },
    { label: 'Leads This Month', value: String(metrics.leadsThisMonth.value), note: change(metrics.leadsThisMonth), up: (metrics.leadsThisMonth.changePct ?? 0) >= 0, icon: <TrendingUp size={20} /> },
    { label: 'Avg. Rating', value: metrics.averageRating.totalReviews ? metrics.averageRating.value.toFixed(1) : '–', note: `${metrics.averageRating.totalReviews} reviews`, up: true, icon: <Star size={20} /> },
  ];
  const showUpgrade = data.plan.tier !== 'premium';

  return (
    <>
      {!data.isPublished && (
        <div className="upgrade-banner unpublished">
          <Star size={20} className="upgrade-icon" />
          <div className="upgrade-text">
            <strong>Your profile isn't live yet.</strong> Planners can't find you until you finish setup and launch it.
          </div>
          <Link to="/artist/onboarding" className="upgrade-btn">Finish setup</Link>
        </div>
      )}
      {showUpgrade && data.isPublished && (
        <div className="upgrade-banner">
          <Crown size={20} className="upgrade-icon" />
          <div className="upgrade-text">
            <strong>Get 3× more leads</strong> — Upgrade to Pro for unlimited leads + top search placement
          </div>
          <Link to="/pricing" className="upgrade-btn">Upgrade now</Link>
        </div>
      )}

      <div className="metrics-grid">
        {cards.map((m) => (
          <div key={m.label} className="metric-card">
            <div className="metric-header">
              <span className="metric-label">{m.label}</span>
              <span className="metric-icon">{m.icon}</span>
            </div>
            <div className="metric-value">{m.value}</div>
            <div className={`metric-change${m.up ? ' up' : ' down'}`}>{m.note}</div>
          </div>
        ))}
      </div>

      <div className="dashboard-row">
        <div className="dashboard-card">
          <div className="card-header">
            <h2 className="card-title">Recent Leads</h2>
            <Link to="/artist/leads" className="card-action">View all <ChevronRight size={14} /></Link>
          </div>
          <div className="leads-list">
            {data.recentLeads.length === 0 && <p className="lead-event">No leads yet — share your profile link to get started.</p>}
            {data.recentLeads.map((lead) => (
              <div key={lead.id} className="lead-item">
                <div className="lead-avatar">{lead.plannerName[0]}</div>
                <div className="lead-info">
                  <div className="lead-name">{lead.plannerName}</div>
                  <div className="lead-event">{lead.eventTitle}{lead.eventDate ? ` · ${formatDate(lead.eventDate)}` : ''}</div>
                </div>
                <div className="lead-right">
                  <div className="lead-budget">{budgetK(lead.budgetMin, lead.budgetMax)}</div>
                  {lead.status === 'new' && <span className="lead-badge new">{lead.isLocked ? 'Locked' : 'New'}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="dashboard-card">
          <div className="card-header">
            <h2 className="card-title">Lead Sources</h2>
            <span className="card-period">Last 30 days</span>
          </div>
          <div className="sources-list">
            {data.leadSources.map((s) => (
              <div key={s.source} className="source-item">
                <div className="source-label-row">
                  <span className="source-label">{s.label}</span>
                  <span className="source-pct">{s.pct}%</span>
                </div>
                <div className="source-bar">
                  <div className="source-fill" style={{ width: `${s.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="profile-completeness">
        <div className="complete-header">
          <h2 className="card-title">Profile strength: {data.completeness.percent}%</h2>
          <div className="complete-bar-wrap">
            <div className="complete-bar">
              <div className="complete-fill" style={{ width: `${data.completeness.percent}%` }} />
            </div>
            <span className="complete-pct">{data.completeness.percent}%</span>
          </div>
        </div>
        <div className="complete-items">
          {data.completeness.items.map((item) => (
            <div key={item.key} className={`complete-item${item.done ? ' done' : ''}`}>
              <span className="complete-dot" />
              {item.label}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const dashboard = useArtistDashboard();
  const name = dashboard.data?.greetingName ?? user?.fullName.split(' ')[0] ?? '';
  const myArtist = useMyArtist();
  const hidden = myArtist.data ? suspensionMessage(myArtist.data) : null;

  return (
    <div className="artist-layout">
      <ArtistSidebar active="dashboard" />

      <main className="artist-main">
        <header className="artist-topbar">
          <div>
            <h1 className="artist-page-title">Dashboard</h1>
            <p className="artist-page-sub">{greeting()}{name ? `, ${name}` : ''} 👋</p>
          </div>
          <div className="topbar-actions">
            {user?.artistSlug && dashboard.data?.isPublished && (
              <Link to={`/profile/${user.artistSlug}`} className="topbar-view-profile">View Profile</Link>
            )}
          </div>
        </header>

        {hidden && (
          <div className="artist-suspension-banner" role="alert">
            {hidden} <Link to="/contact">Contact us</Link> if you have questions.
          </div>
        )}

        <QueryState query={dashboard}>{(data) => <Dashboard data={data} />}</QueryState>
      </main>
    </div>
  );
}
