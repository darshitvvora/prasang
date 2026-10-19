import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Crown, Phone, Calendar, MapPin, IndianRupee, ChevronDown, Lock } from 'lucide-react';
import ArtistSidebar from '../../components/ArtistSidebar';
import QueryState, { InlineError } from '../../components/QueryState';
import { useArtistLeads, useUpdateLead } from '../../api/queries';
import { formatDate, relativeTime } from '../../api/format';
import type { ArtistLead } from '../../api/types';
import type { LeadStatus } from '../../types/artist';
import { leadBanner } from './planUsage';
import './ArtistPages.css';

type Filter = 'all' | LeadStatus;
const FILTERS: Filter[] = ['all', 'new', 'contacted', 'converted', 'declined', 'expired'];

const STATUS_COLORS: Record<LeadStatus, string> = {
  new: '#d4f53f',
  contacted: '#60a5fa',
  converted: '#4ade80',
  declined: '#f87171',
  expired: '#666',
};

const budgetK = (min: number, max: number | null) => `${(min / 1000).toFixed(0)}k${max === null ? '+' : ` – ${(max / 1000).toFixed(0)}k`}`;

function LeadCard({ lead }: { lead: ArtistLead }) {
  const [expanded, setExpanded] = useState(false);
  const update = useUpdateLead();
  const setStatus = (status: 'contacted' | 'converted' | 'declined') => update.mutate({ id: lead.id, status });
  const phone = lead.plannerPhone;

  return (
    <div className={`lead-card${lead.isLocked ? ' locked' : ''}`}>
      <div className="lead-card-top">
        <div className="lead-card-left">
          <div className="lead-card-avatar">{lead.plannerName[0]}</div>
          <div>
            <div className="lead-card-name">{lead.plannerName}</div>
            <div className="lead-card-meta">
              {lead.eventDate && <span><Calendar size={12} /> {formatDate(lead.eventDate)}</span>}
              {lead.eventCity && <span><MapPin size={12} /> {lead.eventCity}</span>}
            </div>
          </div>
        </div>
        <div className="lead-card-right">
          <span className="lead-status-badge" style={{ background: `${STATUS_COLORS[lead.status]}20`, color: STATUS_COLORS[lead.status] }}>
            {lead.status}
          </span>
          <span className="lead-time">{relativeTime(lead.createdAt)}</span>
        </div>
      </div>

      <div className="lead-card-event">
        <span className="lead-event-type">{lead.eventTitle}</span>
        <span className="lead-budget"><IndianRupee size={12} />{budgetK(lead.budgetMin, lead.budgetMax)}</span>
      </div>

      {lead.isLocked ? (
        <div className="lead-locked-note">
          <Lock size={14} /> You've reached this month's lead limit. <Link to="/pricing">Upgrade</Link> to see this planner's details.
        </div>
      ) : (
        <>
          {expanded && (
            <div className="lead-card-expanded">
              {lead.notes && <div className="lead-notes">{lead.notes}</div>}
              {phone && (
                <div className="lead-actions">
                  <a href={`tel:+91${phone}`} className="lead-action-btn phone" onClick={() => lead.status === 'new' && setStatus('contacted')}>
                    <Phone size={15} /> Call
                  </a>
                  <a href={`https://wa.me/91${phone}`} target="_blank" rel="noreferrer" className="lead-action-btn whatsapp"
                    onClick={() => lead.status === 'new' && setStatus('contacted')}>
                    WhatsApp
                  </a>
                  <span className="lead-phone-reveal">+91 {phone}</span>
                </div>
              )}
              {lead.plannerEmail && <div className="lead-notes">✉️ {lead.plannerEmail}</div>}
              <div className="lead-status-actions">
                {lead.status === 'new' && <button className="lead-status-btn" disabled={update.isPending} onClick={() => setStatus('contacted')}>Mark contacted</button>}
                {(lead.status === 'new' || lead.status === 'contacted') && (
                  <>
                    <button className="lead-status-btn primary" disabled={update.isPending} onClick={() => setStatus('converted')}>Mark booked</button>
                    <button className="lead-status-btn" disabled={update.isPending} onClick={() => setStatus('declined')}>Decline</button>
                  </>
                )}
              </div>
              <InlineError error={update.error} />
            </div>
          )}
          <button className="lead-expand-btn" onClick={() => setExpanded(!expanded)}>
            {expanded ? 'Hide details' : 'View details'}
            <ChevronDown size={14} style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
          </button>
        </>
      )}
    </div>
  );
}

export default function LeadsPage() {
  const [filter, setFilter] = useState<Filter>('all');
  const leads = useArtistLeads(filter);
  const banner = leads.data ? leadBanner(leads.data.plan) : null;

  return (
    <div className="artist-layout">
      <ArtistSidebar active="leads" />

      <main className="artist-main">
        <header className="artist-topbar">
          <div>
            <h1 className="artist-page-title">Leads</h1>
            <p className="artist-page-sub">Event planners who want to book you</p>
          </div>
        </header>

        {banner && (
          <div className="upgrade-banner">
            <Crown size={20} className="upgrade-icon" />
            <div className="upgrade-text"><strong>{banner.strong}</strong> {banner.rest}</div>
            <Link to="/pricing" className="upgrade-btn">Upgrade</Link>
          </div>
        )}

        <div className="leads-filter-tabs">
          {FILTERS.map((s) => (
            <button key={s} className={`leads-filter-tab${filter === s ? ' active' : ''}`} onClick={() => setFilter(s)}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
              {leads.data && <span className="tab-count">{leads.data.counts[s]}</span>}
            </button>
          ))}
        </div>

        <QueryState query={leads} isEmpty={(d) => d.items.length === 0} empty={<div className="leads-empty">No leads in this category yet.</div>}>
          {(data) => (
            <div className="leads-cards">
              {data.items.map((lead) => <LeadCard key={lead.id} lead={lead} />)}
            </div>
          )}
        </QueryState>
      </main>
    </div>
  );
}
