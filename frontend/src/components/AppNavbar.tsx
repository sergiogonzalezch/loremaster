/**
 * Barra de navegación superior con branding, enlaces y menú de usuario.
 *
 * Muestra el avatar del usuario (o iniciales como fallback), enlaces a
 * colecciones, perfil público, admin (si aplica) y logout.
 */

import { useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Alert, Container, Dropdown } from "react-bootstrap";
import { useClerk } from "@clerk/clerk-react";
import { useAuth } from "../hooks/useAuth";
import SafeImage from "./SafeImage";
import { clerkKey } from "../utils/clerkConfig";

/** Círculo con las iniciales del usuario como avatar fallback. */
function InitialsCircle({ username }: { username: string }) {
  const initials = username.slice(0, 2).toUpperCase();
  return (
    <div
      className="lm-avatar-initials"
      style={{ width: 32, height: 32, fontSize: "0.7rem" }}
    >
      {initials}
    </div>
  );
}

/**
 * Item de logout para el modo Clerk.
 *
 * Componente separado para que useClerk() solo se llame dentro de
 * ClerkProvider — evita errores en el modo local (sin Clerk).
 */
function ClerkLogoutItem({
  onLocalLogout,
}: {
  onLocalLogout: () => Promise<void>;
}) {
  const { signOut } = useClerk();

  async function handleLogout() {
    await onLocalLogout();
    await signOut();
  }

  return (
    <Dropdown.Item onClick={() => void handleLogout()}>
      Cerrar sesión
    </Dropdown.Item>
  );
}

export default function AppNavbar() {
  const { user, logout, avatarUrl } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const from = (location.state as { from?: string })?.from ?? location.pathname;
  const [logoutError, setLogoutError] = useState<string | null>(null);

  async function handleLocalLogout() {
    setLogoutError(null);
    try {
      await logout();
      navigate("/feed", { replace: true });
    } catch {
      setLogoutError("No se pudo cerrar sesión. Inténtalo de nuevo.");
    }
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
    <>
      {logoutError && (
        <Alert
          variant="danger"
          dismissible
          onClose={() => setLogoutError(null)}
          className="mb-0 rounded-0 text-center py-2"
          style={{ fontSize: "0.85rem" }}
        >
          {logoutError}
        </Alert>
      )}
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
                    <SafeImage
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
                  {clerkKey ? (
                    <ClerkLogoutItem onLocalLogout={handleLocalLogout} />
                  ) : (
                    <Dropdown.Item onClick={() => void handleLocalLogout()}>
                      Cerrar sesión
                    </Dropdown.Item>
                  )}
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
    </>
  );
}
