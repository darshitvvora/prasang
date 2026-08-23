import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import SearchPage from './pages/SearchPage';
import ArtistProfilePage from './pages/ArtistProfilePage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import PricingPage from './pages/PricingPage';
import DashboardPage from './pages/artist/DashboardPage';
import OnboardingPage from './pages/artist/OnboardingPage';
import LeadsPage from './pages/artist/LeadsPage';
import PlannerDashboardPage from './pages/planner/DashboardPage';
import PlannerInquiriesPage from './pages/planner/InquiriesPage';

// Legal Pages
import PrivacyPolicy from './pages/legal/PrivacyPolicy';
import TermsOfService from './pages/legal/TermsOfService';
import CookiePolicy from './pages/legal/CookiePolicy';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/profile/:slug" element={<ArtistProfilePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/artist/dashboard" element={<DashboardPage />} />
        <Route path="/artist/onboarding" element={<OnboardingPage />} />
        <Route path="/artist/leads" element={<LeadsPage />} />
        <Route path="/planner/dashboard" element={<PlannerDashboardPage />} />
        <Route path="/planner/inquiries" element={<PlannerInquiriesPage />} />
        
        {/* Legal Routes */}
        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
        <Route path="/terms-of-service" element={<TermsOfService />} />
        <Route path="/cookie-policy" element={<CookiePolicy />} />
      </Routes>
    </BrowserRouter>
  );
}
