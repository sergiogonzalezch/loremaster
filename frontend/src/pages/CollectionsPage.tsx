import { useEffect, useState, useCallback, useMemo } from "react";
import type { FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Row,
  Col,
  Card,
  Button,
  Alert,
  Modal,
  Form,
  Pagination,
} from "react-bootstrap";
import { getCollections, createCollection, deleteCollection } from "../api";
import LoadingSpinner from "../components/LoadingSpinner";
import ConfirmModal from "../components/ConfirmModal";
import type { Collection } from "../types";
import { formatDate } from "../utils/formatters";
import { parseApiError } from "../utils/errors";
import { useDebouncedValue } from "../hooks/useDebouncedValue";

export default function CollectionsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalPages, setTotalPages] = useState(0);
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<Collection | null>(null);
  const [deleting, setDeleting] = useState(false);

  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const [name, setName] = useState(searchParams.get("name") ?? "");
  const [createdAfter, setCreatedAfter] = useState(
    searchParams.get("created_after")?.slice(0, 10) ?? "",
  );
  const [createdBefore, setCreatedBefore] = useState(
    searchParams.get("created_before")?.slice(0, 10) ?? "",
  );

  const page = Number(searchParams.get("page") ?? 1);
  const pageSize = Number(searchParams.get("page_size") ?? 12);

  const debouncedName = useDebouncedValue(name);

  const fetchCollections = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getCollections({
        page,
        page_size: pageSize,
        name: debouncedName || undefined,
        created_after: createdAfter || undefined,
        created_before: createdBefore || undefined,
      });
      setCollections(res.data);
      setTotalPages(res.meta.total_pages);
    } catch (e) {
      setError(parseApiError(e, "Error al cargar las colecciones"));
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedName, createdAfter, createdBefore]);

  const setParam = useCallback(
    (updates: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([key, value]) => {
        if (!value) {
          next.delete(key);
          return;
        }
        next.set(key, value);
      });
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  useEffect(() => {
    window.dispatchEvent(
      new CustomEvent("lm:collections", {
        detail: {
          collections,
          nav: (id: string) => navigate(`/collections/${id}`),
        },
      }),
    );
  }, [collections, navigate]);

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteCollection(deleteTarget.id);
      setDeleteTarget(null);
      await fetchCollections();
    } catch (e) {
      setError(parseApiError(e, "Error al eliminar la colección"));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await createCollection({
        name: createName,
        description: createDescription,
      });
      setShowCreate(false);
      setCreateName("");
      setCreateDescription("");
      await fetchCollections();
    } catch (e) {
      setError(parseApiError(e, "Error al crear la colección"));
    } finally {
      setCreating(false);
    }
  }

  const paginationItems = useMemo(() => {
    const items: Array<number | "ellipsis-left" | "ellipsis-right"> = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i += 1) items.push(i);
      return items;
    }
    items.push(1);
    if (page > 3) items.push("ellipsis-left");
    for (
      let i = Math.max(2, page - 1);
      i <= Math.min(totalPages - 1, page + 1);
      i += 1
    ) {
      items.push(i);
    }
    if (page < totalPages - 2) items.push("ellipsis-right");
    items.push(totalPages);
    return items;
  }, [page, totalPages]);

  return (
    <div className="lm-page">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Colecciones</h2>
        <Button variant="warning" onClick={() => setShowCreate(true)}>
          + Nueva colección
        </Button>
      </div>

      <Card className="mb-3">
        <Card.Body>
          <Row className="g-3">
            <Col md={4}>
              <Form.Label>Buscar por nombre</Form.Label>
              <Form.Control
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setParam({ page: "1", name: e.target.value || null });
                }}
                placeholder="Ej. Reinos del Norte"
              />
            </Col>
            <Col md={3}>
              <Form.Label>Creada desde</Form.Label>
              <Form.Control
                type="date"
                value={createdAfter}
                onChange={(e) => {
                  setCreatedAfter(e.target.value);
                  setParam({
                    page: "1",
                    created_after: e.target.value || null,
                  });
                }}
              />
            </Col>
            <Col md={3}>
              <Form.Label>Creada hasta</Form.Label>
              <Form.Control
                type="date"
                value={createdBefore}
                onChange={(e) => {
                  setCreatedBefore(e.target.value);
                  setParam({
                    page: "1",
                    created_before: e.target.value || null,
                  });
                }}
              />
            </Col>
            <Col md={2}>
              <Form.Label>Page size</Form.Label>
              <Form.Select
                value={String(pageSize)}
                onChange={(e) =>
                  setParam({ page: "1", page_size: e.target.value })
                }
              >
                {[6, 12, 24, 50].map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </Form.Select>
            </Col>
          </Row>
          <div className="mt-3 d-flex justify-content-end">
            <Button
              size="sm"
              variant="outline-secondary"
              onClick={() => {
                setName("");
                setCreatedAfter("");
                setCreatedBefore("");
                setParam({
                  page: "1",
                  page_size: String(pageSize),
                  name: null,
                  created_after: null,
                  created_before: null,
                });
              }}
            >
              Reset filtros
            </Button>
          </div>
        </Card.Body>
      </Card>

      {error && (
        <Alert
          variant={error.variant}
          onClose={() => setError(null)}
          dismissible
        >
          {error.text}
        </Alert>
      )}

      {loading ? (
        <LoadingSpinner />
      ) : collections.length === 0 ? (
        <div className="lm-empty">
          <span className="lm-empty-glyph">✦</span>
          <p>No hay colecciones todavía.</p>
          <p>Crea tu primera colección para empezar a construir tu mundo.</p>
        </div>
      ) : (
        <>
          <Row className="g-4 lm-stagger">
            {collections.map((col) => (
              <Col key={col.id} md={4}>
                <Card
                  className="h-100 lm-collection-card"
                  onClick={() => navigate(`/collections/${col.id}`)}
                >
                  <Card.Body>
                    <Card.Title>{col.name}</Card.Title>
                    <Card.Text
                      className="text-muted"
                      style={{
                        overflow: "hidden",
                        display: "-webkit-box",
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: "vertical",
                      }}
                    >
                      {col.description || "Sin descripción"}
                    </Card.Text>
                  </Card.Body>
                  <Card.Footer className="d-flex justify-content-between align-items-center">
                    <small className="text-muted">
                      {formatDate(col.created_at)}
                    </small>
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(col);
                      }}
                    >
                      Eliminar
                    </Button>
                  </Card.Footer>
                </Card>
              </Col>
            ))}
          </Row>
          {totalPages > 1 && (
            <div className="d-flex justify-content-center mt-4">
              <Pagination>
                <Pagination.Prev
                  disabled={page <= 1}
                  onClick={() => setParam({ page: String(page - 1) })}
                />
                {paginationItems.map((item) =>
                  typeof item === "number" ? (
                    <Pagination.Item
                      active={item === page}
                      key={item}
                      onClick={() => setParam({ page: String(item) })}
                    >
                      {item}
                    </Pagination.Item>
                  ) : (
                    <Pagination.Ellipsis key={item} disabled />
                  ),
                )}
                <Pagination.Next
                  disabled={page >= totalPages}
                  onClick={() => setParam({ page: String(page + 1) })}
                />
              </Pagination>
            </div>
          )}
        </>
      )}

      <ConfirmModal
        show={deleteTarget !== null}
        title="Eliminar colección"
        message={`¿Estás seguro de que quieres eliminar "${deleteTarget?.name}"? Esta acción eliminará todos sus documentos y entidades.`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        variant={deleting ? "secondary" : "danger"}
      />

      <Modal show={showCreate} onHide={() => setShowCreate(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Nueva colección</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleCreate}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Nombre *</Form.Label>
              <Form.Control
                type="text"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                placeholder="Nombre de la colección"
                required
                autoFocus
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Descripción</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={createDescription}
                onChange={(e) => setCreateDescription(e.target.value)}
                placeholder="Descripción opcional"
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button
              variant="secondary"
              onClick={() => setShowCreate(false)}
              disabled={creating}
            >
              Cancelar
            </Button>
            <Button
              variant="warning"
              type="submit"
              disabled={creating || !createName.trim()}
            >
              {creating ? "Creando..." : "Crear"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </div>
  );
}
