import { useState } from 'react';
import ArtistSidebar from '../../components/ArtistSidebar';
import QueryState from '../../components/QueryState';
import { useMyReviews, useReplyToReview, useReportReview } from '../../api/queries';
import type { Review } from '../../api/types';
import { validateReply, validateReport } from '../reviewForm';
import './ArtistPages.css';

function ReviewItem({ review }: { review: Review }) {
  const replyMut = useReplyToReview();
  const reportMut = useReportReview();
  const [mode, setMode] = useState<'none' | 'reply' | 'report'>('none');
  const [text, setText] = useState(review.artistReply ?? '');
  const [error, setError] = useState<string | null>(null);

  const submit = () => {
    const problem = mode === 'reply' ? validateReply(text) : validateReport(text);
    setError(problem);
    if (problem) return;
    const done = { onSuccess: () => setMode('none') };
    if (mode === 'reply') replyMut.mutate({ id: review.id, text: text.trim() }, done);
    else reportMut.mutate({ id: review.id, reason: text.trim() }, done);
  };

  return (
    <div className="artist-review-item">
      <div className="artist-review-head">
        <strong>{review.reviewerName}</strong> · {'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}
        {review.verified && <span className="artist-review-verified">Booked via Prasang</span>}
      </div>
      <p>{review.text}</p>
      {review.artistReply && mode !== 'reply' && <p className="artist-review-reply"><strong>Your reply:</strong> {review.artistReply}</p>}
      {reportMut.isSuccess && <p className="artist-review-note">Thanks — we'll look into this review.</p>}
      {mode === 'none' ? (
        <div className="artist-review-actions">
          <button type="button" onClick={() => { setText(review.artistReply ?? ''); setError(null); setMode('reply'); }}>
            {review.artistReply ? 'Edit reply' : 'Reply'}
          </button>
          {!reportMut.isSuccess && (
            <button type="button" onClick={() => { setText(''); setError(null); setMode('report'); }}>Report</button>
          )}
        </div>
      ) : (
        <div className="artist-review-editor">
          <textarea rows={3} maxLength={1000} value={text} onChange={(e) => setText(e.target.value)}
            placeholder={mode === 'reply' ? 'Thank the planner or add context — everyone can see this.' : 'Why should Prasang look at this review?'} />
          {error && <span className="artist-review-error">{error}</span>}
          <div className="artist-review-actions">
            <button type="button" onClick={submit} disabled={replyMut.isPending || reportMut.isPending}>
              {mode === 'reply' ? 'Post reply' : 'Send report'}
            </button>
            <button type="button" onClick={() => setMode('none')}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ReviewsPage() {
  const reviews = useMyReviews();
  return (
    <div className="artist-layout">
      <ArtistSidebar active="reviews" />
      <main className="artist-main">
        <header className="artist-topbar">
          <div>
            <h1 className="artist-page-title">Reviews</h1>
            <p className="artist-page-sub">Reviews from planners who booked you. Reply publicly or report one to us.</p>
          </div>
        </header>
        <QueryState query={reviews} isEmpty={(d) => d.items.length === 0} empty={<p>No reviews yet.</p>}>
          {(data) => <div className="subscription-card">{data.items.map((r) => <ReviewItem key={r.id} review={r} />)}</div>}
        </QueryState>
      </main>
    </div>
  );
}
