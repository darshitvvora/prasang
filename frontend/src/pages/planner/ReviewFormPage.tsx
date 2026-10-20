import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Star } from 'lucide-react';
import PlannerSidebar from '../../components/PlannerSidebar';
import QueryState from '../../components/QueryState';
import { useCreateReview, usePlannerInquiries } from '../../api/queries';
import { ApiError } from '../../api/client';
import type { PlannerInquiry } from '../../api/types';
import { validateReview, type ReviewErrors } from '../reviewForm';
import './PlannerPages.css';

function ReviewForm({ inquiry }: { inquiry: PlannerInquiry }) {
  const create = useCreateReview();
  const navigate = useNavigate();
  const [rating, setRating] = useState(0);
  const [text, setText] = useState('');
  const [errors, setErrors] = useState<ReviewErrors>({});

  if (inquiry.reviewId) return <p>You've already reviewed this booking. Thank you!</p>;
  if (!inquiry.canReview) return <p>You can review {inquiry.artist.name} once the booking is confirmed and the event is over.</p>;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const found = validateReview({ rating, text });
    setErrors(found);
    if (Object.keys(found).length) return;
    create.mutate({ leadId: inquiry.id, rating, text: text.trim() }, { onSuccess: () => navigate(`/profile/${inquiry.artist.slug}`) });
  };
  const serverError = create.error instanceof ApiError ? create.error.message : create.error ? 'Something went wrong. Please try again.' : null;

  return (
    <form className="review-form" onSubmit={submit} noValidate>
      <p>How was {inquiry.artist.name} at your {inquiry.eventTitle.toLowerCase()}?</p>
      <div className="review-form-stars" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" role="radio" aria-checked={rating === n} aria-label={`${n} star${n > 1 ? 's' : ''}`}
            className={n <= rating ? 'on' : ''} onClick={() => setRating(n)}>
            <Star size={28} fill={n <= rating ? 'currentColor' : 'none'} />
          </button>
        ))}
      </div>
      {errors.rating && <span className="review-form-error">{errors.rating}</span>}
      <label>Your review
        <textarea rows={6} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)}
          placeholder="What did guests love? Was the artist on time and easy to work with?" />
        <span className="review-form-count">{text.trim().length}/2000</span>
      </label>
      {errors.text && <span className="review-form-error">{errors.text}</span>}
      {serverError && <p className="review-form-error" role="alert">{serverError}</p>}
      <button type="submit" className="review-form-submit" disabled={create.isPending}>
        {create.isPending ? 'Posting…' : 'Post review'}
      </button>
    </form>
  );
}

export default function ReviewFormPage() {
  const { id = '' } = useParams();
  const inquiries = usePlannerInquiries('all');
  return (
    <div className="planner-layout">
      <PlannerSidebar active="inquiries" />
      <main className="planner-main">
        <header className="planner-topbar">
          <div>
            <h1 className="planner-page-title">Write a review</h1>
            <p className="planner-page-sub"><Link to="/planner/inquiries">Back to my inquiries</Link></p>
          </div>
        </header>
        <QueryState query={inquiries}>
          {(data) => {
            const inquiry = data.items.find((i) => i.id === id);
            return inquiry ? <ReviewForm inquiry={inquiry} /> : <p>We couldn't find that inquiry.</p>;
          }}
        </QueryState>
      </main>
    </div>
  );
}
