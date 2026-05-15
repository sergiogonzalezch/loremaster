import { Container } from "react-bootstrap";

const YEAR = new Date().getFullYear();
const GITHUB_URL = "https://github.com/sergiogonzalezch/loremaster";

const STACK = ["React 19", "FastAPI", "Qdrant", "Ollama", "SQLModel"];

function GithubIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      style={{ width: 16, height: 16, flexShrink: 0 }}
      aria-hidden="true"
    >
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}

export default function AppFooter() {
  return (
    <footer className="lm-footer">
      <Container fluid="lg">
        <div className="lm-footer-body">
          <div className="lm-footer-brand">
            <div className="lm-footer-logo">
              <span className="lm-brand-glyph" style={{ fontSize: "1rem" }}>
                ✦
              </span>
              <span
                style={{
                  fontFamily: "var(--lm-font-head)",
                  fontSize: "1rem",
                  letterSpacing: "0.03em",
                }}
              >
                <span style={{ color: "var(--lm-accent)" }}>Lore</span>Master
              </span>
            </div>
            <p className="lm-footer-tagline">
              Herramienta RAG para worldbuilding colaborativo con IA.
              <br />
              Crea mundos, genera lore, da vida a tus entidades.
            </p>
            <div className="lm-footer-stack">
              {STACK.map((tech, i) => (
                <span key={tech} className="lm-footer-chip">
                  {tech}
                  {i < STACK.length - 1 && (
                    <span className="lm-footer-dot">·</span>
                  )}
                </span>
              ))}
            </div>
          </div>

          <div className="lm-footer-links">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="lm-footer-github-btn"
            >
              <GithubIcon />
              Ver en GitHub
            </a>
            <div className="lm-footer-credit">
              <span className="lm-footer-credit-label">Desarrollado por</span>
              <a
                href="https://github.com/sergiogonzalezch"
                target="_blank"
                rel="noopener noreferrer"
                className="lm-footer-author"
              >
                Sergio González
              </a>
            </div>
          </div>
        </div>

        <div className="lm-footer-bottom">
          <span className="lm-footer-sep">
            ✦ ── ── ── ── ── ── ── ── ── ── ✦
          </span>
          <span className="lm-footer-copy">
            © {YEAR} LoreMaster — open source bajo MIT
          </span>
        </div>
      </Container>
    </footer>
  );
}
