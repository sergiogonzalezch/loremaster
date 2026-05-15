import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  Container,
  Row,
  Col,
  Card,
  Alert,
  Spinner,
  Badge,
} from "react-bootstrap";
import { getPublicProfile } from "../api/users";
import StarfieldCanvas from "../components/StarfieldCanvas";
import AppNavbar from "../components/AppNavbar";
import AppFooter from "../components/AppFooter";
import MarkdownContent from "../components/MarkdownContent";
import PublicContentModal from "../components/PublicContentModal";
import PublicImageModal from "../components/PublicImageModal";
import SafeImage from "../components/SafeImage";
import { parseApiError } from "../utils/errors";
import { formatDate } from "../utils/formatters";
import { CATEGORY_LABELS, ENTITY_TYPE_LABELS } from "../utils/constants";
import type {
  PublicProfile,
  SharedContentItem,
  SharedImageItem,
} from "../types/user";

/**
 * Página de perfil público de un usuario.
 *
 * Muestra la información pública del usuario (nombre, bio, avatar),
 * sus imágenes compartidas y el lore público que ha compartido.
 * Permite copiar el enlace al perfil y, si es el usuario autenticado,
 * navegar a la edición de su perfil.
 */
export default function PublicProfilePage() {
  const { username } = useParams<{ username: string }>();
  const navigate = useNavigate();
  const { user: authUser } = useAuth();
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedContent, setSelectedContent] =
    useState<SharedContentItem | null>(null);
  const [selectedImage, setSelectedImage] = useState<SharedImageItem | null>(
    null,
  );

  useEffect(() => {
    if (!username) return;
    setLoading(true);
    setError(null);
    getPublicProfile(username)
      .then(setProfile)
      .catch((e) => setError(parseApiError(e).text))
      .finally(() => setLoading(false));
  }, [username, refreshKey]);

  useEffect(() => {
    function handleVisibility() {
      if (document.visibilityState === "visible") {
        setRefreshKey((k) => k + 1);
      }
    }
    document.addEventListener("visibilitychange", handleVisibility);
    return () =>
      document.removeEventListener("visibilitychange", handleVisibility);
  }, []);

  const initials = (profile?.display_name ?? profile?.username ?? "?")
    .slice(0, 2)
    .toUpperCase();

  /**
   * Copia la URL actual del perfil al portapapeles y muestra
   * una confirmación temporal.
   */
  function handleShare() {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

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

        <Container fluid="lg" className="py-5">
          {loading ? (
            <div className="d-flex justify-content-center py-5">
              <Spinner
                animation="border"
                style={{ color: "var(--lm-accent)" }}
              />
            </div>
          ) : error ? (
            <Alert variant="warning">{error}</Alert>
          ) : profile ? (
            <>
              <div className="d-flex align-items-center gap-4 mb-5 flex-wrap">
                {profile.avatar_url ? (
                  <SafeImage
                    src={profile.avatar_url}
                    alt={profile.display_name ?? profile.username}
                    style={{
                      width: 72,
                      height: 72,
                      borderRadius: "50%",
                      objectFit: "cover",
                      border: "2px solid var(--lm-accent)",
                      flexShrink: 0,
                    }}
                  />
                ) : (
                  <div
                    style={{
                      width: 72,
                      height: 72,
                      borderRadius: "50%",
                      background:
                        "linear-gradient(135deg, var(--lm-accent) 0%, rgba(255,200,50,0.3) 100%)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "1.5rem",
                      fontFamily: "var(--lm-font-head)",
                      fontWeight: 700,
                      color: "#000",
                      flexShrink: 0,
                    }}
                  >
                    {initials}
                  </div>
                )}
                <div>
                  <h1
                    style={{
                      fontFamily: "var(--lm-font-head)",
                      fontSize: "clamp(1.4rem, 3vw, 2.2rem)",
                      marginBottom: 2,
                    }}
                  >
                    {profile.display_name ?? profile.username}
                  </h1>
                  {profile.display_name && (
                    <p
                      className="text-muted mb-1"
                      style={{ fontSize: "0.9rem" }}
                    >
                      @{profile.username}
                    </p>
                  )}
                  {profile.bio && (
                    <p className="text-muted mb-0" style={{ maxWidth: 520 }}>
                      {profile.bio}
                    </p>
                  )}
                </div>
                <div className="ms-auto d-flex align-items-center gap-2">
                  <button
                    onClick={handleShare}
                    className="btn btn-outline-light"
                    title="Compartir perfil"
                    style={{ fontSize: "0.85rem" }}
                  >
                    ↗ {copied ? "¡Copiado!" : "Compartir"}
                  </button>
                  {authUser?.username === username && (
                    <button
                      onClick={() => navigate("/profile")}
                      className="btn btn-outline-light"
                      title="Editar perfil"
                      style={{ fontSize: "1rem" }}
                    >
                      ⚙
                    </button>
                  )}
                </div>
              </div>

              {profile.shared_images.length > 0 && (
                <section className="mb-5">
                  <h2
                    style={{
                      fontFamily: "var(--lm-font-head)",
                      fontSize: "1.1rem",
                      color: "var(--lm-accent)",
                      textTransform: "uppercase",
                      letterSpacing: "0.12em",
                      marginBottom: "1.2rem",
                    }}
                  >
                    Imágenes ({profile.shared_images.length})
                  </h2>
                  <Row className="g-3">
                    {profile.shared_images.map((img) => (
                      <Col key={img.id} xs={6} sm={4} md={3}>
                        <div
                          role="button"
                          tabIndex={0}
                          className="lm-shared-image-card"
                          style={{
                            position: "relative",
                            borderRadius: 8,
                            overflow: "hidden",
                            border: "1px solid var(--lm-border)",
                            aspectRatio: "1",
                          }}
                          onClick={() => setSelectedImage(img)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ")
                              setSelectedImage(img);
                          }}
                        >
                          {img.image_url ? (
                            <SafeImage
                              src={img.image_url}
                              alt={img.entity_name}
                              style={{
                                width: "100%",
                                height: "100%",
                                objectFit: "cover",
                              }}
                            />
                          ) : (
                            <div
                              style={{
                                width: "100%",
                                height: "100%",
                                background: "var(--lm-surface)",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                color: "var(--lm-muted)",
                                fontSize: "0.75rem",
                              }}
                            >
                              Sin imagen
                            </div>
                          )}
                          <div
                            style={{
                              position: "absolute",
                              bottom: 0,
                              left: 0,
                              right: 0,
                              padding: "4px 6px",
                              background: "rgba(0,0,0,0.65)",
                              fontSize: "0.65rem",
                              color: "#fff",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                          >
                            {img.entity_name}
                            {" · "}
                            {ENTITY_TYPE_LABELS[
                              img.entity_type as keyof typeof ENTITY_TYPE_LABELS
                            ] ?? img.entity_type}
                          </div>
                        </div>
                      </Col>
                    ))}
                  </Row>
                </section>
              )}

              <h2
                style={{
                  fontFamily: "var(--lm-font-head)",
                  fontSize: "1.1rem",
                  color: "var(--lm-accent)",
                  textTransform: "uppercase",
                  letterSpacing: "0.12em",
                  marginBottom: "1.5rem",
                }}
              >
                Lore compartido ({profile.shared_contents.length})
              </h2>

              {profile.shared_contents.length === 0 ? (
                <p className="text-muted">
                  Este usuario no ha compartido contenido aún.
                </p>
              ) : (
                <Row className="g-4">
                  {profile.shared_contents.map((item) => (
                    <Col key={item.id} md={6} lg={4}>
                      <Card
                        className="h-100 lm-collection-card"
                        style={{ cursor: "pointer" }}
                        onClick={() => setSelectedContent(item)}
                      >
                        <Card.Body>
                          <div className="d-flex align-items-center gap-2 mb-2 flex-wrap">
                            <Badge bg="dark" style={{ fontSize: "0.65rem" }}>
                              {CATEGORY_LABELS[
                                item.category as keyof typeof CATEGORY_LABELS
                              ] ?? item.category}
                            </Badge>
                            <Badge
                              style={{
                                background: "var(--lm-accent-glow)",
                                color: "var(--lm-accent)",
                                border: "1px solid var(--lm-border-accent)",
                                fontSize: "0.6rem",
                              }}
                            >
                              {ENTITY_TYPE_LABELS[
                                item.entity_type as keyof typeof ENTITY_TYPE_LABELS
                              ] ?? item.entity_type}
                            </Badge>
                          </div>
                          <Card.Title
                            style={{
                              fontSize: "0.95rem",
                              marginBottom: "0.75rem",
                            }}
                          >
                            {item.entity_name}
                          </Card.Title>
                          <div
                            style={{
                              maxHeight: 200,
                              overflow: "hidden",
                              maskImage:
                                "linear-gradient(to bottom, black 60%, transparent 100%)",
                              WebkitMaskImage:
                                "linear-gradient(to bottom, black 60%, transparent 100%)",
                              fontSize: "0.85rem",
                            }}
                          >
                            <MarkdownContent>{item.content}</MarkdownContent>
                          </div>
                        </Card.Body>
                        <Card.Footer className="d-flex align-items-center justify-content-between">
                          <small className="text-muted">
                            {item.confirmed_at
                              ? formatDate(item.confirmed_at)
                              : formatDate(item.created_at)}
                          </small>
                          <small
                            className="text-muted"
                            style={{ fontSize: "0.7rem" }}
                          >
                            Leer más →
                          </small>
                        </Card.Footer>
                      </Card>
                    </Col>
                  ))}
                </Row>
              )}
            </>
          ) : null}
        </Container>
        <AppFooter />
      </div>

      {selectedContent && (
        <PublicContentModal
          show={!!selectedContent}
          onHide={() => setSelectedContent(null)}
          content={selectedContent.content}
          category={selectedContent.category}
          entityName={selectedContent.entity_name}
          entityType={selectedContent.entity_type}
          ownerUsername={profile?.username ?? ""}
          ownerDisplayName={profile?.display_name ?? null}
          confirmedAt={selectedContent.confirmed_at}
          createdAt={selectedContent.created_at}
        />
      )}

      {selectedImage && profile && (
        <PublicImageModal
          show={!!selectedImage}
          onHide={() => setSelectedImage(null)}
          imageUrl={selectedImage.image_url}
          storagePath={selectedImage.storage_path}
          seed={selectedImage.seed}
          autoPrompt={selectedImage.auto_prompt}
          finalPrompt={selectedImage.final_prompt}
          entityName={selectedImage.entity_name}
          entityType={selectedImage.entity_type}
          ownerUsername={profile.username}
          ownerDisplayName={profile.display_name}
          createdAt={selectedImage.created_at}
        />
      )}
    </>
  );
}
