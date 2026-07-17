import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Check, Upload, AtSign, PlayCircle, ChevronRight } from 'lucide-react';
import type { ArtistType } from '../../types/artist';
import { ARTIST_TYPE_LABELS } from '../../types/artist';
import './ArtistPages.css';

const STEPS = ['Profile Setup', 'Social & Media', 'Choose Plan'];

const CITIES = ['Mumbai', 'Delhi', 'Bengaluru', 'Pune', 'Hyderabad', 'Chennai', 'Kolkata', 'Ahmedabad'];

type FormState = {
  name: string;
  artistType: ArtistType | '';
  city: string;
  area: string;
  bio: string;
  experienceYears: string;
  rateMin: string;
  rateMax: string;
  instagram: string;
  youtube: string;
  selectedPlan: 'basic' | 'pro' | 'premium';
};

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<FormState>({
    name: '', artistType: '', city: '', area: '', bio: '',
    experienceYears: '', rateMin: '', rateMax: '',
    instagram: '', youtube: '', selectedPlan: 'pro',
  });

  function set(key: keyof FormState, val: string) {
    setForm((f) => ({ ...f, [key]: val }));
  }

  function nextStep() { setStep((s) => Math.min(s + 1, 2)); }
  function prevStep() { setStep((s) => Math.max(s - 1, 0)); }

  function handleFinish() {
    navigate('/artist/dashboard');
  }

  const ARTIST_TYPES: ArtistType[] = [
    'magician', 'dj', 'singer', 'comedian', 'band', 'bubble_artist', 'anchor', 'other'
  ];

  return (
    <div className="onboarding-page">
      {/* Top bar */}
      <div className="onboarding-topbar">
        <Link to="/" className="sidebar-logo" style={{ margin: 0 }}>
          <span>prasang</span>
          <span className="sidebar-logo-hindi">प्रसंग</span>
        </Link>
        <div className="onboarding-step-count">Step {step + 1} of {STEPS.length}</div>
      </div>

      {/* Steps indicator */}
      <div className="onboarding-steps">
        {STEPS.map((label, i) => (
          <div key={label} className={`onboarding-step${i <= step ? ' done' : ''}${i === step ? ' active' : ''}`}>
            <div className="step-circle">
              {i < step ? <Check size={14} /> : i + 1}
            </div>
            <span className="step-label">{label}</span>
            {i < STEPS.length - 1 && <div className="step-line" />}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="onboarding-body">
        {/* Step 0 — Profile */}
        {step === 0 && (
          <div className="onboarding-form">
            <h2 className="onboarding-title">Set up your artist profile</h2>
            <p className="onboarding-sub">This is what event planners will see when they search for artists.</p>

            <div className="ob-field">
              <label>Full name / Stage name</label>
              <input
                className="ob-input"
                placeholder="e.g. Arjun the Magician"
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
              />
            </div>

            <div className="ob-field">
              <label>Artist type</label>
              <div className="ob-type-grid">
                {ARTIST_TYPES.map((t) => (
                  <button
                    key={t}
                    type="button"
                    className={`ob-type-btn${form.artistType === t ? ' selected' : ''}`}
                    onClick={() => set('artistType', t)}
                  >
                    {ARTIST_TYPE_LABELS[t]}
                  </button>
                ))}
              </div>
            </div>

            <div className="ob-row">
              <div className="ob-field">
                <label>City</label>
                <select className="ob-input" value={form.city} onChange={(e) => set('city', e.target.value)}>
                  <option value="">Select city</option>
                  {CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="ob-field">
                <label>Area / Locality</label>
                <input
                  className="ob-input"
                  placeholder="e.g. Bandra West"
                  value={form.area}
                  onChange={(e) => set('area', e.target.value)}
                />
              </div>
            </div>

            <div className="ob-field">
              <label>Bio (tell buyers about yourself)</label>
              <textarea
                className="ob-input ob-textarea"
                placeholder="I am a professional magician with 8+ years of experience performing at weddings, corporate events, and private parties across Mumbai..."
                value={form.bio}
                onChange={(e) => set('bio', e.target.value)}
                rows={4}
              />
              <span className="ob-hint">{form.bio.length}/300 characters recommended</span>
            </div>

            <div className="ob-row">
              <div className="ob-field">
                <label>Years of experience</label>
                <input
                  className="ob-input"
                  type="number"
                  min="0"
                  max="50"
                  placeholder="8"
                  value={form.experienceYears}
                  onChange={(e) => set('experienceYears', e.target.value)}
                />
              </div>
              <div className="ob-field">
                <label>Rate range (₹ per event)</label>
                <div className="ob-rate-row">
                  <input
                    className="ob-input"
                    type="number"
                    placeholder="15000"
                    value={form.rateMin}
                    onChange={(e) => set('rateMin', e.target.value)}
                  />
                  <span className="ob-rate-sep">to</span>
                  <input
                    className="ob-input"
                    type="number"
                    placeholder="50000"
                    value={form.rateMax}
                    onChange={(e) => set('rateMax', e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="ob-field">
              <label>Profile photo</label>
              <div className="ob-upload-box">
                <Upload size={24} />
                <span>Click to upload or drag & drop</span>
                <span className="ob-hint">JPG, PNG · Max 5MB</span>
              </div>
            </div>
          </div>
        )}

        {/* Step 1 — Social */}
        {step === 1 && (
          <div className="onboarding-form">
            <h2 className="onboarding-title">Connect your social media</h2>
            <p className="onboarding-sub">Profiles with social links get 2.4× more contact requests.</p>

            <div className="ob-field">
              <label><AtSign size={15} /> Instagram handle</label>
              <div className="ob-social-input">
                <span className="ob-social-prefix">@</span>
                <input
                  className="ob-input ob-social-field"
                  placeholder="arjunmagician"
                  value={form.instagram}
                  onChange={(e) => set('instagram', e.target.value)}
                />
              </div>
            </div>

            <div className="ob-field">
              <label><PlayCircle size={15} /> YouTube channel</label>
              <div className="ob-social-input">
                <span className="ob-social-prefix">youtube.com/</span>
                <input
                  className="ob-input ob-social-field"
                  placeholder="@arjunmagic"
                  value={form.youtube}
                  onChange={(e) => set('youtube', e.target.value)}
                />
              </div>
            </div>

            <div className="ob-field">
              <label>Upload portfolio media</label>
              <div className="ob-upload-box tall">
                <Upload size={28} />
                <span>Upload photos & videos of your performances</span>
                <span className="ob-hint">Up to 20 photos + 3 videos on Basic plan</span>
              </div>
            </div>

            <div className="ob-info-card">
              <div className="ob-info-icon">💡</div>
              <div className="ob-info-text">
                <strong>Tip:</strong> Artists with 5+ portfolio photos get 3× more profile views than those with none.
              </div>
            </div>
          </div>
        )}

        {/* Step 2 — Plan */}
        {step === 2 && (
          <div className="onboarding-form">
            <h2 className="onboarding-title">Choose your plan</h2>
            <p className="onboarding-sub">Start free. Upgrade anytime. All plans include a 7-day trial.</p>

            <div className="ob-plans">
              {([
                { id: 'basic', name: 'Basic', price: 299, leads: '15 leads/mo', color: '#60a5fa' },
                { id: 'pro', name: 'Pro', price: 599, leads: 'Unlimited leads', color: '#d4f53f', popular: true },
                { id: 'premium', name: 'Premium', price: 1199, leads: 'Unlimited + Top 3 placement', color: '#a78bfa' },
              ] as const).map((plan) => (
                <button
                  key={plan.id}
                  type="button"
                  className={`ob-plan-card${form.selectedPlan === plan.id ? ' selected' : ''}`}
                  onClick={() => set('selectedPlan', plan.id)}
                >
                  {'popular' in plan && plan.popular && <div className="ob-plan-popular">Recommended</div>}
                  <div className="ob-plan-name" style={{ color: plan.color }}>{plan.name}</div>
                  <div className="ob-plan-price">₹{plan.price}<span>/mo</span></div>
                  <div className="ob-plan-leads">{plan.leads}</div>
                  {form.selectedPlan === plan.id && <Check size={18} className="ob-plan-check" />}
                </button>
              ))}
            </div>

            <Link to="/pricing" className="ob-compare-link">
              Compare all plans →
            </Link>

            <div className="ob-trial-note">
              🎉 7-day free trial on all paid plans. No credit card required to start.
            </div>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="onboarding-footer">
          {step > 0 && (
            <button className="ob-back-btn" onClick={prevStep}>← Back</button>
          )}
          {step < 2 ? (
            <button className="ob-next-btn" onClick={nextStep}>
              Next <ChevronRight size={16} />
            </button>
          ) : (
            <button className="ob-next-btn" onClick={handleFinish}>
              Launch Profile 🚀
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
