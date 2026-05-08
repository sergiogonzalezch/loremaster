import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Container } from "react-bootstrap";
import { useAuth } from "../hooks/useAuth";

export default function AppNavbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const from = (location.state as { from?: string })?.from ?? location.pathname;

  function handleLogout() {
    logout();
    navigate("/feed", { replace: true });
  }

  const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
    color: isActive ? "var(--lm-accent)" : "rgba(255,255,255,0.55)",
    textDecoration: "none",
    fontSize: "0.82rem",
    fontFamily: "var(--lm-font-head)",
    letterSpacing: "0.08em",
    textTransform: "uppercase" as const,
  });

  return (
    <nav
      style={{
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        backdropFilter: "blur(8px)",
        backgroundColor: "rgba(10,10,18,0.7)",
        position: "relative",
        zIndex: 2,
      }}
      className="py-3"
    >
      <Container
        fluid="lg"
        className="d-flex align-items-center justify-content-between"
      >
        <Link
          to="/feed"
          className="navbar-brand"
          style={{ textDecoration: "none" }}
        >
          <span className="lm-brand-glyph">✦</span>
          <span className="lore">Lore</span>
          <span>Master</span>
        </Link>

        {user ? (
          <div className="d-flex align-items-center gap-3">
            <NavLink to="/collections" style={navLinkStyle}>
              Colecciones
            </NavLink>
            {user.is_admin && (
              <NavLink to="/admin" style={navLinkStyle}>
                Admin
              </NavLink>
            )}
            <NavLink to="/profile" style={navLinkStyle}>
              {user.username}
            </NavLink>
            <button
              onClick={handleLogout}
              className="btn btn-sm btn-outline-secondary"
            >
              Cerrar sesión
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            state={{ from }}
            className="btn btn-sm btn-warning"
            style={{ fontFamily: "var(--lm-font-head)" }}
          >
            Iniciar sesión
          </Link>
        )}
      </Container>
    </nav>
  );
}
