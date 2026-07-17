import { Link } from 'react-router-dom';
import { Eye, MessageCircle, TrendingUp, Star, Crown, ArrowRight, Bell, ChevronRight } from 'lucide-react';
import './ArtistPages.css';

const METRICS = [
  { label: 'Profile Views', value: '1,243', change: '+18%', icon: <Eye size={20} />, up: true },
  { label: 'Contact Clicks', value: '87', change: '+34%', icon: <MessageCircle size={20} />, up: true },
  { label: 'Leads This Month', value: '23', change: '+12%', icon: <TrendingUp size={20} />, up: true },
  { label: 'Avg. Rating', value: '4.8', change: '12 reviews', icon: <Star size={20} />, up: true },
];

const RECENT_LEADS = [
  { name: 'Rahul Mehta', event: 'Wedding Reception', date: 'Dec 28', budget: '₹40k–60k', status: 'new' },
  { name: 'Priya Gupta', event: 'Corporate Event', date: 'Jan 5', budget: '₹25k–40k', status: 'new' },
  { name: 'Arjun Singh', event: 'Birthday Party', date: 'Dec 31', budget: '₹15k–25k', status: 'viewed' },
];

const LEAD_SOURCES = [
  { label: 'Search results', pct: 42 },
  { label: 'Featured placement', pct: 28 },
  { label: 'Direct profile link', pct: 18 },
  { label: 'Category browse', pct: 12 },
];

export default function DashboardPage() {
  return (
    <div className="artist-layout">
      {/* Sidebar */}
      <aside className="artist-sidebar">
        <Link to="/" className="sidebar-logo">
          <span>prasang</span>
          <span className="sidebar-logo-hindi">प्रसंग</span>
        </Link>

        <nav className="sidebar-nav">
          <Link to="/artist/dashboard" className="sidebar-link active">
            <TrendingUp size={18} /> Dashboard
          </Link>
          <Link to="/artist/leads" className="sidebar-link">
            <MessageCircle size={18} /> Leads
          </Link>
          <Link to="/artist/onboarding" className="sidebar-link">
            <Star size={18} /> My Profile
          </Link>
          <Link to="/pricing" className="sidebar-link">
            <Crown size={18} /> Upgrade
          </Link>
        </nav>

        <div className="sidebar-tier-card">
          <div className="sidebar-tier-name">Basic Plan</div>
          <div className="sidebar-tier-note">15 leads/month · 6 used</div>
          <div className="sidebar-tier-bar">
            <div className="sidebar-tier-fill" style={{ width: '40%' }} />
          </div>
          <Link to="/pricing" className="sidebar-upgrade-btn">
            Upgrade to Pro <ArrowRight size={14} />
          </Link>
        </div>
      </aside>

      {/* Main */}
      <main className="artist-main">
        <header className="artist-topbar">
          <div>
            <h1 className="artist-page-title">Dashboard</h1>
            <p className="artist-page-sub">Good morning, Arjun 👋</p>
          </div>
          <div className="topbar-actions">
            <button className="topbar-icon-btn" aria-label="Notifications">
              <Bell size={20} />
              <span className="notif-dot" />
            </button>
            <Link to={`/profile/arjun-malhotra`} className="topbar-view-profile">
              View Profile
            </Link>
          </div>
        </header>

        {/* Upgrade prompt */}
        <div className="upgrade-banner">
          <Crown size={20} className="upgrade-icon" />
          <div className="upgrade-text">
            <strong>Get 3× more leads</strong> — Upgrade to Pro for unlimited leads + top search placement
          </div>
          <Link to="/pricing" className="upgrade-btn">Upgrade now</Link>
        </div>

        {/* Metrics */}
        <div className="metrics-grid">
          {METRICS.map((m) => (
            <div key={m.label} className="metric-card">
              <div className="metric-header">
                <span className="metric-label">{m.label}</span>
                <span className="metric-icon">{m.icon}</span>
              </div>
              <div className="metric-value">{m.value}</div>
              <div className={`metric-change${m.up ? ' up' : ' down'}`}>{m.change} this month</div>
            </div>
          ))}
        </div>

        <div className="dashboard-row">
          {/* Recent leads */}
          <div className="dashboard-card">
            <div className="card-header">
              <h2 className="card-title">Recent Leads</h2>
              <Link to="/artist/leads" className="card-action">View all <ChevronRight size={14} /></Link>
            </div>
            <div className="leads-list">
              {RECENT_LEADS.map((lead) => (
                <div key={lead.name} className="lead-item">
                  <div className="lead-avatar">{lead.name[0]}</div>
                  <div className="lead-info">
                    <div className="lead-name">{lead.name}</div>
                    <div className="lead-event">{lead.event} · {lead.date}</div>
                  </div>
                  <div className="lead-right">
                    <div className="lead-budget">{lead.budget}</div>
                    {lead.status === 'new' && <span className="lead-badge new">New</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Lead sources */}
          <div className="dashboard-card">
            <div className="card-header">
              <h2 className="card-title">Lead Sources</h2>
              <span className="card-period">Last 30 days</span>
            </div>
            <div className="sources-list">
              {LEAD_SOURCES.map((s) => (
                <div key={s.label} className="source-item">
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

        {/* Profile completeness */}
        <div className="profile-completeness">
          <div className="complete-header">
            <h2 className="card-title">Profile strength: 65%</h2>
            <div className="complete-bar-wrap">
              <div className="complete-bar">
                <div className="complete-fill" style={{ width: '65%' }} />
              </div>
              <span className="complete-pct">65%</span>
            </div>
          </div>
          <div className="complete-items">
            {[
              { done: true, label: 'Basic info added' },
              { done: true, label: 'Profile photo uploaded' },
              { done: true, label: 'Bio written' },
              { done: false, label: 'Add portfolio media' },
              { done: false, label: 'Connect Instagram' },
              { done: false, label: 'Get your first review' },
            ].map((item) => (
              <div key={item.label} className={`complete-item${item.done ? ' done' : ''}`}>
                <span className="complete-dot" />
                {item.label}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
