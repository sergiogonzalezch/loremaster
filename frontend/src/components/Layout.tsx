import { Navbar, Container, Button } from "react-bootstrap";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import StarfieldCanvas from "./StarfieldCanvas";
import { useAuth } from "../hooks/useAuth";

export default function Layout() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <>
      <StarfieldCanvas />
      <Navbar variant="dark">
        <Container fluid="lg">
          <Navbar.Brand as={Link} to="/">
            <span className="lm-brand-glyph">✦</span>
            <span className="lore">Lore</span>
            <span>Master</span>
          </Navbar.Brand>
          <div className="d-flex align-items-center gap-3 ms-auto">
            {user?.is_admin && (
              <NavLink
                to="/admin"
                style={({ isActive }) => ({
                  color: isActive
                    ? "var(--lm-accent)"
                    : "rgba(255,255,255,0.55)",
                  textDecoration: "none",
                  fontSize: "0.82rem",
                  fontFamily: "var(--lm-font-head)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                })}
              >
                Admin
              </NavLink>
            )}
            <Navbar.Text>{user?.username}</Navbar.Text>
            <Button
              variant="outline-secondary"
              size="sm"
              onClick={handleLogout}
            >
              Cerrar sesión
            </Button>
          </div>
        </Container>
      </Navbar>
      <Container
        fluid="lg"
        className="py-4"
        style={{ position: "relative", zIndex: 1 }}
      >
        <Outlet />
      </Container>
    </>
  );
}
