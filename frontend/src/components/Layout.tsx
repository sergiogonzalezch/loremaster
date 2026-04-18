import { Navbar, Container } from "react-bootstrap";
import { Link, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <>
      <Navbar variant="dark">
        <Container fluid="lg">
          <Navbar.Brand as={Link} to="/">
            <span className="lm-brand-glyph">✦</span>
            <span className="lore">Lore</span>
            <span>Master</span>
          </Navbar.Brand>
        </Container>
      </Navbar>
      <Container fluid="lg" className="py-4">
        <Outlet />
      </Container>
    </>
  );
}