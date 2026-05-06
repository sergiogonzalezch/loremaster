import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Card, Form, Button, Alert, Tabs, Tab } from "react-bootstrap";
import { login, register } from "../api/auth";
import { setToken } from "../utils/token";
import { parseApiError } from "../utils/errors";
import StarfieldCanvas from "../components/StarfieldCanvas";

export default function LoginPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<string>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const fn = tab === "login" ? login : register;
      const { access_token } = await fn({ username, password });
      setToken(access_token);
      navigate("/", { replace: true });
    } catch (err) {
      const { text } = parseApiError(err);
      setError(text);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <StarfieldCanvas />
      <Container
        className="d-flex align-items-center justify-content-center"
        style={{ minHeight: "100vh", position: "relative", zIndex: 1 }}
      >
        <Card style={{ width: "100%", maxWidth: 420 }}>
          <Card.Body className="p-4">
            <div className="text-center mb-4">
              <span className="lm-brand-glyph" style={{ fontSize: "2rem" }}>✦</span>
              <h1 className="h4 mt-2 mb-0" style={{ fontFamily: "var(--lm-font-head)" }}>
                <span style={{ color: "var(--lm-accent)" }}>Lore</span>Master
              </h1>
            </div>

            <Tabs activeKey={tab} onSelect={(k) => { setTab(k ?? "login"); setError(null); }} className="mb-3">
              <Tab eventKey="login" title="Iniciar sesión" />
              <Tab eventKey="register" title="Registrarse" />
            </Tabs>

            {error && <Alert variant="warning">{error}</Alert>}

            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-3">
                <Form.Label>Usuario</Form.Label>
                <Form.Control
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoFocus
                  required
                  disabled={loading}
                />
              </Form.Group>
              <Form.Group className="mb-4">
                <Form.Label>Contraseña</Form.Label>
                <Form.Control
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                />
              </Form.Group>
              <Button type="submit" className="w-100" disabled={loading}>
                {loading
                  ? "Cargando..."
                  : tab === "login"
                    ? "Iniciar sesión"
                    : "Crear cuenta"}
              </Button>
            </Form>
          </Card.Body>
        </Card>
      </Container>
    </>
  );
}
