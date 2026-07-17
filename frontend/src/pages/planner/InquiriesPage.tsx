import { useState } from 'react';
import { Link } from 'react-router-dom';
import { LayoutDashboard, MessageCircle, Heart, Search, Calendar, MapPin, IndianRupee, ChevronDown, ExternalLink, ChevronRight } from 'lucide-react';
import { mockArtists } from '../../data/mockArtists';
import { INQUIRIES, STATUS_COLORS } from '../../data/mockPlannerActivity';
import type { InquiryStatus } from '../../data/mockPlannerActivity';
import { ARTIST_TYPE_LABELS } from '../../types/artist';
import './PlannerPages.css';

type FilterStatus = 'all' | InquiryStatus;

export default function InquiriesPage() {
  const [filter, setFilter] = useState<FilterStatus>('all');
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = filter === 'all' ? INQUIRIES : INQUIRIES.filter((i) => i.status === filter);
  const counts = {
    all: INQUIRIES.length,
    pending: INQUIRIES.filter((i) => i.status === 'pending').length,
    responded: INQUIRIES.filter((i) => i.status === 'responded').length,
    confirmed: INQUIRIES.filter((i) => i.status === 'confirmed').length,
    declined: INQUIRIES.filter((i) => i.status === 'declined').length,
  };

  return (
    <div className="planner-layout">
      <aside className="planner-sidebar">
        <Link to="/" className="planner-sidebar-logo">
          <span>prasang</span>
          <span className="planner-sidebar-logo-hindi">प्रसंग</span>
        </Link>
        <nav className="planner-sidebar-nav">
          <Link to="/planner/dashboard" className="planner-sidebar-link">
            <LayoutDashboard size={18} /> Dashboard
          </Link>
          <Link to="/planner/inquiries" className="planner-sidebar-link active">
            <MessageCircle size={18} /> My Inquiries
          </Link>
          <Link to="/planner/saved" className="planner-sidebar-link">
            <Heart size={18} /> Saved Artists
          </Link>
          <Link to="/search" className="planner-sidebar-link">
            <Search size={18} /> Browse Artists
          </Link>
        </nav>
        <div className="planner-promo-card">
          <div className="planner-promo-title">Looking for more artists?</div>
          <div className="planner-promo-note">Search magicians, DJs, singers and more near you.</div>
          <Link to="/search" className="planner-promo-btn">
            Browse Artists <ChevronRight size={14} />
          </Link>
        </div>
      </aside>

      <main className="planner-main">
        <header className="planner-topbar">
          <div>
            <h1 className="planner-page-title">My Inquiries</h1>
            <p className="planner-page-sub">Artists you've reached out to for your events</p>
          </div>
        </header>

        <div className="planner-filter-tabs">
          {(['all', 'pending', 'responded', 'confirmed', 'declined'] as FilterStatus[]).map((s) => (
            <button
              key={s}
              className={`planner-filter-tab${filter === s ? ' active' : ''}`}
              onClick={() => setFilter(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
              <span className="planner-tab-count">{counts[s]}</span>
            </button>
          ))}
        </div>

        <div className="planner-inquiry-cards">
          {filtered.length === 0 && (
            <div className="planner-inquiries-empty">No inquiries in this category yet.</div>
          )}
          {filtered.map((inquiry) => {
            const artist = mockArtists.find((a) => a.artistId === inquiry.artistId);
            if (!artist) return null;
            return (
              <div key={inquiry.id} className="planner-inquiry-card">
                <div className="planner-inquiry-card-top">
                  <div className="planner-inquiry-card-left">
                    <img src={artist.profileImageUrl} alt={artist.name} className="planner-inquiry-card-avatar" />
                    <div>
                      <div className="planner-inquiry-card-name">{artist.name}</div>
                      <div className="planner-inquiry-card-meta">
                        <span><Calendar size={12} /> {inquiry.eventDate}</span>
                        <span><MapPin size={12} /> {artist.locationArea}, {artist.locationCity}</span>
                      </div>
                    </div>
                  </div>
                  <div className="planner-inquiry-card-right">
                    <span
                      className="planner-status-badge"
                      style={{ background: `${STATUS_COLORS[inquiry.status]}20`, color: STATUS_COLORS[inquiry.status] }}
                    >
                      {inquiry.status}
                    </span>
                    <span className="planner-inquiry-time">{inquiry.contactedAt}</span>
                  </div>
                </div>

                <div className="planner-inquiry-card-event">
                  <span className="planner-inquiry-event-type">{inquiry.event} · {ARTIST_TYPE_LABELS[artist.artistType]}</span>
                  <span className="planner-inquiry-budget">
                    <IndianRupee size={12} />
                    {(inquiry.budgetMin / 1000).toFixed(0)}k – {(inquiry.budgetMax / 1000).toFixed(0)}k
                  </span>
                </div>

                {expanded === inquiry.id && (
                  <div className="planner-inquiry-card-expanded">
                    <div className="planner-inquiry-notes">{inquiry.notes}</div>
                    <Link to={`/profile/${artist.slug}`} className="planner-inquiry-view-profile-btn">
                      <ExternalLink size={15} /> View Profile
                    </Link>
                  </div>
                )}

                <button
                  className="planner-inquiry-expand-btn"
                  onClick={() => setExpanded(expanded === inquiry.id ? null : inquiry.id)}
                >
                  {expanded === inquiry.id ? 'Hide details' : 'View details'}
                  <ChevronDown
                    size={14}
                    style={{ transform: expanded === inquiry.id ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
                  />
                </button>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
