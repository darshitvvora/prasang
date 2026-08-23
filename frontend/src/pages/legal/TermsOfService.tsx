import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import './LegalPages.css';

export default function TermsOfService() {
  return (
    <>
      <Navbar />
      <main className="legal-page-container">
        <div className="legal-page-header">
          <h1 className="legal-page-title">Terms of Service</h1>
          <p className="legal-page-date">Last Updated: August 23, 2026</p>
        </div>
        
        <div className="legal-page-content">
          <p>
            Welcome to Prasang ("we," "our," or "us"). By accessing or using our platform at prasang.in, you agree to be bound by these Terms of Service. If you disagree with any part of the terms, then you may not access the service.
          </p>

          <h2>1. Nature of the Service</h2>
          <p>
            Prasang is a peer-to-peer artist discovery platform connecting performers with event planners in India. We operate on a subscription model for artists. We do not act as an agent, broker, or booking agency. All transactions, contracts, and bookings are strictly between the event planner and the artist. We do not charge commissions on bookings.
          </p>

          <h2>2. User Accounts</h2>
          <p>
            When you create an account with us, you must provide information that is accurate, complete, and current at all times. Failure to do so constitutes a breach of the Terms, which may result in immediate termination of your account. You are responsible for safeguarding the password that you use to access the service and for any activities or actions under your password.
          </p>

          <h2>3. Artist Subscriptions</h2>
          <p>
            Artists may opt for paid subscription tiers (e.g., Basic, Pro, Premium) for enhanced visibility and lead generation. Subscription fees are billed in advance on a recurring basis and are non-refundable except as required by law. We reserve the right to modify subscription fees with reasonable prior notice.
          </p>

          <h2>4. Content and Portfolios</h2>
          <p>
            Artists are solely responsible for the content (images, videos, bios) they upload or embed from social media (Instagram, YouTube, etc.). You warrant that you have the rights to use and display such content. We reserve the right to remove any content that violates these terms or is deemed inappropriate, illegal, or infringing on intellectual property rights.
          </p>

          <h2>5. Limitation of Liability</h2>
          <p>
            Prasang shall not be liable for any disputes, damages, or losses arising out of bookings or interactions between artists and event planners. We provide the platform "as is" and make no warranties regarding the quality, safety, or legality of the services offered by the artists.
          </p>

          <h2>6. Governing Law</h2>
          <p>
            These Terms shall be governed and construed in accordance with the laws of India, specifically subject to the jurisdiction of the courts in Mumbai, Maharashtra, without regard to its conflict of law provisions.
          </p>

          <h2>7. Contact Us</h2>
          <p>
            If you have any questions about these Terms, please contact us at support@prasang.in.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
