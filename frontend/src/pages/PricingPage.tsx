import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Check, X, Crown, Zap, Sparkles } from 'lucide-react';
import Navbar from '../components/Navbar';
import QueryState, { InlineError } from '../components/QueryState';
import { useAuth } from '../auth/AuthProvider';
import { useCreateSubscription, useMySubscription, usePlans, useVerifyPayment } from '../api/queries';
import { getDowngradePreview } from '../api/endpoints';
import { downgradeWarning } from './pricing/downgrade';

const TIER_ORDER: SubscriptionTier[] = ['free', 'pro', 'premium'];
import type { CreateSubscriptionResponse, Plan, VerifyPaymentResponse } from '../api/types';
import type { SubscriptionTier } from '../types/artist';
import { isMockLink } from '../payments/paymentLink';
import PaymentLinkPanel from '../payments/PaymentLinkPanel';
import { pricingCta } from './pricing/pricingCta';
import './PricingPage.css';

const TIER_STYLE: Record<SubscriptionTier, { icon: React.ReactNode; color: string }> = {
  free: { icon: <Zap size={22} />, color: '#60a5fa' }, // the Basic plan
  pro: { icon: <Crown size={22} />, color: 'var(--color-accent)' },
  premium: { icon: <Sparkles size={22} />, color: '#a78bfa' },
};

function FeatureValue({ value }: { value: string | boolean | undefined }) {
  if (value === true) return <Check size={18} className="feat-check" />;
  if (value === false || value === undefined) return <X size={16} className="feat-x" />;
  return <span className="feat-text">{value}</span>;
}

export default function PricingPage() {
  const [annual, setAnnual] = useState(true);
  const { user } = useAuth();
  const navigate = useNavigate();
  const plansQuery = usePlans();
  const isArtist = user?.role === 'artist';
  const subscription = useMySubscription(isArtist);
  const createSubscription = useCreateSubscription();
  const verifyPayment = useVerifyPayment();
  const [busyTier, setBusyTier] = useState<SubscriptionTier | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [pending, setPending] = useState<(CreateSubscriptionResponse & { label: string }) | null>(null);

  const plans = plansQuery.data?.items ?? [];
  const allFeatures = [...new Set(plans.flatMap((p) => p.features.map((f) => f.label)))];
  const featureOf = (p: Plan, label: string) => p.features.find((f) => f.label === label)?.value;

  function paid(result: VerifyPaymentResponse) {
    setPending(null);
    setSuccess(`You're on ${result.plan.name}! Your profile now gets ${result.plan.name} placement.`);
  }

  async function subscribe(tier: Exclude<SubscriptionTier, 'free'>) {
    setBusyTier(tier);
    setError(null);
    setSuccess(null);
    setPending(null);
    try {
      const current = subscription.data?.plan.tier;
      if (current && TIER_ORDER.indexOf(tier) < TIER_ORDER.indexOf(current)) {
        const warning = downgradeWarning(await getDowngradePreview(tier));
        if (warning && !window.confirm(`${warning}\n\nContinue?`)) return;
      }
      const created = await createSubscription.mutateAsync({ tier, billingCycle: annual ? 'annual' : 'monthly' });
      if (isMockLink(created.payment.url)) { // local fake gateway / Mockoon: nothing to pay
        const result = await verifyPayment.mutateAsync({ subscriptionId: created.subscriptionId });
        if (result.status === 'active') return paid(result);
      }
      const planName = plans.find((p) => p.tier === tier)?.name ?? tier;
      setPending({ ...created, label: `${planName} (${annual ? 'yearly' : 'monthly'})` });
    } catch (e) {
      setError(e);
    } finally {
      setBusyTier(null);
    }
  }

  function renderCta(plan: Plan) {
    const cta = pricingCta(plan.tier, user, subscription.data?.plan);
    const cls = `plan-cta${plan.popular ? ' primary' : ''}`;
    if (cta.kind === 'link') return <Link to={cta.to} className={cls}>{cta.label}</Link>;
    if (cta.kind === 'current') return <span className={`${cls} current`}>{cta.label}</span>;
    if (cta.kind === 'subscribe' && plan.tier !== 'free') {
      const tier = plan.tier;
      return (
        <button type="button" className={cls} disabled={busyTier !== null} onClick={() => subscribe(tier)}>
          {busyTier === tier ? 'Creating payment link…' : cta.label}
        </button>
      );
    }
    return null;
  }

  return (
    <div className="pricing-page">
      <Navbar />

      <div className="pricing-hero">
        <p className="pricing-eyebrow">Simple pricing</p>
        <h1 className="pricing-title">
          Grow your bookings.<br />
          Pay only for what you need.
        </h1>
        <p className="pricing-subtitle">
          Join 12,500+ artists across India. Cancel anytime.
        </p>

        {/* Billing toggle */}
        <div className="pricing-toggle">
          <button
            className={`toggle-btn${!annual ? ' active' : ''}`}
            onClick={() => setAnnual(false)}
          >
            Monthly
          </button>
          <button
            className={`toggle-btn${annual ? ' active' : ''}`}
            onClick={() => setAnnual(true)}
          >
            Annual
            <span className="toggle-save">Save ~17%</span>
          </button>
        </div>
      </div>

      {success && (
        <div className="pricing-status success" role="status">
          {success} <button type="button" onClick={() => navigate('/artist/dashboard')}>Go to dashboard →</button>
        </div>
      )}
      <div className="pricing-status-error"><InlineError error={error} /></div>
      {pending && (
        <PaymentLinkPanel subscriptionId={pending.subscriptionId} payment={pending.payment} onPaid={paid}
          title={`Pay for ${pending.label} — your plan starts as soon as PhonePe confirms.`} />
      )}

      {/* Pricing cards */}
      <QueryState query={plansQuery}>
        {() => (
      <div className="pricing-grid">
        {plans.map((plan) => {
          const price = annual ? plan.annualMonthlyEquivalent : plan.monthlyPrice;
          const style = TIER_STYLE[plan.tier];

          return (
            <div key={plan.tier} className={`pricing-card${plan.popular ? ' popular' : ''}`}>
              {plan.popular && <div className="popular-badge">Most Popular</div>}

              <div className="plan-header">
                <span className="plan-icon" style={{ color: style.color }}>{style.icon}</span>
                <div>
                  <div className="plan-name">{plan.name}</div>
                  <div className="plan-tagline">{plan.tagline}</div>
                </div>
              </div>

              <div className="plan-price">
                {price === 0 ? (
                  <span className="price-amount">Free</span>
                ) : (
                  <>
                    <span className="price-currency">₹</span>
                    <span className="price-amount">{price}</span>
                    <span className="price-period">/mo</span>
                  </>
                )}
                {annual && price > 0 && (
                  <span className="price-note">billed ₹{plan.annualPrice.toLocaleString('en-IN')}/year</span>
                )}
              </div>

              {renderCta(plan)}

              <ul className="plan-features">
                {plan.features.map((f) => {
                  if (f.value === false) return null;
                  return (
                    <li key={f.label} className="plan-feature-item">
                      <Check size={15} className="feat-check-sm" />
                      <span className="feat-name">{f.label}</span>
                      {typeof f.value === 'string' && <span className="feat-val">{f.value}</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
        )}
      </QueryState>

      {/* Comparison table */}
      <div className="comparison-section">
        <h2 className="comparison-title">Full comparison</h2>
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr>
                <th className="col-feature">Features</th>
                {plans.map((p) => (
                  <th key={p.tier} className={`col-plan${p.popular ? ' col-popular' : ''}`}>
                    <span style={{ color: TIER_STYLE[p.tier].color }}>{p.name}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {allFeatures.map((feat) => (
                <tr key={feat}>
                  <td className="feat-row-label">{feat}</td>
                  {plans.map((p) => (
                    <td key={p.tier} className={`feat-row-val${p.popular ? ' col-popular' : ''}`}>
                      <FeatureValue value={featureOf(p, feat)} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* FAQ */}
      <div className="pricing-faq">
        <h2 className="faq-title">Frequently asked questions</h2>
        <div className="faq-grid">
          {[
            { q: 'Can I change plans later?', a: 'Yes! Switch anytime — the new plan starts the day you pay for it and replaces the old one.' },
            { q: 'Is there a free trial for paid plans?', a: 'All paid plans come with a 7-day free trial. No credit card required to start.' },
            { q: 'How do buyers contact me?', a: 'Buyers submit their event details and we reveal your contact info to them. You also get instant WhatsApp notifications on Pro & Premium.' },
            { q: 'What payment methods do you accept?', a: 'UPI, credit/debit cards and net banking through PhonePe. No auto-debit: we email and text you a payment link a few days before each renewal.' },
          ].map((item) => (
            <div key={item.q} className="faq-item">
              <div className="faq-q">{item.q}</div>
              <div className="faq-a">{item.a}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="pricing-bottom-cta">
        <h2>Ready to get more bookings?</h2>
        <p>Start free. Upgrade when you're ready.</p>
        <Link to={isArtist ? '/artist/onboarding' : '/signup?role=artist'} className="pricing-bottom-btn">{isArtist ? 'Edit your profile →' : 'Create your profile →'}</Link>
      </div>
    </div>
  );
}
