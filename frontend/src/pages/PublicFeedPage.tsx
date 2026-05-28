import { useEffect, useReducer, useState } from "react";
import { Link } from "react-router-dom";
import {
  Container,
  Row,
  Col,
  Card,
  Alert,
  Spinner,
  Pagination,
  Badge,
} from "react-bootstrap";
import { getPublicFeed, getPublicImages } from "../api/users";
import { formatDate } from "../utils/formatters";
import { parseApiError } from "../utils/errors";
import { CATEGORY_LABELS, ENTITY_TYPE_LABELS } from "../utils/constants";
import PublicContentModal from "../components/PublicContentModal";
import PublicImageModal from "../components/PublicImageModal";
import SafeImage from "../components/SafeImage";
import { resolveImageUrl } from "../utils/media";
import type { PublicFeedItem, PublicImageItem } from "../types/user";
import type { PaginatedResponse } from "../types";

const PAGE_SIZE = 12;

/**
 * Página de feed público con contenido e imágenes compartidas.
 *
 * Muestra un muro de lore público generado por la comunidad,
 * incluyendo tarjetas de contenido narrativo e imágenes compartidas.
 * Permite navegar por páginas y abrir modales con el detalle completo.
 */
export default function PublicFeedPage() {
  const [items, setItems] = useState<PublicFeedItem[]>([]);
  const [images, setImages] = useState<PublicImageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [refreshKey, incrementRefresh] = useReducer((n: number) => n + 1, 0);
  const [selectedItem, setSelectedItem] = useState<PublicFeedItem | null>(null);
  const [selectedImage, setSelectedImage] = useState<PublicImageItem | null>(
    null,
  );

  /**
   * Carga el feed público y las imágenes compartidas en paralelo.
   * Se re-ejecuta al cambiar de página o cuando el usuario vuelve a la pestaña.
   */
  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    Promise.all([
      getPublicFeed({ page, page_size: PAGE_SIZE }, ctrl.signal),
      getPublicImages({ page_size: 8 }, ctrl.signal),
    ])
      .then(
        ([feedRes, imgRes]: [
          PaginatedResponse<PublicFeedItem>,
          PaginatedResponse<PublicImageItem>,
        ]) => {
          setItems(feedRes.data);
          setTotalPages(feedRes.meta.total_pages);
          setImages(imgRes.data);
        },
      )
      .catch((e) => {
        if (e?.name !== "ApiAbortError") setError(parseApiError(e).text);
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [page, refreshKey]);

  useEffect(() => {
    function handleVisibility() {
      if (document.visibilityState === "visible") {
        incrementRefresh();
      }
    }
    document.addEventListener("visibilitychange", handleVisibility);
    return () =>
      document.removeEventListener("visibilitychange", handleVisibility);
  }, [incrementRefresh]);

  return (
    <Container fluid="lg" className="py-5">
      <div className="mb-5">
        <h1
          style={{
            fontFamily: "var(--lm-font-head)",
            fontSize: "clamp(1.8rem, 4vw, 3rem)",
            letterSpacing: "0.02em",
          }}
        >
          Lore <span style={{ color: "var(--lm-accent)" }}>público</span>
        </h1>
        <p className="text-muted mb-0">
          Contenido narrativo compartido por la comunidad de escritores y
          creadores.
        </p>
      </div>

      {error && <Alert variant="warning">{error}</Alert>}

      {loading ? (
        <div className="d-flex justify-content-center py-5">
          <Spinner animation="border" style={{ color: "var(--lm-accent)" }} />
        </div>
      ) : (
        <>
          {images.length > 0 && (
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
                Imágenes compartidas
              </h2>
              <Row className="g-3">
                {images.map((img) => (
                  <Col key={img.image_id} xs={6} sm={4} md={3} lg={2}>
                    <button
                      type="button"
                      aria-label={`Ver imagen de ${img.entity_name}`}
                      className="lm-shared-image-card p-0 border-0 bg-transparent"
                      style={{
                        display: "block",
                        width: "100%",
                        position: "relative",
                        borderRadius: 8,
                        overflow: "hidden",
                        border: "1px solid var(--lm-border)",
                        aspectRatio: "1",
                        cursor: "pointer",
                      }}
                      onClick={() => setSelectedImage(img)}
                    >
                      {img.storage_path || img.image_url ? (
                        <SafeImage
                          src={resolveImageUrl(img.image_url, img.storage_path)}
                          alt={img.entity_name}
                          style={{
                            width: "100%",
                            height: "100%",
                            objectFit: "cover",
                          }}
                        />
                      ) : (
                        <div className="lm-img-placeholder">Sin imagen</div>
                      )}
                      <div className="lm-img-caption">
                        <Link
                          to={`/users/${img.owner_username}`}
                          style={{
                            color: "var(--lm-accent)",
                            textDecoration: "none",
                          }}
                        >
                          @{img.owner_username}
                        </Link>
                        {" · "}
                        {img.entity_name}
                      </div>
                    </button>
                  </Col>
                ))}
              </Row>
            </section>
          )}

          {items.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <div style={{ fontSize: "2.5rem", opacity: 0.3 }}>✦</div>
              <p className="mt-3">No hay contenido compartido todavía.</p>
            </div>
          ) : (
            <>
              <Row className="g-4">
                {items.map((item) => (
                  <Col key={item.content_id} sm={6} lg={4}>
                    <Card
                      className="h-100 lm-collection-card"
                      style={{ cursor: "pointer" }}
                      onClick={() => setSelectedItem(item)}
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
                          className="mb-1"
                          style={{ fontSize: "0.95rem" }}
                        >
                          {item.entity_name}
                        </Card.Title>
                        <Card.Text
                          className="text-muted"
                          style={{
                            fontSize: "0.82rem",
                            overflow: "hidden",
                            display: "-webkit-box",
                            WebkitLineClamp: 4,
                            WebkitBoxOrient: "vertical",
                            lineHeight: 1.55,
                          }}
                        >
                          {item.content_preview}
                        </Card.Text>
                      </Card.Body>
                      <Card.Footer className="d-flex align-items-center justify-content-between">
                        <div>
                          <Link
                            to={`/users/${item.owner_username}`}
                            onClick={(e) => e.stopPropagation()}
                            style={{
                              color: "var(--lm-accent)",
                              fontSize: "0.8rem",
                              textDecoration: "none",
                            }}
                          >
                            @{item.owner_username}
                          </Link>
                          <small
                            className="text-muted d-block"
                            style={{ fontSize: "0.72rem" }}
                          >
                            {item.confirmed_at
                              ? formatDate(item.confirmed_at)
                              : formatDate(item.created_at)}
                          </small>
                        </div>
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

              {totalPages > 1 && (
                <div className="d-flex justify-content-center mt-5">
                  <Pagination>
                    <Pagination.Prev
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    />
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(
                      (p) => (
                        <Pagination.Item
                          key={p}
                          active={p === page}
                          onClick={() => setPage(p)}
                        >
                          {p}
                        </Pagination.Item>
                      ),
                    )}
                    <Pagination.Next
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    />
                  </Pagination>
                </div>
              )}
            </>
          )}
        </>
      )}

      {selectedItem && (
        <PublicContentModal
          show={!!selectedItem}
          onHide={() => setSelectedItem(null)}
          content={selectedItem.content}
          category={selectedItem.category}
          entityName={selectedItem.entity_name}
          entityType={selectedItem.entity_type}
          ownerUsername={selectedItem.owner_username}
          ownerDisplayName={selectedItem.owner_display_name}
          confirmedAt={selectedItem.confirmed_at}
          createdAt={selectedItem.created_at}
        />
      )}

      {selectedImage && (
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
          ownerUsername={selectedImage.owner_username}
          ownerDisplayName={selectedImage.owner_display_name}
          createdAt={selectedImage.created_at}
        />
      )}
    </Container>
  );
}
