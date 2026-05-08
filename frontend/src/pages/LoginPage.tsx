import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  Container,
  Card,
  Form,
  Button,
  Alert,
  Tabs,
  Tab,
} from "react-bootstrap";
import { login, register } from "../api/auth";
import { useAuth } from "../hooks/useAuth";
import { parseApiError } from "../utils/errors";
import StarfieldCanvas from "../components/StarfieldCanvas";

interface LoginForm {
  username_or_email: string;
  password: string;
}

interface RegisterForm {
  username: string;
  email: string;
  password: string;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const { login: contextLogin } = useAuth();
  const [tab, setTab] = useState<string>("login");
  const [loginForm, setLoginForm] = useState<LoginForm>({
    username_or_email: "",
    password: "",
  });
  const [registerForm, setRegisterForm] = useState<RegisterForm>({
    username: "",
    email: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access_token } = await login(loginForm);
      contextLogin(access_token);
      navigate("/", { replace: true });
    } catch (err) {
      const { text } = parseApiError(err);
      setError(text);
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register(registerForm);
      setSuccess("Usuario creado correctamente. Ya puedes iniciar sesión.");
      setRegisterForm({ username: "", email: "", password: "" });
      setTab("login");
      setLoginForm({ username_or_email: registerForm.username, password: "" });
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

            <Form onSubmit={tab === "login" ? handleLogin : handleRegister}>
              {tab === "login" ? (
                <>
                  <Form.Group className="mb-3">
                    <Form.Label>Usuario o correo electrónico</Form.Label>
                    <Form.Control
                      type="text"
                      value={loginForm.username_or_email}
                      onChange={(e) =>
                        setLoginForm({
                          ...loginForm,
                          username_or_email: e.target.value,
                        })
                      }
                      autoFocus
                      required
                      disabled={loading}
                    />
                  </Form.Group>
                  <Form.Group className="mb-4">
                    <Form.Label>Contraseña</Form.Label>
                    <Form.Control
                      type="password"
                      value={loginForm.password}
                      onChange={(e) =>
                        setLoginForm({ ...loginForm, password: e.target.value })
                      }
                      required
                      disabled={loading}
                    />
                  </Form.Group>
                </>
              ) : (
                <>
                  <Form.Group className="mb-3">
                    <Form.Label>Usuario</Form.Label>
                    <Form.Control
                      type="text"
                      value={registerForm.username}
                      onChange={(e) =>
                        setRegisterForm({
                          ...registerForm,
                          username: e.target.value,
                        })
                      }
                      autoFocus
                      required
                      disabled={loading}
                    />
                  </Form.Group>
                  <Form.Group className="mb-3">
                    <Form.Label>Correo electrónico</Form.Label>
                    <Form.Control
                      type="email"
                      value={registerForm.email}
                      onChange={(e) =>
                        setRegisterForm({
                          ...registerForm,
                          email: e.target.value,
                        })
                      }
                      required
                      disabled={loading}
                    />
                  </Form.Group>
                  <Form.Group className="mb-4">
                    <Form.Label>Contraseña</Form.Label>
                    <Form.Control
                      type="password"
                      value={registerForm.password}
                      onChange={(e) =>
                        setRegisterForm({
                          ...registerForm,
                          password: e.target.value,
                        })
                      }
                      required
                      disabled={loading}
                    />
                  </Form.Group>
                </>
              )}
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
