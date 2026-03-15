import { NavLink } from 'react-router-dom';

export function Navbar() {
  return (
    <nav className="navbar">
      <NavLink to="/" className="navbar-brand">
        <span className="brand-icon">📄</span>
        DocFlow
      </NavLink>
      <div className="navbar-links">
        <NavLink
          to="/"
          end
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          ⬆️ Upload
        </NavLink>
        <NavLink
          to="/crm"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          🏢 CRM
        </NavLink>
        <NavLink
          to="/compliance"
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          🛡️ Conformité
        </NavLink>
      </div>
    </nav>
  );
}
