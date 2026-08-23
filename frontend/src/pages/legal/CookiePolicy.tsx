import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import './LegalPages.css';

export default function CookiePolicy() {
  return (
    <>
      <Navbar />
      <main className="legal-page-container">
        <div className="legal-page-header">
          <h1 className="legal-page-title">Cookie Policy</h1>
          <p className="legal-page-date">Last Updated: August 23, 2026</p>
        </div>
        
        <div className="legal-page-content">
          <p>
            This Cookie Policy explains how Prasang ("we", "us", and "our") uses cookies and similar technologies to recognize you when you visit our website at prasang.in. It explains what these technologies are and why we use them, as well as your rights to control our use of them.
          </p>

          <h2>1. What are cookies?</h2>
          <p>
            Cookies are small data files that are placed on your computer or mobile device when you visit a website. Cookies are widely used by website owners in order to make their websites work, or to work more efficiently, as well as to provide reporting information.
          </p>

          <h2>2. Why do we use cookies?</h2>
          <p>We use first-party and third-party cookies for several reasons:</p>
          <ul>
            <li><strong>Essential Cookies:</strong> These are strictly necessary to provide you with services available through our Platform, such as securing your account and managing user sessions.</li>
            <li><strong>Performance & Analytics Cookies:</strong> These cookies collect information that is used either in aggregate form to help us understand how our Platform is being used, or to help us customize our Platform for you (e.g., recently viewed artists, search history).</li>
            <li><strong>Functionality Cookies:</strong> These are used to recognize you when you return to our Platform, enabling us to personalize content and remember your preferences (like location or language filters).</li>
          </ul>

          <h2>3. Third-Party Cookies</h2>
          <p>
            In some special cases, we also use cookies provided by trusted third parties. For example, our site uses third-party analytics to help us understand how you use the site and ways we can improve your experience. We also embed social media content (from YouTube, Instagram, etc.), which may set their own cookies when you interact with their widgets.
          </p>

          <h2>4. How can I control cookies?</h2>
          <p>
            You have the right to decide whether to accept or reject non-essential cookies. You can set or amend your web browser controls to accept or refuse cookies. If you choose to reject cookies, you may still use our website though your access to some functionality and areas of our website may be restricted.
          </p>
          <p>
            Since the means by which you can refuse cookies through your web browser controls vary from browser to browser, you should visit your browser's help menu for more information.
          </p>

          <h2>5. Updates to this policy</h2>
          <p>
            We may update this Cookie Policy from time to time in order to reflect changes to the cookies we use or for other operational, legal, or regulatory reasons. Please revisit this Cookie Policy regularly to stay informed about our use of cookies and related technologies.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
