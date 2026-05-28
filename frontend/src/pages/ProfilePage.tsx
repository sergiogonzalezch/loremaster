import { useEffect, useReducer, useRef, useState } from "react";
import type { FormEvent, Reducer } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
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

// Estado de status: loading, saving, uploadingAvatar, error y success.
type StatusState = {
  loading: boolean;
  saving: boolean;
  uploadingAvatar: boolean;
  error: string | null;
  success: boolean;
};

type StatusAction =
  | { type: "INIT_DONE" }
  | { type: "INIT_ERROR"; error: string }
  | { type: "SAVE_START" }
  | { type: "SAVE_OK" }
  | { type: "SAVE_ERROR"; error: string }
  | { type: "UPLOAD_START" }
  | { type: "UPLOAD_DONE" }
  | { type: "UPLOAD_ERROR"; error: string }
  | { type: "SHOW_ERROR"; error: string }
  | { type: "DISMISS_ERROR" }
  | { type: "DISMISS_SUCCESS" };

const statusReducer: Reducer<StatusState, StatusAction> = (state, action) => {
  switch (action.type) {
    case "INIT_DONE":
      return { ...state, loading: false };
    case "INIT_ERROR":
      return { ...state, loading: false, error: action.error };
    case "SAVE_START":
      return { ...state, saving: true, error: null, success: false };
    case "SAVE_OK":
      return { ...state, saving: false, success: true };
    case "SAVE_ERROR":
      return { ...state, saving: false, error: action.error };
    case "UPLOAD_START":
      return { ...state, uploadingAvatar: true, error: null };
    case "UPLOAD_DONE":
      return { ...state, uploadingAvatar: false };
    case "UPLOAD_ERROR":
      return { ...state, uploadingAvatar: false, error: action.error };
    case "SHOW_ERROR":
      return { ...state, error: action.error };
    case "DISMISS_ERROR":
      return { ...state, error: null };
    case "DISMISS_SUCCESS":
      return { ...state, success: false };
  }
};

// Form state: 3 campos relacionados.
type FormState = { displayName: string; bio: string; email: string };
type FormAction =
  | { type: "RESET"; displayName: string; bio: string }
  | { type: "SET_DISPLAY"; value: string }
  | { type: "SET_BIO"; value: string }
  | { type: "SET_EMAIL"; value: string };

const formReducer: Reducer<FormState, FormAction> = (state, action) => {
  switch (action.type) {
    case "RESET":
      return { displayName: action.displayName, bio: action.bio, email: "" };
    case "SET_DISPLAY":
      return { ...state, displayName: action.value };
    case "SET_BIO":
      return { ...state, bio: action.value };
    case "SET_EMAIL":
      return { ...state, email: action.value };
  }
};

/**
 * Página de edición del perfil del usuario autenticado.
 *
 * Permite modificar el nombre para mostrar, la biografía y el correo
 * electrónico, así como subir o eliminar la foto de perfil.
 */
export default function ProfilePage() {
  const navigate = useNavigate();
  const { setAvatarUrl: setContextAvatarUrl } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [avatarUrl, setAvatarUrl] = useState("");
  const [status, dispatchStatus] = useReducer(statusReducer, {
    loading: true,
    saving: false,
    uploadingAvatar: false,
    error: null,
    success: false,
  });
  const { loading, saving, uploadingAvatar, error, success } = status;
  const [form, dispatchForm] = useReducer(formReducer, {
    displayName: "",
    bio: "",
    email: "",
  });
  const { displayName, bio, email } = form;
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([getMyProfile(), getMyAvatar()])
      .then(([p, avatar]) => {
        setProfile(p);
        dispatchForm({
          type: "RESET",
          displayName: p.display_name ?? "",
          bio: p.bio ?? "",
        });
        const url = avatar.avatar_url;
        setAvatarUrl(url ? `${url}?t=${Date.now()}` : "");
        dispatchStatus({ type: "INIT_DONE" });
      })
      .catch((e) =>
        dispatchStatus({ type: "INIT_ERROR", error: parseApiError(e).text }),
      );
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
      dispatchStatus({
        type: "SHOW_ERROR",
        error: "Solo se permiten imágenes (JPEG, PNG, WebP, GIF).",
      });
      return;
    }

    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
      dispatchStatus({
        type: "SHOW_ERROR",
        error: "La imagen excede el tamaño máximo de 5MB.",
      });
      return;
    }

    dispatchStatus({ type: "UPLOAD_START" });
    try {
      const result = await uploadMyAvatar(file);
      const url = result.avatar_url;
      const busted = url ? `${url}?t=${Date.now()}` : "";
      setAvatarUrl(busted);
      setContextAvatarUrl(busted || null);
      dispatchStatus({ type: "UPLOAD_DONE" });
    } catch (e) {
      dispatchStatus({ type: "UPLOAD_ERROR", error: parseApiError(e).text });
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDeleteAvatar() {
    dispatchStatus({ type: "DISMISS_ERROR" });
    try {
      await deleteMyAvatar();
      setAvatarUrl("");
      setContextAvatarUrl(null);
    } catch (e) {
      dispatchStatus({ type: "SHOW_ERROR", error: parseApiError(e).text });
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    dispatchStatus({ type: "SAVE_START" });

    const patch: UpdateProfileRequest = {};
    if (displayName !== (profile?.display_name ?? ""))
      patch.display_name = displayName || null;
    if (bio !== (profile?.bio ?? "")) patch.bio = bio || null;
    if (email) patch.email = email;

    try {
      const updated = await updateMyProfile(patch);
      setProfile(updated);
      dispatchForm({
        type: "RESET",
        displayName: updated.display_name ?? "",
        bio: updated.bio ?? "",
      });
      dispatchStatus({ type: "SAVE_OK" });
    } catch (e) {
      dispatchStatus({ type: "SAVE_ERROR", error: parseApiError(e).text });
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
          type="button"
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
                  onClose={() => dispatchStatus({ type: "DISMISS_ERROR" })}
                >
                  {error}
                </Alert>
              )}
              {success && (
                <Alert
                  variant="success"
                  dismissible
                  onClose={() => dispatchStatus({ type: "DISMISS_SUCCESS" })}
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
                      <div className="lm-avatar-placeholder">
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
                    onChange={(e) =>
                      dispatchForm({ type: "SET_DISPLAY", value: e.target.value })
                    }
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
                    onChange={(e) =>
                      dispatchForm({ type: "SET_BIO", value: e.target.value })
                    }
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
                    onChange={(e) =>
                      dispatchForm({ type: "SET_EMAIL", value: e.target.value })
                    }
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
                      Guardando…
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
