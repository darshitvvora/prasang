import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './auth/AuthProvider';
import RequireRole from './auth/RequireRole';
import HomePage from './pages/HomePage';
import SearchPage from './pages/SearchPage';
import ArtistProfilePage from './pages/ArtistProfilePage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import PricingPage from './pages/PricingPage';
import NotFoundPage from './pages/NotFoundPage';
import AuthCallbackPage from './pages/AuthCallbackPage';
import DashboardPage from './pages/artist/DashboardPage';
import OnboardingPage from './pages/artist/OnboardingPage';
import LeadsPage from './pages/artist/LeadsPage';
import PlannerDashboardPage from './pages/planner/DashboardPage';
import PlannerInquiriesPage from './pages/planner/InquiriesPage';
import AboutPage from './pages/AboutPage';
import ContactPage from './pages/ContactPage';

// Legal Pages
import PrivacyPolicy from './pages/legal/PrivacyPolicy';
import TermsOfService from './pages/legal/TermsOfService';
import CookiePolicy from './pages/legal/CookiePolicy';

const artist = (el: React.ReactNode) => <RequireRole role="artist">{el}</RequireRole>;
const planner = (el: React.ReactNode) => <RequireRole role="planner">{el}</RequireRole>;

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/profile/:slug" element={<ArtistProfilePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/auth/callback/google" element={<AuthCallbackPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />
          <Route path="/artist/dashboard" element={artist(<DashboardPage />)} />
          <Route path="/artist/onboarding" element={artist(<OnboardingPage />)} />
          <Route path="/artist/leads" element={artist(<LeadsPage />)} />
          <Route path="/planner/dashboard" element={planner(<PlannerDashboardPage />)} />
          <Route path="/planner/inquiries" element={planner(<PlannerInquiriesPage />)} />

          {/* Legal Routes */}
          <Route path="/privacy-policy" element={<PrivacyPolicy />} />
          <Route path="/terms-of-service" element={<TermsOfService />} />
          <Route path="/cookie-policy" element={<CookiePolicy />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
