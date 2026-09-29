import { Link } from 'react-router-dom';
import { MessageCircle, CheckCircle2, Calendar, ChevronRight, Search, Star } from 'lucide-react';
import PlannerSidebar from '../../components/PlannerSidebar';
import QueryState from '../../components/QueryState';
import { usePlannerInquiries } from '../../api/queries';
import { formatDate, imageOr } from '../../api/format';
import { STATUS_COLORS } from './plannerStatus';
import './PlannerPages.css';

export default function DashboardPage() {
  const inquiries = usePlannerInquiries('all');

  return (
    <div className="planner-layout">
      <PlannerSidebar active="dashboard" />

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

        <QueryState query={inquiries}>
          {({ summary, items }) => (
            <>
              <div className="planner-metrics-grid">
                {[
                  { label: 'Artists Contacted', value: summary.artistsContacted, icon: <MessageCircle size={20} /> },
                  { label: 'Responses Received', value: summary.responsesReceived, icon: <Star size={20} /> },
                  { label: 'Confirmed Bookings', value: summary.confirmedBookings, icon: <CheckCircle2 size={20} /> },
                ].map((m) => (
                  <div key={m.label} className="planner-metric-card">
                    <div className="planner-metric-header">
                      <span className="planner-metric-label">{m.label}</span>
                      <span className="planner-metric-icon">{m.icon}</span>
                    </div>
                    <div className="planner-metric-value">{m.value}</div>
                  </div>
                ))}
              </div>

              <div className="planner-upcoming-card">
                <div className="planner-upcoming-icon"><Calendar size={20} /></div>
                {summary.upcoming ? (
                  <>
                    <div className="planner-upcoming-info">
                      <div className="planner-upcoming-title">{summary.upcoming.eventTitle} with {summary.upcoming.artistName}</div>
                      <div className="planner-upcoming-sub">{formatDate(summary.upcoming.eventDate)}</div>
                    </div>
                    <div className="planner-upcoming-days">
                      {summary.upcoming.daysToEvent === 0 ? 'Today' : `${summary.upcoming.daysToEvent}d to go`}
                    </div>
                  </>
                ) : (
                  <div className="planner-upcoming-empty">No upcoming events yet — browse artists to plan your next one.</div>
                )}
              </div>

              <div className="planner-dashboard-row">
                <div className="planner-dashboard-card">
                  <div className="planner-card-header">
                    <h2 className="planner-card-title">Recent Inquiries</h2>
                    <Link to="/planner/inquiries" className="planner-card-action">View all <ChevronRight size={14} /></Link>
                  </div>
                  {items.length === 0 ? (
                    <p className="planner-empty-note">You haven't contacted any artists yet.</p>
                  ) : (
                    <div className="planner-inquiry-preview-list">
                      {items.slice(0, 3).map((inquiry) => (
                        <Link key={inquiry.id} to={`/profile/${inquiry.artist.slug}`} className="planner-inquiry-preview-item">
                          <div className="planner-inquiry-avatar">
                            <img src={imageOr(inquiry.artist.profileImageUrl)} alt={inquiry.artist.name} />
                          </div>
                          <div className="planner-inquiry-info">
                            <div className="planner-inquiry-name">{inquiry.artist.name}</div>
                            <div className="planner-inquiry-event">
                              {inquiry.eventTitle}{inquiry.eventDate ? ` · ${formatDate(inquiry.eventDate)}` : ''}
                            </div>
                          </div>
                          <span className="planner-status-badge" style={{ background: `${STATUS_COLORS[inquiry.status]}20`, color: STATUS_COLORS[inquiry.status] }}>
                            {inquiry.status}
                          </span>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </QueryState>
      </main>
    </div>
  );
}
