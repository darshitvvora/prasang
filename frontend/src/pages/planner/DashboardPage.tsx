import { Link } from 'react-router-dom';
import { LayoutDashboard, MessageCircle, CheckCircle2, Calendar, ChevronRight, Search, Star } from 'lucide-react';
import { mockArtists } from '../../data/mockArtists';
import { INQUIRIES, STATUS_COLORS } from '../../data/mockPlannerActivity';
import { ARTIST_TYPE_LABELS } from '../../types/artist';
import './PlannerPages.css';

export default function DashboardPage() {
  const respondedCount = INQUIRIES.filter((i) => i.status === 'responded' || i.status === 'confirmed').length;
  const confirmedCount = INQUIRIES.filter((i) => i.status === 'confirmed').length;

  const upcoming = INQUIRIES
    .filter((i) => i.status !== 'declined' && i.daysToEvent >= 0)
    .sort((a, b) => a.daysToEvent - b.daysToEvent)[0];
  const upcomingArtist = upcoming ? mockArtists.find((a) => a.artistId === upcoming.artistId) : undefined;

  const recentInquiries = INQUIRIES.slice(0, 3);

  return (
    <div className="planner-layout">
      <aside className="planner-sidebar">
        <Link to="/" className="planner-sidebar-logo">
          <span>prasang</span>
          <span className="planner-sidebar-logo-hindi">प्रसंग</span>
        </Link>

        <nav className="planner-sidebar-nav">
          <Link to="/planner/dashboard" className="planner-sidebar-link active">
            <LayoutDashboard size={18} /> Dashboard
          </Link>
          <Link to="/planner/inquiries" className="planner-sidebar-link">
            <MessageCircle size={18} /> My Inquiries
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
            <h1 className="planner-page-title">Dashboard</h1>
            <p className="planner-page-sub">Track the artists you've reached out to</p>
          </div>
          <Link to="/search" className="planner-topbar-cta">
            <Search size={16} /> Browse Artists
          </Link>
        </header>

        <div className="planner-metrics-grid">
          <div className="planner-metric-card">
            <div className="planner-metric-header">
              <span className="planner-metric-label">Artists Contacted</span>
              <span className="planner-metric-icon"><MessageCircle size={20} /></span>
            </div>
            <div className="planner-metric-value">{INQUIRIES.length}</div>
          </div>
          <div className="planner-metric-card">
            <div className="planner-metric-header">
              <span className="planner-metric-label">Responses Received</span>
              <span className="planner-metric-icon"><Star size={20} /></span>
            </div>
            <div className="planner-metric-value">{respondedCount}</div>
          </div>
          <div className="planner-metric-card">
            <div className="planner-metric-header">
              <span className="planner-metric-label">Confirmed Bookings</span>
              <span className="planner-metric-icon"><CheckCircle2 size={20} /></span>
            </div>
            <div className="planner-metric-value">{confirmedCount}</div>
          </div>
        </div>

        {upcoming && upcomingArtist ? (
          <div className="planner-upcoming-card">
            <div className="planner-upcoming-icon"><Calendar size={20} /></div>
            <div className="planner-upcoming-info">
              <div className="planner-upcoming-title">{upcoming.event} with {upcomingArtist.name}</div>
              <div className="planner-upcoming-sub">{upcoming.eventDate}</div>
            </div>
            <div className="planner-upcoming-days">{upcoming.daysToEvent}d to go</div>
          </div>
        ) : (
          <div className="planner-upcoming-card">
            <div className="planner-upcoming-icon"><Calendar size={20} /></div>
            <div className="planner-upcoming-empty">No upcoming events yet — browse artists to plan your next one.</div>
          </div>
        )}

        <div className="planner-dashboard-row">
          <div className="planner-dashboard-card">
            <div className="planner-card-header">
              <h2 className="planner-card-title">Recent Inquiries</h2>
              <Link to="/planner/inquiries" className="planner-card-action">View all <ChevronRight size={14} /></Link>
            </div>
            {recentInquiries.length === 0 ? (
              <p className="planner-empty-note">You haven't contacted any artists yet.</p>
            ) : (
              <div className="planner-inquiry-preview-list">
                {recentInquiries.map((inquiry) => {
                  const artist = mockArtists.find((a) => a.artistId === inquiry.artistId);
                  if (!artist) return null;
                  return (
                    <div key={inquiry.id} className="planner-inquiry-preview-item">
                      <div className="planner-inquiry-avatar">
                        <img src={artist.profileImageUrl} alt={artist.name} />
                      </div>
                      <div className="planner-inquiry-info">
                        <div className="planner-inquiry-name">{artist.name}</div>
                        <div className="planner-inquiry-event">{inquiry.event} · {inquiry.eventDate}</div>
                      </div>
                      <span
                        className="planner-status-badge"
                        style={{ background: `${STATUS_COLORS[inquiry.status]}20`, color: STATUS_COLORS[inquiry.status] }}
                      >
                        {inquiry.status}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
