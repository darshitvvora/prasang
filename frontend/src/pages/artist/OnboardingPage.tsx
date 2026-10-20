import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Check, Upload, AtSign, PlayCircle, ChevronRight, Plane, Globe, CalendarDays } from 'lucide-react';
import type { ArtistType, EventType } from '../../types/artist';
import { ARTIST_TYPE_LABELS, EVENT_TYPE_LABELS, LANGUAGES } from '../../types/artist';
import { ApiError } from '../../api/client';
import { requestUploadUrl, setAvatar, uploadToUrl } from '../../api/endpoints';
import { useCreateArtist, useLocations, useMyArtist, useMySubscription, useStartTrial, useUpdateMyArtist } from '../../api/queries';
import { imageOr } from '../../api/format';
import { useAuth } from '../../auth/AuthProvider';
import FullPageSpinner from '../../components/FullPageSpinner';
import MediaUploader from '../../components/MediaUploader';
import { InlineError } from '../../components/QueryState';
import {
  emptyProfileForm, errorsFromApi, formFromProfile, toProfileInput, validateProfileForm,
  type ProfileFormErrors, type ProfileFormState,
} from './profileForm';
import './ArtistPages.css';

const STEPS = ['Profile Setup', 'Social & Media', 'Choose Plan'];
type PaidTier = 'basic' | 'pro' | 'premium';

const ARTIST_TYPES: ArtistType[] = ['magician', 'dj', 'singer', 'comedian', 'band', 'bubble_artist', 'anchor', 'other'];

export default function OnboardingPage() {
  const myArtist = useMyArtist();
  const { user } = useAuth();
  if (myArtist.isPending) return <FullPageSpinner />;
  const notFound = myArtist.error instanceof ApiError && myArtist.error.status === 404;
  if (myArtist.isError && !notFound) {
    return <div className="onboarding-page"><div className="onboarding-body"><InlineError error={myArtist.error} /></div></div>;
  }
  const initial = myArtist.data ? formFromProfile(myArtist.data) : { ...emptyProfileForm(), name: user?.fullName ?? '' };
  return (
    <OnboardingWizard
      initial={initial}
      exists={!!myArtist.data}
      published={myArtist.data?.isPublished ?? false}
      avatarUrl={myArtist.data?.profileImageUrl ?? null}
    />
  );
}

function OnboardingWizard({ initial, exists, published, avatarUrl }: { initial: ProfileFormState; exists: boolean; published: boolean; avatarUrl: string | null }) {
  const navigate = useNavigate();
  const locations = useLocations();
  const subscription = useMySubscription();
  const createArtist = useCreateArtist();
  const updateArtist = useUpdateMyArtist();
  const startTrial = useStartTrial();
  const avatarInput = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState(0);
  const [form, setForm] = useState<ProfileFormState>(initial);
  const [errors, setErrors] = useState<ProfileFormErrors>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [selectedPlan, setSelectedPlan] = useState<PaidTier>('pro');
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(avatarUrl);

  useEffect(() => () => { if (avatarPreview?.startsWith('blob:')) URL.revokeObjectURL(avatarPreview); }, [avatarPreview]);

  const cities = locations.data?.cities ?? [];
  const areas = cities.find((c) => c.name === form.city)?.areas ?? [];
  const trialAvailable = subscription.data?.plan.trialAvailable ?? false;

  function set<K extends keyof ProfileFormState>(key: K, val: ProfileFormState[K]) {
    setForm((f) => ({ ...f, [key]: val }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }
  const toggle = <T,>(list: T[], item: T) => (list.includes(item) ? list.filter((x) => x !== item) : [...list, item]);
  const toggleEventType = (t: EventType) => set('eventTypes', toggle(form.eventTypes, t));
  const toggleLanguage = (lang: string) => set('languages', toggle(form.languages, lang));

  function pickAvatar(file: File | undefined) {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { setError(new Error('Profile photo must be under 5 MB')); return; }
    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
  }

  async function save(task: () => Promise<void>) {
    setSaving(true);
    setError(null);
    try {
      await task();
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.code === 'validation_error') {
        setErrors(errorsFromApi((e.details?.fields ?? {}) as Record<string, string>));
      }
      setError(e);
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function saveProfileStep() {
    const found = validateProfileForm(form);
    setErrors(found);
    if (Object.keys(found).length > 0) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    const ok = await save(async () => {
      const input = toProfileInput(form);
      if (exists || createArtist.isSuccess) await updateArtist.mutateAsync(input);
      else await createArtist.mutateAsync(input);
      if (avatarFile) {
        const target = await requestUploadUrl({ kind: 'avatar', contentType: avatarFile.type || 'image/jpeg', sizeBytes: avatarFile.size });
        await uploadToUrl(target, avatarFile);
        await setAvatar(target.storageKey);
        setAvatarFile(null);
      }
    });
    if (ok) setStep(1);
  }

  async function saveSocialStep() {
    const input = toProfileInput(form);
    const ok = await save(async () => {
      await updateArtist.mutateAsync({
        instagramHandle: input.instagramHandle, youtubeChannel: input.youtubeChannel, facebookUrl: input.facebookUrl,
        googlePlaceUrl: input.googlePlaceUrl,
      });
    });
    if (ok) setStep(2);
  }

  async function handleFinish() {
    const ok = await save(async () => {
      if (!published) await updateArtist.mutateAsync({ isPublished: true });
      if (trialAvailable) {
        await startTrial.mutateAsync({ tier: selectedPlan }).catch((e) => {
          if (!(e instanceof ApiError && e.code === 'trial_used')) throw e;
        });
      }
    });
    if (ok) navigate('/artist/dashboard');
  }

  const fieldError = (k: keyof ProfileFormState) => errors[k] && <span className="ob-field-error">{errors[k]}</span>;
  const prevStep = () => setStep((s) => Math.max(s - 1, 0));

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
        <InlineError error={error} />

        {/* Step 0 — Profile */}
        {step === 0 && (
          <div className="onboarding-form">
            <h2 className="onboarding-title">{exists ? 'Edit your artist profile' : 'Set up your artist profile'}</h2>
            <p className="onboarding-sub">This is what event planners will see when they search for artists.</p>

            <div className="ob-field">
              <label htmlFor="ob-name">Full name / Stage name</label>
              <input id="ob-name" className="ob-input" placeholder="e.g. Arjun the Magician" value={form.name} onChange={(e) => set('name', e.target.value)} />
              {fieldError('name')}
            </div>

            <div className="ob-field">
              <label>Artist type</label>
              <div className="ob-type-grid">
                {ARTIST_TYPES.map((t) => (
                  <button key={t} type="button" className={`ob-type-btn${form.artistType === t ? ' selected' : ''}`} onClick={() => set('artistType', t)}>
                    {ARTIST_TYPE_LABELS[t]}
                  </button>
                ))}
              </div>
              {fieldError('artistType')}
            </div>

            <div className="ob-row">
              <div className="ob-field">
                <label htmlFor="ob-city">City</label>
                <select id="ob-city" className="ob-input" value={form.city} onChange={(e) => { set('city', e.target.value); set('area', ''); }}>
                  <option value="">Select city</option>
                  {cities.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
                </select>
                {fieldError('city')}
              </div>
              <div className="ob-field">
                <label htmlFor="ob-area">Area / Locality</label>
                <input id="ob-area" className="ob-input" placeholder="e.g. Bandra West" value={form.area} list="ob-area-options" onChange={(e) => set('area', e.target.value)} />
                <datalist id="ob-area-options">{areas.map((a) => <option key={a} value={a} />)}</datalist>
                {fieldError('area')}
              </div>
            </div>

            <div className="ob-row">
              <div className="ob-field">
                <label htmlFor="ob-phone">Contact phone (shown to planners who enquire)</label>
                <input id="ob-phone" className="ob-input" type="tel" inputMode="numeric" placeholder="9876543210" maxLength={10}
                  value={form.contactPhone} onChange={(e) => set('contactPhone', e.target.value.replace(/\D/g, '').slice(0, 10))} />
                {fieldError('contactPhone')}
              </div>
              <div className="ob-field">
                <label htmlFor="ob-whatsapp">WhatsApp number (optional)</label>
                <input id="ob-whatsapp" className="ob-input" type="tel" inputMode="numeric" placeholder="Same as phone if empty" maxLength={10}
                  value={form.whatsappNumber} onChange={(e) => set('whatsappNumber', e.target.value.replace(/\D/g, '').slice(0, 10))} />
                {fieldError('whatsappNumber')}
              </div>
            </div>

            <div className="ob-field">
              <label htmlFor="ob-bio">Bio (tell buyers about yourself)</label>
              <textarea id="ob-bio" className="ob-input ob-textarea" rows={4} maxLength={2000} value={form.bio} onChange={(e) => set('bio', e.target.value)}
                placeholder="I am a professional magician with 8+ years of experience performing at weddings, corporate events, and private parties across Mumbai..." />
              <span className="ob-hint">{form.bio.length}/300 characters recommended</span>
              {fieldError('bio')}
            </div>

            <div className="ob-row">
              <div className="ob-field">
                <label htmlFor="ob-exp">Years of experience</label>
                <input id="ob-exp" className="ob-input" type="number" min="0" max="50" placeholder="8" value={form.experienceYears} onChange={(e) => set('experienceYears', e.target.value)} />
                {fieldError('experienceYears')}
              </div>
              <div className="ob-field">
                <label>Rate range (₹ per event)</label>
                <div className="ob-rate-row">
                  <input className="ob-input" type="number" min="0" placeholder="15000" aria-label="Minimum rate" value={form.rateMin} onChange={(e) => set('rateMin', e.target.value)} />
                  <span className="ob-rate-sep">to</span>
                  <input className="ob-input" type="number" min="0" placeholder="50000" aria-label="Maximum rate" value={form.rateMax} onChange={(e) => set('rateMax', e.target.value)} />
                </div>
                {fieldError('rateMin') ?? fieldError('rateMax')}
              </div>
            </div>

            <div className="ob-field">
              <label>
                <CalendarDays size={15} /> Event types you perform at
              </label>
              <div className="ob-type-grid">
                {(Object.keys(EVENT_TYPE_LABELS) as EventType[]).map((t) => (
                  <button
                    key={t}
                    type="button"
                    className={`ob-type-btn${form.eventTypes.includes(t) ? ' selected' : ''}`}
                    onClick={() => toggleEventType(t)}
                  >
                    {EVENT_TYPE_LABELS[t]}
                  </button>
                ))}
              </div>
            </div>

            <div className="ob-field">
              <label>
                <Globe size={15} /> Languages you perform in
              </label>
              <div className="ob-type-grid">
                {LANGUAGES.map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    className={`ob-type-btn${form.languages.includes(lang) ? ' selected' : ''}`}
                    onClick={() => toggleLanguage(lang)}
                  >
                    {lang}
                  </button>
                ))}
              </div>
            </div>

            <div className="ob-field">
              <label className="ob-toggle-label">
                <Plane size={15} /> Ready to travel outside your city?
                <label className="ob-toggle">
                  <input
                    type="checkbox"
                    checked={form.readyToTravel}
                    onChange={(e) => set('readyToTravel', e.target.checked)}
                  />
                  <span className="ob-toggle-track" />
                </label>
              </label>
              <span className="ob-hint">
                {form.readyToTravel ? '✈️ Artists open to travelling get 40% more enquiries from other cities.' : 'You will only receive enquiries from your city.'}
              </span>
            </div>

            {fieldError('eventTypes')}

            <div className="ob-field">
              <label>Profile photo</label>
              <button type="button" className="ob-upload-box" onClick={() => avatarInput.current?.click()}>
                {avatarPreview ? <img src={imageOr(avatarPreview)} alt="Profile preview" className="ob-avatar-preview" /> : <Upload size={24} />}
                <span>{avatarPreview ? 'Change photo' : 'Click to upload'}</span>
                <span className="ob-hint">JPG, PNG · Max 5MB</span>
              </button>
              <input ref={avatarInput} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(e) => pickAvatar(e.target.files?.[0])} />
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
                <input className="ob-input ob-social-field" placeholder="arjunmagician" value={form.instagram} onChange={(e) => set('instagram', e.target.value)} />
              </div>
            </div>

            <div className="ob-field">
              <label><PlayCircle size={15} /> YouTube channel</label>
              <div className="ob-social-input">
                <span className="ob-social-prefix">youtube.com/</span>
                <input className="ob-input ob-social-field" placeholder="@arjunmagic" value={form.youtube} onChange={(e) => set('youtube', e.target.value)} />
              </div>
            </div>

            <div className="ob-field">
              <label><Globe size={15} /> Facebook page</label>
              <input className="ob-input" placeholder="facebook.com/yourpage" value={form.facebook} onChange={(e) => set('facebook', e.target.value)} />
              {fieldError('facebook')}
              <span className="ob-hint">Your Instagram, YouTube and Facebook appear as live widgets on your profile.</span>
            </div>

            <div className="ob-field">
              <label><Globe size={15} /> Google Maps link to your business (optional)</label>
              <input className="ob-input" placeholder="https://maps.app.goo.gl/…" value={form.googleMaps} onChange={(e) => set('googleMaps', e.target.value)} />
              {fieldError('googleMaps')}
              <span className="ob-hint">If you have a Google Business listing, we show your Google rating and recent Google reviews on your profile.</span>
            </div>

            <MediaUploader />

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
                  className={`ob-plan-card${selectedPlan === plan.id ? ' selected' : ''}`}
                  onClick={() => setSelectedPlan(plan.id)}
                >
                  {'popular' in plan && plan.popular && <div className="ob-plan-popular">Recommended</div>}
                  <div className="ob-plan-name" style={{ color: plan.color }}>{plan.name}</div>
                  <div className="ob-plan-price">₹{plan.price}<span>/mo</span></div>
                  <div className="ob-plan-leads">{plan.leads}</div>
                  {selectedPlan === plan.id && <Check size={18} className="ob-plan-check" />}
                </button>
              ))}
            </div>

            <Link to="/pricing" className="ob-compare-link">
              Compare all plans →
            </Link>

            <div className="ob-trial-note">
              {trialAvailable
                ? '🎉 7-day free trial on all paid plans. No credit card required to start.'
                : 'Your free trial has been used. You can upgrade any time from the Pricing page.'}
            </div>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="onboarding-footer">
          {step > 0 && (
            <button className="ob-back-btn" onClick={prevStep} disabled={saving}>← Back</button>
          )}
          {step === 0 && (
            <button className="ob-next-btn" onClick={saveProfileStep} disabled={saving}>
              {saving ? 'Saving…' : <>Next <ChevronRight size={16} /></>}
            </button>
          )}
          {step === 1 && (
            <button className="ob-next-btn" onClick={saveSocialStep} disabled={saving}>
              {saving ? 'Saving…' : <>Next <ChevronRight size={16} /></>}
            </button>
          )}
          {step === 2 && (
            <button className="ob-next-btn" onClick={handleFinish} disabled={saving}>
              {saving ? 'Launching…' : published ? 'Save & go to dashboard' : trialAvailable ? `Start ${selectedPlan} trial & launch 🚀` : 'Launch Profile 🚀'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
