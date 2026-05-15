/**
 * Layout principal con Navbar y contenedor de páginas.
 *
 * Incluye el canvas de estrellas de fondo y el Outlet de React Router
 * para renderizar las páginas hijas.
 */

import { Container } from "react-bootstrap";
import { Outlet } from "react-router-dom";
import StarfieldCanvas from "./StarfieldCanvas";
import AppNavbar from "./AppNavbar";
import AppFooter from "./AppFooter";

export default function Layout() {
  return (
    <div
      style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}
    >
      <StarfieldCanvas />
      <AppNavbar />
      <Container
        fluid="lg"
        className="py-4"
        style={{ position: "relative", zIndex: 1, flex: 1 }}
      >
        <Outlet />
      </Container>
      <AppFooter />
    </div>
  );
}
