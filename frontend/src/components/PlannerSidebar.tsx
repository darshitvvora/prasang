import { Link } from 'react-router-dom';
import { LayoutDashboard, MessageCircle, Search, ChevronRight } from 'lucide-react';
import '../pages/planner/PlannerPages.css';

export default function PlannerSidebar({ active }: { active: 'dashboard' | 'inquiries' }) {
  return (
    <aside className="planner-sidebar">
      <Link to="/" className="planner-sidebar-logo">
        <span>prasang</span>
        <span className="planner-sidebar-logo-hindi">प्रसंग</span>
      </Link>
      <nav className="planner-sidebar-nav">
        <Link to="/planner/dashboard" className={`planner-sidebar-link${active === 'dashboard' ? ' active' : ''}`}>
          <LayoutDashboard size={18} /> Dashboard
        </Link>
        <Link to="/planner/inquiries" className={`planner-sidebar-link${active === 'inquiries' ? ' active' : ''}`}>
          <MessageCircle size={18} /> My Inquiries
        </Link>
        <Link to="/search" className="planner-sidebar-link">
          <Search size={18} /> Browse Artists
        </Link>
      </nav>
      <div className="planner-promo-card">
        <div className="planner-promo-title">Looking for more artists?</div>
        <div className="planner-promo-note">Search magicians, DJs, singers and more near you.</div>
        <Link to="/search" className="planner-promo-btn">
          Browse Artists <ChevronRight size={14} />
        </Link>
      </div>
    </aside>
  );
}
