import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import './LegalPages.css';

export default function PrivacyPolicy() {
  return (
    <>
      <Navbar />
      <main className="legal-page-container">
        <div className="legal-page-header">
          <h1 className="legal-page-title">Privacy Policy</h1>
          <p className="legal-page-date">Last Updated: August 23, 2026</p>
        </div>
        
        <div className="legal-page-content">
          <p>
            Welcome to Prasang ("we," "our," or "us"). We are committed to protecting your personal information and your right to privacy. This Privacy Policy applies to all information collected through our website (prasang.in), mobile application, and related services (collectively, the "Platform").
          </p>

          <h2>1. Information We Collect</h2>
          <p>We collect personal information that you voluntarily provide to us when you register on the Platform. This includes:</p>
          <ul>
            <li><strong>Personal Details:</strong> Name, phone number, email address, and profile picture.</li>
            <li><strong>Artist Details:</strong> Location, event types supported, languages spoken, and performance rates.</li>
            <li><strong>Automatically Collected Information:</strong> IP address, browser type, device information, and usage data collected via cookies.</li>
          </ul>

          <h2>2. How We Use Your Information</h2>
          <p>We process your information for purposes based on legitimate business interests, the fulfillment of our contract with you, compliance with our legal obligations, and/or your consent. We use your data to:</p>
          <ul>
            <li>Facilitate account creation and authentication.</li>
            <li>Connect event planners with artists and send lead notifications.</li>
            <li>Improve our AI-powered discovery and search indexing.</li>
            <li>Send administrative and marketing communications.</li>
          </ul>

          <h2>3. Data Sharing and Disclosure</h2>
          <p>
            Prasang is a pure subscription platform. We do not sell your personal data. We may share your data with third-party service providers (such as Razorpay for payments and AWS for hosting) strictly for the purpose of operating the Platform. We may also disclose your information to comply with applicable laws, such as the Digital Personal Data Protection Act, 2023 (DPDPA) of India, and the General Data Protection Regulation (GDPR).
          </p>

          <h2>4. Your Privacy Rights</h2>
          <p>
            Depending on your location, you may have the right to request access to, correction of, or deletion of your personal data. Users in India are protected under the DPDPA, and users in the European Economic Area are protected under the GDPR. You may update your profile information directly from your dashboard or contact us to exercise your rights.
          </p>

          <h2>5. Contact Us</h2>
          <p>
            If you have questions or comments about this policy, you may email our Data Protection Officer at privacy@prasang.in or by post to our registered office in Mumbai, India.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
