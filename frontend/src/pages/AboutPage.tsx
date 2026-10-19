import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { useSiteInfo } from '../api/queries';
import { SiteContactDetails } from './ContactPage';
import './legal/LegalPages.css';
import './site.css';

export default function AboutPage() {
  const site = useSiteInfo();
  return (
    <>
      <Navbar />
      <main className="legal-page-container">
        <div className="legal-page-header">
          <h1 className="legal-page-title">About Prasang</h1>
          <p className="legal-page-date">प्रसंग — occasion, gathering. Find artists for every prasang.</p>
        </div>
        <div className="legal-page-content">
          <p>
            Prasang helps people across India find the right performer for every occasion — weddings, birthdays,
            house parties and corporate events. Browse DJs, singers, magicians, comedians, anchors and bands, watch
            their work, read reviews from real bookings and contact them directly.
          </p>

          <h2>For event planners</h2>
          <ul>
            <li>Searching, viewing profiles and contacting artists is completely free.</li>
            <li>You talk to the artist directly on phone or WhatsApp — no middleman, no booking fee.</li>
            <li>Reviews on Prasang come only from planners who actually booked the artist.</li>
          </ul>

          <h2>For artists</h2>
          <ul>
            <li>A professional profile page you can share on Instagram and WhatsApp, with your videos and posts.</li>
            <li>Enquiries from planners near you, sent straight to your phone.</li>
            <li>No commission. You keep 100% of what you earn — artists pay only a simple monthly or annual plan.</li>
          </ul>
          <p><Link to="/pricing">See plans and pricing</Link> · <Link to="/artist/onboarding">List your profile</Link></p>

          <h2>Contact us</h2>
          {site.data && <SiteContactDetails info={site.data} />}
          <p>Or write to us on the <Link to="/contact">contact page</Link>.</p>
        </div>
      </main>
      <Footer />
    </>
  );
}
