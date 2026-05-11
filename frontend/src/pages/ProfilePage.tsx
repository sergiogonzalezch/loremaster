import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
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
import {
  getMyProfile,
  updateMyProfile,
  uploadMyAvatar,
  deleteMyAvatar,
  getMyAvatar,
} from "../api/users";
import SafeImage from "../components/SafeImage";
import { parseApiError } from "../utils/errors";
import { formatDate } from "../utils/formatters";
import type { UserProfile, UpdateProfileRequest } from "../types/user";

/**
 * Página de edición del perfil del usuario autenticado.
 *
 * Permite modificar el nombre para mostrar, la biografía y el correo
 * electrónico, así como subir o eliminar la foto de perfil.
 */
export default function ProfilePage() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [email, setEmail] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  useEffect(() => {
    Promise.all([getMyProfile(), getMyAvatar()])
      .then(([p, avatar]) => {
        setProfile(p);
        setDisplayName(p.display_name ?? "");
        setBio(p.bio ?? "");
        setAvatarUrl(avatar.avatar_url ?? "");
        setEmail("");
      })
      .catch((e) => setError(parseApiError(e).text))
      .finally(() => setLoading(false));
  }, []);

  /**
   * Valida y sube un nuevo archivo de imagen como avatar del usuario.
   *
   * @param e - Evento de cambio del input de tipo archivo.
   */
  async function handleAvatarUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ["image/jpeg", "image/png", "image/webp", "image/gif"];
    if (!allowedTypes.includes(file.type)) {
      setError("Solo se permiten imágenes (JPEG, PNG, WebP, GIF).");
      return;
    }

    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
      setError("La imagen excede el tamaño máximo de 5MB.");
      return;
    }

    setUploadingAvatar(true);
    setError(null);

    try {
      const result = await uploadMyAvatar(file);
      setAvatarUrl(result.avatar_url ?? "");
    } catch (e) {
      setError(parseApiError(e).text);
    } finally {
      setUploadingAvatar(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  /**
   * Elimina el avatar actual del usuario.
   */
  async function handleDeleteAvatar() {
    setError(null);
    try {
      await deleteMyAvatar();
      setAvatarUrl("");
    } catch (e) {
      setError(parseApiError(e).text);
    }
  }

  /**
   * Envía los cambios del perfil al backend, actualizando solo
   * los campos que han sido modificados.
   *
   * @param e - Evento del formulario de perfil.
   */
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);

    const patch: UpdateProfileRequest = {};
    if (displayName !== (profile?.display_name ?? ""))
      patch.display_name = displayName || null;
    if (bio !== (profile?.bio ?? "")) patch.bio = bio || null;
    if (email) patch.email = email;

    try {
      const updated = await updateMyProfile(patch);
      setProfile(updated);
      setDisplayName(updated.display_name ?? "");
      setBio(updated.bio ?? "");
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
        <button
          onClick={() => navigate(-1)}
          className="btn btn-sm btn-outline-secondary mb-3"
          style={{ fontSize: "0.8rem" }}
        >
          ← Volver
        </button>
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
                    Foto de perfil
                  </Form.Label>
                  <div className="d-flex align-items-center gap-3">
                    {avatarUrl ? (
                      <SafeImage
                        src={avatarUrl}
                        alt="Avatar"
                        style={{
                          width: "80px",
                          height: "80px",
                          borderRadius: "50%",
                          objectFit: "cover",
                          border: "2px solid var(--lm-accent)",
                        }}
                      />
                    ) : (
                      <div
                        style={{
                          width: "80px",
                          height: "80px",
                          borderRadius: "50%",
                          backgroundColor: "var(--lm-bg-secondary)",
                          border: "2px dashed var(--lm-accent)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "var(--lm-accent)",
                          fontSize: "1.5rem",
                        }}
                      >
                        <i className="bi bi-person" />
                      </div>
                    )}
                    <div className="d-flex flex-column gap-2">
                      <div className="d-flex gap-2">
                        <Button
                          variant="outline-primary"
                          size="sm"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={uploadingAvatar}
                        >
                          {uploadingAvatar ? (
                            <Spinner animation="border" size="sm" />
                          ) : (
                            <>
                              <i className="bi bi-upload me-1" />
                              {avatarUrl ? "Cambiar" : "Subir"}
                            </>
                          )}
                        </Button>
                        {avatarUrl && (
                          <Button
                            variant="outline-danger"
                            size="sm"
                            onClick={handleDeleteAvatar}
                          >
                            <i className="bi bi-trash me-1" />
                            Eliminar
                          </Button>
                        )}
                      </div>
                      <Form.Text className="text-muted mb-0">
                        JPEG, PNG, WebP, GIF · Máx 5MB
                      </Form.Text>
                    </div>
                  </div>
                  <Form.Control
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    onChange={handleAvatarUpload}
                    className="d-none"
                  />
                </Form.Group>

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
