import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Calendar, ChevronDown, ExternalLink, IndianRupee } from 'lucide-react';
import PlannerSidebar from '../../components/PlannerSidebar';
import QueryState from '../../components/QueryState';
import { useAnswerInquiry, usePlannerInquiries } from '../../api/queries';
import { afterAnswer, inquiryActions } from './bookingAnswer';
import { formatDate, imageOr, relativeTime } from '../../api/format';
import type { PlannerInquiry } from '../../api/types';
import type { InquiryStatus } from '../../types/artist';
import { ARTIST_TYPE_LABELS } from '../../types/artist';
import { STATUS_COLORS } from './plannerStatus';
import './PlannerPages.css';

type FilterStatus = 'all' | InquiryStatus;
const FILTERS: FilterStatus[] = ['all', 'pending', 'responded', 'confirmed', 'declined'];
const budgetK = (min: number, max: number | null) => `${(min / 1000).toFixed(0)}k${max === null ? '+' : ` – ${(max / 1000).toFixed(0)}k`}`;

function BookingBar({ inquiry }: { inquiry: PlannerInquiry }) {
  const answer = useAnswerInquiry();
  const navigate = useNavigate();
  const actions = inquiryActions(inquiry);
  const send = (value: 'booked' | 'not_booked' | 'deciding') => answer.mutate({ id: inquiry.id, answer: value }, {
    onSuccess: (updated) => { if (afterAnswer(updated) === 'review') navigate(`/planner/inquiries/${inquiry.id}/review`); },
  });
  return (
    <div className="planner-booking-bar">
      {actions.label && <span className="planner-booking-label">{actions.label}</span>}
      {actions.ask && (
        <div className="planner-booking-question">
          <span>Did you book {inquiry.artist.name}?</span>
          <button type="button" disabled={answer.isPending} onClick={() => send('booked')}>Yes, booked</button>
          <button type="button" disabled={answer.isPending} onClick={() => send('not_booked')}>No</button>
          {inquiry.plannerAnswer !== 'deciding' && (
            <button type="button" disabled={answer.isPending} onClick={() => send('deciding')}>Still deciding</button>
          )}
        </div>
      )}
      {actions.review === 'write' && (
        <Link to={`/planner/inquiries/${inquiry.id}/review`} className="planner-booking-review">Write a review</Link>
      )}
      {actions.review === 'after-event' && <span className="planner-booking-hint">You can review after the event.</span>}
      {actions.review === 'written' && <span className="planner-booking-hint">Thanks for your review!</span>}
      {answer.isError && <span className="planner-booking-error">Couldn't save that. Please try again.</span>}
    </div>
  );
}

function InquiryCard({ inquiry }: { inquiry: PlannerInquiry }) {
  const [expanded, setExpanded] = useState(false);
  const { artist } = inquiry;
  return (
    <div className="planner-inquiry-card">
      <div className="planner-inquiry-card-top">
        <div className="planner-inquiry-card-left">
          <img src={imageOr(artist.profileImageUrl)} alt={artist.name} className="planner-inquiry-card-avatar" />
          <div>
            <div className="planner-inquiry-card-name">{artist.name}</div>
            <div className="planner-inquiry-card-meta">
              {inquiry.eventDate && <span><Calendar size={12} /> {formatDate(inquiry.eventDate)}</span>}
            </div>
          </div>
        </div>
        <div className="planner-inquiry-card-right">
          <span className="planner-status-badge" style={{ background: `${STATUS_COLORS[inquiry.status]}20`, color: STATUS_COLORS[inquiry.status] }}>
            {inquiry.status}
          </span>
          <span className="planner-inquiry-time">{relativeTime(inquiry.contactedAt)}</span>
        </div>
      </div>

      <div className="planner-inquiry-card-event">
        <span className="planner-inquiry-event-type">{inquiry.eventTitle} · {ARTIST_TYPE_LABELS[artist.artistType]}</span>
        <span className="planner-inquiry-budget"><IndianRupee size={12} />{budgetK(inquiry.budgetMin, inquiry.budgetMax)}</span>
      </div>

      <BookingBar inquiry={inquiry} />

      {expanded && (
        <div className="planner-inquiry-card-expanded">
          {inquiry.notes && <div className="planner-inquiry-notes">{inquiry.notes}</div>}
          <Link to={`/profile/${artist.slug}`} className="planner-inquiry-view-profile-btn">
            <ExternalLink size={15} /> View Profile
          </Link>
        </div>
      )}

      <button className="planner-inquiry-expand-btn" onClick={() => setExpanded(!expanded)}>
        {expanded ? 'Hide details' : 'View details'}
        <ChevronDown size={14} style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
      </button>
    </div>
  );
}

export default function InquiriesPage() {
  const [filter, setFilter] = useState<FilterStatus>('all');
  const inquiries = usePlannerInquiries(filter);

  return (
    <div className="planner-layout">
      <PlannerSidebar active="inquiries" />

      <main className="planner-main">
        <header className="planner-topbar">
          <div>
            <h1 className="planner-page-title">My Inquiries</h1>
            <p className="planner-page-sub">Artists you've reached out to for your events</p>
          </div>
        </header>

        <div className="planner-filter-tabs">
          {FILTERS.map((s) => (
            <button key={s} className={`planner-filter-tab${filter === s ? ' active' : ''}`} onClick={() => setFilter(s)}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
              {inquiries.data && <span className="planner-tab-count">{inquiries.data.counts[s]}</span>}
            </button>
          ))}
        </div>

        <QueryState query={inquiries} isEmpty={(d) => d.items.length === 0}
          empty={<div className="planner-inquiries-empty">No inquiries in this category yet.</div>}>
          {(data) => (
            <div className="planner-inquiry-cards">
              {data.items.map((inquiry) => <InquiryCard key={inquiry.id} inquiry={inquiry} />)}
            </div>
          )}
        </QueryState>
      </main>
    </div>
  );
}
