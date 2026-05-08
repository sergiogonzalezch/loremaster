import { Container } from "react-bootstrap";
import { Outlet } from "react-router-dom";
import StarfieldCanvas from "./StarfieldCanvas";
import AppNavbar from "./AppNavbar";

export default function Layout() {
  return (
    <>
      <StarfieldCanvas />
      <AppNavbar />
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
