import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import '../components/QueryState.css';

export default function NotFoundPage({ title = 'Page not found', message = "The page you're looking for doesn't exist." }: { title?: string; message?: string }) {
  return (
    <>
      <Navbar />
      <main className="container qs-fullpage">
        <h1 className="qs-error-title" style={{ fontSize: 28 }}>{title}</h1>
        <p className="qs-label">{message}</p>
        <Link to="/search" className="qs-retry">Browse artists</Link>
      </main>
      <Footer />
    </>
  );
}
