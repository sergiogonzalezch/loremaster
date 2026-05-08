import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  Container,
  Row,
  Col,
  Card,
  Form,
  Button,
  Alert,
  Spinner,
} from "react-bootstrap";
import { getMyProfile, updateMyProfile } from "../api/users";
import { parseApiError } from "../utils/errors";
import { formatDate } from "../utils/formatters";
import type { UserProfile, UpdateProfileRequest } from "../types/user";

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    getMyProfile()
      .then((p) => {
        setProfile(p);
        setDisplayName(p.display_name ?? "");
        setBio(p.bio ?? "");
        setAvatarUrl(p.avatar_url ?? "");
        setEmail("");
      })
      .catch((e) => setError(parseApiError(e).text))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);

    const patch: UpdateProfileRequest = {};
    if (displayName !== (profile?.display_name ?? ""))
      patch.display_name = displayName || null;
    if (bio !== (profile?.bio ?? "")) patch.bio = bio || null;
    if (avatarUrl !== (profile?.avatar_url ?? ""))
      patch.avatar_url = avatarUrl || null;
    if (email) patch.email = email;

    try {
      const updated = await updateMyProfile(patch);
      setProfile(updated);
      setDisplayName(updated.display_name ?? "");
      setBio(updated.bio ?? "");
      setAvatarUrl(updated.avatar_url ?? "");
      setEmail("");
      setSuccess(true);
    } catch (e) {
      setError(parseApiError(e).text);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="d-flex justify-content-center py-5">
        <Spinner animation="border" style={{ color: "var(--lm-accent)" }} />
      </div>
    );
  }

  return (
    <Container fluid="lg" className="py-5">
      <div className="mb-4">
        <h1
          style={{
            fontFamily: "var(--lm-font-head)",
            fontSize: "clamp(1.4rem, 3vw, 2rem)",
          }}
        >
          Mi <span style={{ color: "var(--lm-accent)" }}>perfil</span>
        </h1>
        {profile && (
          <p className="text-muted mb-0" style={{ fontSize: "0.85rem" }}>
            @{profile.username} · Cuenta creada el{" "}
            {formatDate(profile.created_at)}
          </p>
        )}
      </div>

      <Row>
        <Col md={7} lg={6}>
          <Card className="lm-collection-card">
            <Card.Body className="p-4">
              {error && (
                <Alert
                  variant="danger"
                  dismissible
                  onClose={() => setError(null)}
                >
                  {error}
                </Alert>
              )}
              {success && (
                <Alert
                  variant="success"
                  dismissible
                  onClose={() => setSuccess(false)}
                >
                  Perfil actualizado correctamente.
                </Alert>
              )}
              <Form onSubmit={handleSubmit}>
                <Form.Group className="mb-3">
                  <Form.Label className="small text-muted">
                    Nombre para mostrar
                  </Form.Label>
                  <Form.Control
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="Tu nombre o alias"
                    maxLength={100}
                  />
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label className="small text-muted">
                    Biografía
                  </Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    placeholder="Cuéntanos algo sobre ti..."
                    maxLength={500}
                  />
                  <Form.Text className="text-muted">{bio.length}/500</Form.Text>
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label className="small text-muted">
                    URL de avatar
                  </Form.Label>
                  <Form.Control
                    type="url"
                    value={avatarUrl}
                    onChange={(e) => setAvatarUrl(e.target.value)}
                    placeholder="https://..."
                  />
                </Form.Group>

                <Form.Group className="mb-4">
                  <Form.Label className="small text-muted">
                    Cambiar correo electrónico
                  </Form.Label>
                  <Form.Control
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Dejar vacío para no cambiar"
                  />
                </Form.Group>

                <Button
                  type="submit"
                  disabled={saving}
                  style={{
                    backgroundColor: "var(--lm-accent)",
                    borderColor: "var(--lm-accent)",
                    color: "#000",
                  }}
                >
                  {saving ? (
                    <>
                      <Spinner animation="border" size="sm" className="me-2" />
                      Guardando...
                    </>
                  ) : (
                    "Guardar cambios"
                  )}
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
}
