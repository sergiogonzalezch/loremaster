/**
 * Barra de navegación superior con branding, enlaces y menú de usuario.
 *
 * Muestra el avatar del usuario (o iniciales como fallback), enlaces a
 * colecciones, perfil público, admin (si aplica) y logout.
 */

import { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Container, Dropdown } from "react-bootstrap";
import { useAuth } from "../hooks/useAuth";
import { getMyAvatar } from "../api/users";

/** Círculo con las iniciales del usuario como avatar fallback. */
function InitialsCircle({ username }: { username: string }) {
  const initials = username.slice(0, 2).toUpperCase();
  return (
    <div
      style={{
        width: 32,
        height: 32,
        borderRadius: "50%",
        background:
          "linear-gradient(135deg, var(--lm-accent) 0%, rgba(255,200,50,0.3) 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "0.7rem",
        fontFamily: "var(--lm-font-head)",
        fontWeight: 700,
        color: "#000",
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}

export default function AppNavbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const from = (location.state as { from?: string })?.from ?? location.pathname;
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setAvatarUrl(null);
      return;
    }
    getMyAvatar()
      .then((r) => setAvatarUrl(r.avatar_url ?? null))
      .catch(() => {});
  }, [user]);

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

            <Dropdown align="end">
              <Dropdown.Toggle
                as="div"
                style={{ cursor: "pointer", listStyle: "none" }}
                className="d-flex align-items-center gap-2"
              >
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt={user.username}
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      objectFit: "cover",
                      border: "1px solid var(--lm-accent)",
                      flexShrink: 0,
                    }}
                  />
                ) : (
                  <InitialsCircle username={user.username} />
                )}
                <span
                  style={{
                    color: "rgba(255,255,255,0.55)",
                    fontSize: "0.82rem",
                    fontFamily: "var(--lm-font-head)",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                  }}
                >
                  {user.username}
                </span>
              </Dropdown.Toggle>

              <Dropdown.Menu
                variant="dark"
                style={{
                  backgroundColor: "rgba(10,10,18,0.95)",
                  border: "1px solid var(--lm-border)",
                  backdropFilter: "blur(8px)",
                }}
              >
                <Dropdown.Item as={Link} to={`/users/${user.username}`}>
                  Mi perfil público
                </Dropdown.Item>
                {user.is_admin && (
                  <Dropdown.Item as={Link} to="/admin">
                    Admin
                  </Dropdown.Item>
                )}
                <Dropdown.Divider
                  style={{ borderColor: "rgba(255,255,255,0.2)" }}
                />
                <Dropdown.Item onClick={handleLogout}>
                  Cerrar sesión
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
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
