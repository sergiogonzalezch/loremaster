import { Navbar, Container } from "react-bootstrap";
import { Link, Outlet } from "react-router-dom";
import StarfieldCanvas from "./StarfieldCanvas";

export default function Layout() {
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
        </Container>
      </Navbar>
      <Container fluid="lg" className="py-4" style={{ position: "relative", zIndex: 1 }}>
        <Outlet />
      </Container>
    </>
  );
}
