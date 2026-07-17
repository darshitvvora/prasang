import { useState } from 'react';
import { Link } from 'react-router-dom';
import { MessageCircle, TrendingUp, Star, Crown, Phone, Calendar, MapPin, IndianRupee, ChevronDown } from 'lucide-react';
import './ArtistPages.css';

type LeadStatus = 'all' | 'new' | 'contacted' | 'converted' | 'expired';

const LEADS = [
  {
    id: '1', name: 'Rahul Mehta', phone: '+91 98765 XXXXX', event: 'Wedding Reception',
    city: 'Mumbai', area: 'Bandra West', date: '2024-12-28', budgetMin: 40000, budgetMax: 60000,
    notes: 'Looking for a magician for ~100 guests, 2 hours show', status: 'new', createdAt: '2 hours ago'
  },
  {
    id: '2', name: 'Priya Gupta', phone: '+91 87654 XXXXX', event: 'Corporate Gala',
    city: 'Mumbai', area: 'Nariman Point', date: '2025-01-05', budgetMin: 25000, budgetMax: 40000,
    notes: 'Annual company event, need 45-min performance', status: 'new', createdAt: '5 hours ago'
  },
  {
    id: '3', name: 'Arjun Singh', phone: '+91 76543 XXXXX', event: 'Birthday Party',
    city: 'Pune', area: 'Koregaon Park', date: '2024-12-31', budgetMin: 15000, budgetMax: 25000,
    notes: 'Kid-friendly magic show, 30-40 children', status: 'contacted', createdAt: '1 day ago'
  },
  {
    id: '4', name: 'Sneha Patel', phone: '+91 65432 XXXXX', event: 'Product Launch',
    city: 'Mumbai', area: 'BKC', date: '2025-01-12', budgetMin: 50000, budgetMax: 80000,
    notes: 'Tech company launch event, 200 attendees', status: 'converted', createdAt: '3 days ago'
  },
  {
    id: '5', name: 'Vikram Joshi', phone: '+91 54321 XXXXX', event: 'Anniversary Party',
    city: 'Thane', area: 'Hiranandani', date: '2024-12-20', budgetMin: 20000, budgetMax: 35000,
    notes: 'Silver jubilee celebration', status: 'expired', createdAt: '10 days ago'
  },
];

const STATUS_COLORS: Record<string, string> = {
  new: '#d4f53f',
  contacted: '#60a5fa',
  converted: '#4ade80',
  expired: '#666',
};

export default function LeadsPage() {
  const [filter, setFilter] = useState<LeadStatus>('all');
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = filter === 'all' ? LEADS : LEADS.filter((l) => l.status === filter);
  const counts = {
    all: LEADS.length,
    new: LEADS.filter((l) => l.status === 'new').length,
    contacted: LEADS.filter((l) => l.status === 'contacted').length,
    converted: LEADS.filter((l) => l.status === 'converted').length,
    expired: LEADS.filter((l) => l.status === 'expired').length,
  };

  return (
    <div className="artist-layout">
      <aside className="artist-sidebar">
        <Link to="/" className="sidebar-logo">
          <span>prasang</span>
          <span className="sidebar-logo-hindi">प्रसंग</span>
        </Link>
        <nav className="sidebar-nav">
          <Link to="/artist/dashboard" className="sidebar-link">
            <TrendingUp size={18} /> Dashboard
          </Link>
          <Link to="/artist/leads" className="sidebar-link active">
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
            Upgrade to Pro <span>→</span>
          </Link>
        </div>
      </aside>

      <main className="artist-main">
        <header className="artist-topbar">
          <div>
            <h1 className="artist-page-title">Leads</h1>
            <p className="artist-page-sub">Event planners who want to book you</p>
          </div>
        </header>

        {/* Upgrade if on free */}
        <div className="upgrade-banner">
          <Crown size={20} className="upgrade-icon" />
          <div className="upgrade-text">
            <strong>You have 9 leads remaining this month.</strong> Upgrade to Pro for unlimited leads.
          </div>
          <Link to="/pricing" className="upgrade-btn">Upgrade</Link>
        </div>

        {/* Filter tabs */}
        <div className="leads-filter-tabs">
          {(['all', 'new', 'contacted', 'converted', 'expired'] as LeadStatus[]).map((s) => (
            <button
              key={s}
              className={`leads-filter-tab${filter === s ? ' active' : ''}`}
              onClick={() => setFilter(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
              <span className="tab-count">{counts[s]}</span>
            </button>
          ))}
        </div>

        {/* Leads list */}
        <div className="leads-cards">
          {filtered.length === 0 && (
            <div className="leads-empty">No leads in this category yet.</div>
          )}
          {filtered.map((lead) => (
            <div key={lead.id} className="lead-card">
              <div className="lead-card-top">
                <div className="lead-card-left">
                  <div className="lead-card-avatar">{lead.name[0]}</div>
                  <div>
                    <div className="lead-card-name">{lead.name}</div>
                    <div className="lead-card-meta">
                      <span><Calendar size={12} /> {lead.date}</span>
                      <span><MapPin size={12} /> {lead.area}, {lead.city}</span>
                    </div>
                  </div>
                </div>
                <div className="lead-card-right">
                  <span
                    className="lead-status-badge"
                    style={{ background: `${STATUS_COLORS[lead.status]}20`, color: STATUS_COLORS[lead.status] }}
                  >
                    {lead.status}
                  </span>
                  <span className="lead-time">{lead.createdAt}</span>
                </div>
              </div>

              <div className="lead-card-event">
                <span className="lead-event-type">{lead.event}</span>
                <span className="lead-budget">
                  <IndianRupee size={12} />
                  {(lead.budgetMin / 1000).toFixed(0)}k – {(lead.budgetMax / 1000).toFixed(0)}k
                </span>
              </div>

              {expanded === lead.id && (
                <div className="lead-card-expanded">
                  <div className="lead-notes">{lead.notes}</div>
                  <div className="lead-actions">
                    <a
                      href={`tel:${lead.phone}`}
                      className="lead-action-btn phone"
                    >
                      <Phone size={15} /> Call
                    </a>
                    <a
                      href={`https://wa.me/${lead.phone.replace(/\D/g, '')}`}
                      target="_blank"
                      rel="noreferrer"
                      className="lead-action-btn whatsapp"
                    >
                      WhatsApp
                    </a>
                    <span className="lead-phone-reveal">{lead.phone}</span>
                  </div>
                </div>
              )}

              <button
                className="lead-expand-btn"
                onClick={() => setExpanded(expanded === lead.id ? null : lead.id)}
              >
                {expanded === lead.id ? 'Hide details' : 'View details'}
                <ChevronDown
                  size={14}
                  style={{ transform: expanded === lead.id ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
                />
              </button>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
