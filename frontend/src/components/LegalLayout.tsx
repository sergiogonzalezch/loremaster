import { Container, Card } from "react-bootstrap";
import { Link } from "react-router-dom";
import StarfieldCanvas from "./StarfieldCanvas";
import AppNavbar from "./AppNavbar";
import AppFooter from "./AppFooter";
import MarkdownContent from "./MarkdownContent";

interface LegalLayoutProps {
  /** Título del documento legal (se muestra como encabezado). */
  title: string;
  /** Fecha de última actualización en texto legible. */
  lastUpdated: string;
  /** Cuerpo del documento en formato Markdown. */
  content: string;
}

/** Enlaces de navegación entre los tres documentos legales. */
const LEGAL_LINKS = [
  { to: "/terms", label: "Términos y Condiciones" },
  { to: "/privacy", label: "Política de Privacidad" },
  { to: "/ai-notice", label: "Aviso de uso de IA" },
] as const;

/**
 * Chrome público reutilizable para las páginas legales (Términos, Privacidad,
 * Aviso de IA). Replica la estructura de las páginas públicas (StarfieldCanvas
 * + AppNavbar + AppFooter) y renderiza el contenido Markdown sanitizado.
 */
export default function LegalLayout({
  title,
  lastUpdated,
  content,
}: LegalLayoutProps) {
  return (
    <>
      <StarfieldCanvas />
      <div
        style={{
          position: "relative",
          zIndex: 1,
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <AppNavbar />

        <Container fluid="lg" className="py-5" style={{ flex: 1 }}>
          <div style={{ maxWidth: 820, margin: "0 auto" }}>
            <h1
              style={{
                fontFamily: "var(--lm-font-head)",
                color: "var(--lm-accent)",
              }}
            >
              {title}
            </h1>
            <p className="text-muted mb-4">
              Última actualización: {lastUpdated}
            </p>

            <Card body className="bg-dark bg-opacity-50">
              <MarkdownContent>{content}</MarkdownContent>

              <hr className="my-4" />
              <p className="text-muted small mb-0">
                Este documento es una plantilla orientativa adaptada a este
                proyecto y <strong>no constituye asesoría legal</strong>. Para un
                uso comercial real, conviene revisarlo con un profesional.
              </p>
            </Card>

            <nav className="d-flex flex-wrap gap-3 mt-4">
              {LEGAL_LINKS.filter((l) => l.label !== title).map((l) => (
                <Link key={l.to} to={l.to} className="lm-footer-author">
                  {l.label}
                </Link>
              ))}
              <Link to="/" className="text-muted ms-auto">
                ← Volver al inicio
              </Link>
            </nav>
          </div>
        </Container>

        <AppFooter />
      </div>
    </>
  );
}
