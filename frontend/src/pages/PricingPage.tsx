import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, X, Crown, Zap, Star, Sparkles } from 'lucide-react';
import './PricingPage.css';

const PLANS = [
  {
    id: 'free',
    name: 'Free',
    icon: <Star size={22} />,
    monthlyPrice: 0,
    yearlyPrice: 0,
    tagline: 'Get started, get noticed',
    color: '#888',
    features: {
      'Profile listing': true,
      'Basic search visibility': true,
      'Contact leads per month': '3',
      'Media uploads': '5 photos',
      'Profile views shown': false,
      'Instagram / YouTube link': true,
      'Verified badge': false,
      'Featured in search': false,
      'Priority in search results': false,
      'Analytics dashboard': false,
      'WhatsApp lead notifications': false,
      'Custom portfolio link': false,
      'Priority support': false,
    },
  },
  {
    id: 'basic',
    name: 'Basic',
    icon: <Zap size={22} />,
    monthlyPrice: 299,
    yearlyPrice: 249,
    tagline: 'For artists just getting started',
    color: '#60a5fa',
    features: {
      'Profile listing': true,
      'Basic search visibility': true,
      'Contact leads per month': '15',
      'Media uploads': '20 photos + 3 videos',
      'Profile views shown': true,
      'Instagram / YouTube link': true,
      'Verified badge': true,
      'Featured in search': false,
      'Priority in search results': false,
      'Analytics dashboard': 'Basic',
      'WhatsApp lead notifications': true,
      'Custom portfolio link': false,
      'Priority support': false,
    },
  },
  {
    id: 'pro',
    name: 'Pro',
    icon: <Crown size={22} />,
    monthlyPrice: 599,
    yearlyPrice: 499,
    tagline: 'For growing artists',
    color: 'var(--color-accent)',
    popular: true,
    features: {
      'Profile listing': true,
      'Basic search visibility': true,
      'Contact leads per month': 'Unlimited',
      'Media uploads': '100 photos + 20 videos',
      'Profile views shown': true,
      'Instagram / YouTube link': true,
      'Verified badge': true,
      'Featured in search': true,
      'Priority in search results': true,
      'Analytics dashboard': 'Advanced',
      'WhatsApp lead notifications': true,
      'Custom portfolio link': true,
      'Priority support': false,
    },
  },
  {
    id: 'premium',
    name: 'Premium',
    icon: <Sparkles size={22} />,
    monthlyPrice: 1199,
    yearlyPrice: 999,
    tagline: 'For professionals who demand the best',
    color: '#a78bfa',
    features: {
      'Profile listing': true,
      'Basic search visibility': true,
      'Contact leads per month': 'Unlimited',
      'Media uploads': 'Unlimited',
      'Profile views shown': true,
      'Instagram / YouTube link': true,
      'Verified badge': true,
      'Featured in search': true,
      'Priority in search results': 'Top 3 placement',
      'Analytics dashboard': 'Full + Export',
      'WhatsApp lead notifications': true,
      'Custom portfolio link': true,
      'Priority support': true,
    },
  },
] as const;

const ALL_FEATURES = [
  'Profile listing',
  'Basic search visibility',
  'Contact leads per month',
  'Media uploads',
  'Profile views shown',
  'Instagram / YouTube link',
  'Verified badge',
  'Featured in search',
  'Priority in search results',
  'Analytics dashboard',
  'WhatsApp lead notifications',
  'Custom portfolio link',
  'Priority support',
] as const;

type FeatureKey = typeof ALL_FEATURES[number];

function FeatureValue({ value }: { value: string | boolean }) {
  if (value === true) return <Check size={18} className="feat-check" />;
  if (value === false) return <X size={16} className="feat-x" />;
  return <span className="feat-text">{value}</span>;
}

export default function PricingPage() {
  const [annual, setAnnual] = useState(true);

  return (
    <div className="pricing-page">
      {/* Navbar minimal */}
      <nav className="pricing-nav">
        <Link to="/" className="pricing-nav-logo">
          <span>prasang</span>
          <span className="pricing-nav-hindi">प्रसंग</span>
        </Link>
        <div className="pricing-nav-actions">
          <Link to="/login" className="pricing-nav-link">Sign in</Link>
          <Link to="/signup" className="pricing-nav-cta">Get started free</Link>
        </div>
      </nav>

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

      {/* Pricing cards */}
      <div className="pricing-grid">
        {PLANS.map((plan) => {
          const price = annual ? plan.yearlyPrice : plan.monthlyPrice;
          const isPopular = 'popular' in plan && plan.popular;

          return (
            <div key={plan.id} className={`pricing-card${isPopular ? ' popular' : ''}`}>
              {isPopular && <div className="popular-badge">Most Popular</div>}

              <div className="plan-header">
                <span className="plan-icon" style={{ color: plan.color }}>{plan.icon}</span>
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
                  <span className="price-note">billed ₹{price * 12}/year</span>
                )}
              </div>

              <Link
                to="/signup"
                className={`plan-cta${isPopular ? ' primary' : ''}`}
              >
                {plan.id === 'free' ? 'Start free' : `Get ${plan.name}`}
              </Link>

              <ul className="plan-features">
                {ALL_FEATURES.map((feat) => {
                  const val = (plan.features as Record<FeatureKey, string | boolean>)[feat];
                  if (val === false) return null;
                  return (
                    <li key={feat} className="plan-feature-item">
                      <Check size={15} className="feat-check-sm" />
                      <span className="feat-name">{feat}</span>
                      {typeof val === 'string' && <span className="feat-val">{val}</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>

      {/* Comparison table */}
      <div className="comparison-section">
        <h2 className="comparison-title">Full comparison</h2>
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr>
                <th className="col-feature">Features</th>
                {PLANS.map((p) => (
                  <th key={p.id} className={`col-plan${p.id === 'pro' ? ' col-popular' : ''}`}>
                    <span style={{ color: p.color }}>{p.name}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ALL_FEATURES.map((feat) => (
                <tr key={feat}>
                  <td className="feat-row-label">{feat}</td>
                  {PLANS.map((p) => (
                    <td key={p.id} className={`feat-row-val${p.id === 'pro' ? ' col-popular' : ''}`}>
                      <FeatureValue value={(p.features as Record<FeatureKey, string | boolean>)[feat]} />
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
            { q: 'Can I change plans later?', a: 'Yes! Upgrade or downgrade anytime. Changes apply from your next billing cycle.' },
            { q: 'Is there a free trial for paid plans?', a: 'All paid plans come with a 7-day free trial. No credit card required to start.' },
            { q: 'How do buyers contact me?', a: 'Buyers submit their event details and we reveal your contact info to them. You also get instant WhatsApp notifications on Pro & Premium.' },
            { q: 'What payment methods do you accept?', a: 'UPI, credit/debit cards, net banking, and Paytm. All payments are 100% secure.' },
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
        <Link to="/signup" className="pricing-bottom-btn">Create your profile →</Link>
      </div>
    </div>
  );
}
