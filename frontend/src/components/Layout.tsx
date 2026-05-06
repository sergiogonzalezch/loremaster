import { Navbar, Container, Button } from "react-bootstrap";
import { Link, Outlet, useNavigate } from "react-router-dom";
import StarfieldCanvas from "./StarfieldCanvas";
import { removeToken } from "../utils/token";

export default function Layout() {
  const navigate = useNavigate();

  function handleLogout() {
    removeToken();
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
          <Button variant="outline-secondary" size="sm" onClick={handleLogout}>
            Cerrar sesión
          </Button>
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
