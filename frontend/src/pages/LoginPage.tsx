import { useEffect, useState } from "react";
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
import { SignIn } from "@clerk/clerk-react";
import { login, register } from "../api/auth";
import { useAuth } from "../hooks/useAuth";
import { parseApiError } from "../utils/errors";
import StarfieldCanvas from "../components/StarfieldCanvas";
import { clerkKey } from "../utils/clerkConfig";

interface LoginForm {
  username_or_email: string;
  password: string;
}

interface RegisterForm {
  username: string;
  email: string;
  password: string;
}

/**
 * Página de autenticación con Clerk (demo/production).
 *
 * ClerkBridge en App.tsx detecta el login y sincroniza la sesión con el
 * backend antes de navegar a "/". Esta página solo muestra el widget de Clerk.
 */
function ClerkLoginPage() {
  return (
    <>
      <StarfieldCanvas />
      <Container
        className="d-flex align-items-center justify-content-center"
        style={{ minHeight: "100vh", position: "relative", zIndex: 1 }}
      >
        <SignIn />
      </Container>
    </>
  );
}

/**
 * Página de inicio de sesión y registro de usuarios (modo local).
 *
 * Permite autenticarse con nombre de usuario o correo electrónico,
 * o crear una nueva cuenta. Muestra un fondo animado de estrellas
 * y un formulario centralizado con pestañas para alternar entre
 * los modos de login y registro.
 */
function LocalLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login: contextLogin } = useAuth();
  const from = (location.state as { from?: string } | null)?.from;
  // Solo rutas internas — descarta cualquier valor que no empiece por "/" para evitar open redirect
  const redirectTo = from?.startsWith("/") ? from : "/";
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
  // Brute-force protection: delay progresivo tras intentos fallidos de login.
  // 1.º fallo: sin espera. 2.º: 2s. 3.º: 4s. 4.º: 8s. 5.º+: 30s (cap).
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [retryAfter, setRetryAfter] = useState(0);

  useEffect(() => {
    if (retryAfter <= 0) return;
    const timer = setTimeout(() => setRetryAfter((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [retryAfter]);

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    if (retryAfter > 0) return;
    setError(null);
    setLoading(true);
    try {
      await login(loginForm);
      setFailedAttempts(0);
      await contextLogin();
      navigate(redirectTo, { replace: true });
    } catch (err) {
      const { text } = parseApiError(err);
      setError(text);
      const next = failedAttempts + 1;
      setFailedAttempts(next);
      if (next >= 2) setRetryAfter(Math.min(2 ** (next - 1), 30));
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
                        setLoginForm((prev) => ({
                          ...prev,
                          username_or_email: e.target.value,
                        }))
                      }
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
                        setLoginForm((prev) => ({
                          ...prev,
                          password: e.target.value,
                        }))
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
                        setRegisterForm((prev) => ({
                          ...prev,
                          username: e.target.value,
                        }))
                      }
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
                        setRegisterForm((prev) => ({
                          ...prev,
                          email: e.target.value,
                        }))
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
                        setRegisterForm((prev) => ({
                          ...prev,
                          password: e.target.value,
                        }))
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
                disabled={loading || retryAfter > 0}
                style={{
                  backgroundColor: "var(--lm-accent)",
                  borderColor: "var(--lm-accent)",
                }}
              >
                {retryAfter > 0
                  ? `Espera ${retryAfter}s…`
                  : loading
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

export default function LoginPage() {
  return clerkKey ? <ClerkLoginPage /> : <LocalLoginPage />;
}
