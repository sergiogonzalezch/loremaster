import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Container,
  Card,
  Form,
  Button,
  Alert,
  Tabs,
  Tab,
} from "react-bootstrap";
import { login as apiLogin, register } from "../api/auth";
import { useAuth } from "../hooks/useAuth";
import { parseApiError } from "../utils/errors";
import StarfieldCanvas from "../components/StarfieldCanvas";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string })?.from ?? "/feed";
  const { login } = useAuth();
  const [tab, setTab] = useState<string>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      if (tab === "login") {
        const { access_token } = await apiLogin({ username, password });
        login(access_token);
        navigate(from, { replace: true });
      } else {
        await register({ username, password });
        setSuccess("Usuario creado correctamente. Ya puedes iniciar sesión.");
        setUsername("");
        setPassword("");
        setTab("login");
      }
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
              <span className="lm-brand-glyph" style={{ fontSize: "2rem" }}>
                ✦
              </span>
              <h1
                className="h4 mt-2 mb-0"
                style={{ fontFamily: "var(--lm-font-head)" }}
              >
                <span style={{ color: "var(--lm-accent)" }}>Lore</span>Master
              </h1>
            </div>

            <Tabs
              activeKey={tab}
              onSelect={(k) => {
                setTab(k ?? "login");
                setError(null);
                setSuccess(null);
              }}
              className="mb-3"
            >
              <Tab eventKey="login" title="Iniciar sesión" />
              <Tab eventKey="register" title="Registrarse" />
            </Tabs>

            {success && <Alert variant="success">{success}</Alert>}
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
              <Button
                type="submit"
                className="w-100"
                disabled={loading}
                style={{
                  backgroundColor: "var(--lm-accent)",
                  borderColor: "var(--lm-accent)",
                }}
              >
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
