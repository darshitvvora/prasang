import { useState } from 'react';
import { Link } from 'react-router-dom';
import ArtistSidebar from '../../components/ArtistSidebar';
import QueryState from '../../components/QueryState';
import { useCancelSubscription, useMyPayments, useMySubscription } from '../../api/queries';
import { formatDate } from '../../api/format';
import type { MySubscriptionResponse } from '../../api/types';
import { formatBillingRow } from './billing';
import './ArtistPages.css';

function PlanCard({ data }: { data: MySubscriptionResponse }) {
  const cancel = useCancelSubscription();
  const [confirming, setConfirming] = useState(false);
  const { plan, subscription } = data;
  const canCancel = subscription?.status === 'active' && !subscription.cancelAtPeriodEnd;
  return (
    <div className="subscription-card">
      <h2 className="subscription-plan-name">{plan.name} plan</h2>
      {plan.status === 'trial' && plan.trialEndsAt && <p>Free trial until {formatDate(plan.trialEndsAt)}.</p>}
      {plan.status === 'active' && plan.periodEnd && <p>Renews or ends on {formatDate(plan.periodEnd)}.</p>}
      {plan.status === 'cancelling' && plan.periodEnd && <p>Cancelled — you keep this plan until {formatDate(plan.periodEnd)}.</p>}
      {plan.status === 'halted' && <p className="subscription-warning">Your last payment failed. Update your payment method with Razorpay to keep this plan.</p>}
      {plan.status === 'free' && <p>You're on the Free plan. <Link to="/pricing">See paid plans</Link>.</p>}
      <div className="subscription-actions">
        <Link to="/pricing" className="topbar-view-profile">Change plan</Link>
        {canCancel && !confirming && (
          <button type="button" className="subscription-cancel" onClick={() => setConfirming(true)}>Cancel at period end</button>
        )}
      </div>
      {confirming && (
        <div className="subscription-confirm" role="dialog" aria-label="Cancel plan">
          <p>You'll keep {plan.name} until the end of this billing period, then move to Free. Cancel?</p>
          <button type="button" className="subscription-cancel" disabled={cancel.isPending}
            onClick={() => cancel.mutate(undefined, { onSuccess: () => setConfirming(false) })}>
            {cancel.isPending ? 'Cancelling…' : 'Yes, cancel'}
          </button>
          <button type="button" className="subscription-keep" onClick={() => setConfirming(false)}>Keep my plan</button>
          {cancel.isError && <p className="subscription-warning">Couldn't cancel right now. Please try again.</p>}
        </div>
      )}
    </div>
  );
}

function BillingHistory() {
  const payments = useMyPayments();
  return (
    <section className="subscription-card">
      <h2 className="subscription-plan-name">Billing history</h2>
      <QueryState query={payments}>
        {(data) => data.items.length === 0 ? <p>No payments yet.</p> : (
          <table className="billing-table">
            <thead><tr><th>Date</th><th>Plan</th><th>Amount</th><th>Status</th><th>Receipt</th></tr></thead>
            <tbody>
              {data.items.map((item) => {
                const row = formatBillingRow(item);
                return (
                  <tr key={item.id}>
                    <td>{row.date}</td><td>{row.plan}</td><td>{row.amount}</td>
                    <td className={item.status === 'failed' ? 'billing-failed' : undefined}>{row.status}</td>
                    <td>{row.receiptUrl ? <a href={row.receiptUrl} target="_blank" rel="noreferrer">Receipt</a> : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </QueryState>
    </section>
  );
}

export default function SubscriptionPage() {
  const sub = useMySubscription();
  return (
    <div className="artist-layout">
      <ArtistSidebar active="subscription" />
      <main className="artist-main">
        <header className="artist-topbar">
          <div>
            <h1 className="artist-page-title">My plan</h1>
            <p className="artist-page-sub">Your plan, renewals and receipts</p>
          </div>
        </header>
        <QueryState query={sub}>{(data) => <PlanCard data={data} />}</QueryState>
        <BillingHistory />
      </main>
    </div>
  );
}
