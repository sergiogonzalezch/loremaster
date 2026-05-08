import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Container,
  Row,
  Col,
  Card,
  Alert,
  Spinner,
  Pagination,
} from "react-bootstrap";
import { getPublicCollections } from "../api/collections";
import StarfieldCanvas from "../components/StarfieldCanvas";
import { useAuth } from "../hooks/useAuth";
import { formatDate } from "../utils/formatters";
import { parseApiError } from "../utils/errors";
import type { Collection } from "../types";

const PAGE_SIZE = 12;

export default function PublicFeedPage() {
  const { user } = useAuth();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    getPublicCollections({ page, page_size: PAGE_SIZE }, ctrl.signal)
      .then((res) => {
        setCollections(res.data);
        setTotalPages(res.meta.total_pages);
      })
      .catch((e) => {
        if (e?.name !== "ApiAbortError") setError(parseApiError(e).text);
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [page]);

  function collectionHref(col: Collection) {
    return user ? `/collections/${col.id}` : `/login`;
  }

  function collectionState(col: Collection) {
    return user ? undefined : { from: `/collections/${col.id}` };
  }

  return (
    <>
      <StarfieldCanvas />
      <div style={{ position: "relative", zIndex: 1, minHeight: "100vh" }}>
        <nav
          style={{
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            backdropFilter: "blur(8px)",
            backgroundColor: "rgba(10,10,18,0.7)",
          }}
          className="py-3"
        >
          <Container
            fluid="lg"
            className="d-flex align-items-center justify-content-between"
          >
            <Link to={user ? "/" : "/feed"} style={{ textDecoration: "none" }}>
              <span className="lm-brand-glyph" style={{ fontSize: "1.1rem" }}>
                ✦
              </span>{" "}
              <span
                style={{
                  fontFamily: "var(--lm-font-head)",
                  fontSize: "1.1rem",
                }}
              >
                <span style={{ color: "var(--lm-accent)" }}>Lore</span>Master
              </span>
            </Link>
            {user ? (
              <Link
                to="/"
                className="btn btn-sm btn-warning"
                style={{ fontFamily: "var(--lm-font-head)" }}
              >
                Mis colecciones
              </Link>
            ) : (
              <Link
                to="/login"
                className="btn btn-sm btn-warning"
                style={{ fontFamily: "var(--lm-font-head)" }}
              >
                Iniciar sesión
              </Link>
            )}
          </Container>
        </nav>

        <Container fluid="lg" className="py-5">
          <div className="mb-5">
            <h1
              style={{
                fontFamily: "var(--lm-font-head)",
                fontSize: "clamp(1.8rem, 4vw, 3rem)",
                letterSpacing: "0.02em",
              }}
            >
              Mundos <span style={{ color: "var(--lm-accent)" }}>públicos</span>
            </h1>
            <p className="text-muted mb-0">
              Colecciones compartidas por la comunidad de escritores y
              creadores.
            </p>
          </div>

          {error && <Alert variant="warning">{error}</Alert>}

          {loading ? (
            <div className="d-flex justify-content-center py-5">
              <Spinner
                animation="border"
                style={{ color: "var(--lm-accent)" }}
              />
            </div>
          ) : collections.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <div style={{ fontSize: "2.5rem", opacity: 0.3 }}>✦</div>
              <p className="mt-3">No hay colecciones públicas todavía.</p>
            </div>
          ) : (
            <>
              <Row className="g-4">
                {collections.map((col) => (
                  <Col key={col.id} sm={6} lg={4}>
                    <Card className="h-100 lm-collection-card">
                      <Card.Body>
                        <div className="d-flex align-items-start justify-content-between gap-2 mb-2">
                          <Card.Title
                            className="mb-0"
                            style={{ fontSize: "1rem" }}
                          >
                            {col.name}
                          </Card.Title>
                          <span
                            className="badge flex-shrink-0"
                            style={{
                              backgroundColor: "var(--lm-accent)",
                              color: "#000",
                              fontSize: "0.65rem",
                            }}
                          >
                            Pública
                          </span>
                        </div>
                        <Card.Text
                          className="text-muted"
                          style={{
                            fontSize: "0.85rem",
                            overflow: "hidden",
                            display: "-webkit-box",
                            WebkitLineClamp: 3,
                            WebkitBoxOrient: "vertical",
                          }}
                        >
                          {col.description || "Sin descripción"}
                        </Card.Text>
                        <div className="d-flex gap-3 mt-2">
                          <small className="text-muted">
                            <strong>{col.document_count}</strong>{" "}
                            {col.document_count === 1 ? "doc." : "docs."}
                          </small>
                          <small className="text-muted">
                            <strong>{col.entity_count}</strong>{" "}
                            {col.entity_count === 1 ? "entidad" : "entidades"}
                          </small>
                        </div>
                      </Card.Body>
                      <Card.Footer className="d-flex align-items-center justify-content-between">
                        <small className="text-muted">
                          {formatDate(col.created_at)}
                        </small>
                        <Link
                          to={collectionHref(col)}
                          state={collectionState(col)}
                          className="btn btn-sm"
                          style={{
                            borderColor: "var(--lm-accent)",
                            color: "var(--lm-accent)",
                          }}
                        >
                          Explorar →
                        </Link>
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
        </Container>
      </div>
    </>
  );
}
