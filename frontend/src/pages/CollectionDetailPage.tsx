import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import {
  Accordion,
  Alert,
  Badge,
  Breadcrumb,
  Button,
  Card,
  Form,
  Modal,
  Spinner,
  Tab,
  Table,
  Tabs,
  Pagination,
} from "react-bootstrap";
import {
  getCollection,
  getDocuments,
  getDocument,
  uploadDocument,
  deleteDocument,
  getEntities,
  createEntity,
  deleteEntity,
  generateText,
} from "../api";
import { ApiAbortError } from "../api/apiClient";
import LoadingSpinner from "../components/LoadingSpinner";
import ConfirmModal from "../components/ConfirmModal";
import MarkdownContent from "../components/MarkdownContent";
import TokenCounter from "../components/TokenCounter";
import { useGenerate } from "../hooks/useGenerate";
import { useCollectionDocumentsStatus } from "../hooks/useCollectionDocumentsStatus";
import type {
  Collection,
  Document,
  Entity,
  CreateEntityRequest,
} from "../types";
import type { EntityType } from "../utils/enums";
import { formatDate } from "../utils/formatters";
import { getErrorMessage, parseApiError } from "../utils/errors";
import { ENTITY_TYPE_BADGE, ENTITY_TYPE_LABELS } from "../utils/constants";

// ─── Documents tab ──────────────────────────────────────────────────────────

function DocumentsTab({
  collectionId,
  onDocumentsMutated,
}: {
  collectionId: string;
  onDocumentsMutated: () => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{
    type: "success" | "warning" | "danger";
    text: string;
  } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [filename, setFilename] = useState("");
  const [status, setStatus] = useState<
    "" | "processing" | "completed" | "failed"
  >("");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(0);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(
    null,
  );
  const [loadingDocumentDetail, setLoadingDocumentDetail] = useState(false);
  const [selectedFileName, setSelectedFileName] = useState("");

  const fetchDocuments = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const res = await getDocuments(
          collectionId,
          {
            page,
            page_size: pageSize,
            filename: filename || undefined,
            status: status || undefined,
            order,
          },
          signal,
        );
        setDocuments(res.data);
        setTotalPages(res.meta.total_pages);
      } catch (e) {
        if (e instanceof ApiAbortError) return;
        setError(parseApiError(e, "Error al cargar documentos"));
      } finally {
        setLoading(false);
      }
    },
    [collectionId, filename, order, page, pageSize, status],
  );

  useEffect(() => {
    const controller = new AbortController();
    fetchDocuments(controller.signal);
    return () => controller.abort();
  }, [fetchDocuments]);

  const hasProcessing = documents.some((d) => d.status === "processing");
  useEffect(() => {
    if (!hasProcessing) return;
    const controller = new AbortController();
    const interval = setInterval(() => fetchDocuments(controller.signal), 3000);
    return () => {
      clearInterval(interval);
      controller.abort();
    };
  }, [hasProcessing, fetchDocuments]);

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFileName(file.name);
    setUploading(true);
    setUploadMsg(null);
    try {
      await uploadDocument(collectionId, file);
      setUploadMsg({
        type: "success",
        text: `"${file.name}" subido correctamente.`,
      });
      await fetchDocuments();
      onDocumentsMutated();
    } catch (err) {
      const { variant, text } = parseApiError(err, "Error al subir");
      setUploadMsg({ type: variant, text });
    } finally {
      setUploading(false);
      setSelectedFileName("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteDocument(collectionId, deleteTarget.id);
      setDeleteTarget(null);
      await fetchDocuments();
      onDocumentsMutated();
    } catch (e) {
      setError(parseApiError(e, "Error al eliminar documento"));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  async function handleOpenDocumentDetail(docId: string) {
    setLoadingDocumentDetail(true);
    try {
      const doc = await getDocument(collectionId, docId);
      setSelectedDocument(doc);
    } catch (e) {
      setError(parseApiError(e, "Error al cargar el detalle del documento"));
    } finally {
      setLoadingDocumentDetail(false);
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
    <>
      <Card className="mb-3">
        <Card.Body>
          <div className="d-flex gap-3 flex-wrap align-items-end">
            <Form.Group style={{ minWidth: 220 }}>
              <Form.Label>Buscar archivo</Form.Label>
              <Form.Control
                value={filename}
                onChange={(e) => {
                  setFilename(e.target.value.trim());
                  setPage(1);
                }}
                placeholder="Ej. worldbuilding.pdf"
              />
            </Form.Group>
            <Form.Group style={{ minWidth: 180 }}>
              <Form.Label>Estado</Form.Label>
              <Form.Select
                value={status}
                onChange={(e) => {
                  setStatus(
                    e.target.value as
                      | ""
                      | "processing"
                      | "completed"
                      | "failed",
                  );
                  setPage(1);
                }}
              >
                <option value="">Todos</option>
                <option value="processing">Procesando</option>
                <option value="completed">Completado</option>
                <option value="failed">Error</option>
              </Form.Select>
            </Form.Group>
            <Form.Group style={{ minWidth: 160 }}>
              <Form.Label>Orden</Form.Label>
              <Form.Select
                value={order}
                onChange={(e) => {
                  setOrder(e.target.value as "asc" | "desc");
                  setPage(1);
                }}
              >
                <option value="desc">Más recientes</option>
                <option value="asc">Más antiguos</option>
              </Form.Select>
            </Form.Group>
            <Form.Group style={{ minWidth: 130 }}>
              <Form.Label>Page size</Form.Label>
              <Form.Select
                value={String(pageSize)}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
              >
                {[5, 10, 20, 50].map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </div>
        </Card.Body>
      </Card>

      <div className="mb-3">
        <Form.Label className="fw-semibold">
          Subir documento (PDF o TXT)
        </Form.Label>
        <div className="d-flex align-items-center gap-2 flex-wrap">
          <Form.Control
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt"
            onChange={handleUpload}
            disabled={uploading}
            className="d-none"
          />
          <Button
            type="button"
            variant="outline-secondary"
            className="lm-upload-trigger"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Subiendo..." : "↑ Seleccionar archivo"}
          </Button>
          <small className="text-muted">
            {selectedFileName || "Ningún archivo seleccionado"}
          </small>
          {uploading && (
            <Spinner
              animation="border"
              size="sm"
              className="lm-spinner-inline"
            />
          )}
        </div>
        {uploadMsg && (
          <Alert
            variant={uploadMsg.type}
            className="mt-2 mb-0 py-2"
            onClose={() => setUploadMsg(null)}
            dismissible
          >
            {uploadMsg.text}
          </Alert>
        )}
      </div>

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
      ) : documents.length === 0 ? (
        <div className="lm-empty">
          <span className="lm-empty-glyph">✦</span>
          <p>No hay documentos en esta colección.</p>
          <p>Sube un PDF o TXT para comenzar.</p>
        </div>
      ) : (
        <Table striped hover responsive className="lm-table">
          <thead>
            <tr>
              <th>Archivo</th>
              <th>Tipo</th>
              <th>Chunks</th>
              <th>Estado</th>
              <th>Creado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td>{doc.filename}</td>
                <td>{doc.file_type.toUpperCase()}</td>
                <td>{doc.chunk_count}</td>
                <td>
                  {doc.status === "completed" && (
                    <Badge bg="success">Completado</Badge>
                  )}
                  {doc.status === "failed" && <Badge bg="danger">Error</Badge>}
                  {doc.status === "processing" && (
                    <Badge bg="secondary">Procesando</Badge>
                  )}
                </td>
                <td>{formatDate(doc.created_at)}</td>
                <td>
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    className="me-2"
                    onClick={() => handleOpenDocumentDetail(doc.id)}
                    disabled={loadingDocumentDetail}
                  >
                    Detalle
                  </Button>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => setDeleteTarget(doc)}
                  >
                    Eliminar
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <ConfirmModal
        show={deleteTarget !== null}
        title="Eliminar documento"
        message={`¿Eliminar "${deleteTarget?.filename}"? Se borrarán sus chunks del índice vectorial.`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        variant={deleting ? "secondary" : "danger"}
      />
      <Modal
        show={selectedDocument !== null}
        onHide={() => setSelectedDocument(null)}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>Detalle del documento</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedDocument && (
            <div className="d-grid gap-2">
              <div>
                <small className="text-muted">Nombre</small>
                <div>{selectedDocument.filename}</div>
              </div>
              <div>
                <small className="text-muted">Tipo</small>
                <div>{selectedDocument.file_type.toUpperCase()}</div>
              </div>
              <div>
                <small className="text-muted">Chunks</small>
                <div>{selectedDocument.chunk_count}</div>
              </div>
              <div>
                <small className="text-muted">Estado</small>
                <div>{selectedDocument.status}</div>
              </div>
              <div>
                <small className="text-muted">Creado</small>
                <div>{formatDate(selectedDocument.created_at, true)}</div>
              </div>
            </div>
          )}
        </Modal.Body>
      </Modal>
      {totalPages > 1 && (
        <div className="d-flex justify-content-center mt-3">
          <Pagination>
            <Pagination.First onClick={() => setPage(1)} disabled={page <= 1} />
            <Pagination.Prev
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            />
            {paginationItems.map((item) =>
              typeof item === "number" ? (
                <Pagination.Item
                  key={item}
                  active={item === page}
                  onClick={() => setPage(item)}
                >
                  {item}
                </Pagination.Item>
              ) : (
                <Pagination.Ellipsis key={item} disabled />
              ),
            )}
            <Pagination.Next
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            />
            <Pagination.Last
              onClick={() => setPage(totalPages)}
              disabled={page >= totalPages}
            />
          </Pagination>
        </div>
      )}
    </>
  );
}

// ─── Entities tab ────────────────────────────────────────────────────────────

function EntitiesTab({ collectionId }: { collectionId: string }) {
  const navigate = useNavigate();
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Entity | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [nameFilter, setNameFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState<"" | EntityType>("");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(0);

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateEntityRequest>({
    type: "character",
    name: "",
    description: "",
  });
  const [creating, setCreating] = useState(false);

  const fetchEntities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getEntities(collectionId, {
        page,
        page_size: pageSize,
        name: nameFilter || undefined,
        type: typeFilter || undefined,
        order,
      });
      setEntities(res.data);
      setTotalPages(res.meta.total_pages);
    } catch (e) {
      setError(parseApiError(e, "Error al cargar entidades"));
    } finally {
      setLoading(false);
    }
  }, [collectionId, nameFilter, order, page, pageSize, typeFilter]);

  useEffect(() => {
    fetchEntities();
  }, [fetchEntities]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await createEntity(collectionId, {
        ...form,
        name: form.name.trim(),
        description: form.description.trim(),
      });
      setShowCreate(false);
      setForm({ type: "character", name: "", description: "" });
      await fetchEntities();
    } catch (err) {
      setError(parseApiError(err, "Error al crear entidad"));
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteEntity(collectionId, deleteTarget.id);
      setDeleteTarget(null);
      await fetchEntities();
    } catch (e) {
      setError(parseApiError(e, "Error al eliminar entidad"));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
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
    <>
      <Card className="mb-3">
        <Card.Body>
          <div className="d-flex gap-3 flex-wrap align-items-end">
            <Form.Group style={{ minWidth: 220 }}>
              <Form.Label>Buscar entidad</Form.Label>
              <Form.Control
                value={nameFilter}
                onChange={(e) => {
                  setNameFilter(e.target.value.trim());
                  setPage(1);
                }}
                placeholder="Ej. Aria"
              />
            </Form.Group>
            <Form.Group style={{ minWidth: 180 }}>
              <Form.Label>Tipo</Form.Label>
              <Form.Select
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value as "" | EntityType);
                  setPage(1);
                }}
              >
                <option value="">Todos</option>
                {(Object.keys(ENTITY_TYPE_LABELS) as EntityType[]).map((t) => (
                  <option key={t} value={t}>
                    {ENTITY_TYPE_LABELS[t]}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            <Form.Group style={{ minWidth: 160 }}>
              <Form.Label>Orden</Form.Label>
              <Form.Select
                value={order}
                onChange={(e) => {
                  setOrder(e.target.value as "asc" | "desc");
                  setPage(1);
                }}
              >
                <option value="desc">Más recientes</option>
                <option value="asc">Más antiguos</option>
              </Form.Select>
            </Form.Group>
            <Form.Group style={{ minWidth: 130 }}>
              <Form.Label>Page size</Form.Label>
              <Form.Select
                value={String(pageSize)}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
              >
                {[5, 10, 20, 50].map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </div>
        </Card.Body>
      </Card>

      <div className="d-flex justify-content-end mb-3">
        <Button variant="warning" onClick={() => setShowCreate(true)}>
          + Nueva entidad
        </Button>
      </div>

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
      ) : entities.length === 0 ? (
        <div className="lm-empty">
          <span className="lm-empty-glyph">✦</span>
          <p>No hay entidades en esta colección.</p>
          <p>Crea personajes, escenas, facciones u objetos.</p>
        </div>
      ) : (
        <Table striped hover responsive className="lm-table">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Descripción</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {entities.map((entity) => (
              <tr key={entity.id}>
                <td>
                  <span
                    className="text-primary fw-semibold"
                    style={{ cursor: "pointer" }}
                    onClick={() =>
                      navigate(
                        `/collections/${collectionId}/entities/${entity.id}`,
                      )
                    }
                  >
                    {entity.name}
                  </span>
                </td>
                <td>
                  <Badge bg={ENTITY_TYPE_BADGE[entity.type]}>
                    {ENTITY_TYPE_LABELS[entity.type]}
                  </Badge>
                </td>
                <td
                  style={{
                    maxWidth: 300,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {entity.description || (
                    <span className="text-muted">Sin descripción</span>
                  )}
                </td>
                <td>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => setDeleteTarget(entity)}
                  >
                    Eliminar
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <ConfirmModal
        show={deleteTarget !== null}
        title="Eliminar entidad"
        message={`¿Eliminar la entidad "${deleteTarget?.name}"? También se eliminarán todos sus drafts.`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        variant={deleting ? "secondary" : "danger"}
      />

      <Modal show={showCreate} onHide={() => setShowCreate(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Nueva entidad</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleCreate}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Tipo *</Form.Label>
              <Form.Select
                value={form.type}
                onChange={(e) =>
                  setForm((f) => ({ ...f, type: e.target.value as EntityType }))
                }
              >
                {(Object.keys(ENTITY_TYPE_LABELS) as EntityType[]).map((t) => (
                  <option key={t} value={t}>
                    {ENTITY_TYPE_LABELS[t]}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Nombre *</Form.Label>
              <Form.Control
                type="text"
                value={form.name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, name: e.target.value.trim() }))
                }
                placeholder="Nombre de la entidad"
                required
                autoFocus
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Descripción</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={form.description}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    description: e.target.value.trim(),
                  }))
                }
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
              disabled={creating || !form.name.trim()}
            >
              {creating ? "Creando..." : "Crear"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
      {totalPages > 1 && (
        <div className="d-flex justify-content-center mt-3">
          <Pagination>
            <Pagination.First onClick={() => setPage(1)} disabled={page <= 1} />
            <Pagination.Prev
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            />
            {paginationItems.map((item) =>
              typeof item === "number" ? (
                <Pagination.Item
                  key={item}
                  active={item === page}
                  onClick={() => setPage(item)}
                >
                  {item}
                </Pagination.Item>
              ) : (
                <Pagination.Ellipsis key={item} disabled />
              ),
            )}
            <Pagination.Next
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            />
            <Pagination.Last
              onClick={() => setPage(totalPages)}
              disabled={page >= totalPages}
            />
          </Pagination>
        </div>
      )}
    </>
  );
}

// ─── Generate tab ────────────────────────────────────────────────────────────

function GenerateTab({
  collectionId,
  refreshKey,
}: {
  collectionId: string;
  refreshKey: number;
}) {
  const [query, setQuery] = useState("");
  const [lastQuery, setLastQuery] = useState("");
  const [errorDismissed, setErrorDismissed] = useState(false);
  const { hasCompletedDocs, refresh } =
    useCollectionDocumentsStatus(collectionId);
  const {
    data: result,
    error,
    isLoading,
    isCancelled,
    run,
    cancel,
    reset,
  } = useGenerate(generateText);
  const parsedError = error ? parseApiError(error) : null;

  useEffect(() => {
    if (error) setErrorDismissed(false);
  }, [error]);

  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal);
    return () => controller.abort();
  }, [refreshKey, refresh]);

  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 5) return;
    setLastQuery(trimmedQuery);
    await run(collectionId, { query: trimmedQuery });
  }

  async function handleRegenerate() {
    if (lastQuery.trim().length < 5 || !hasCompletedDocs) return;
    await run(collectionId, { query: lastQuery.trim() });
  }

  return (
    <>
      {hasCompletedDocs === false && (
        <Alert variant="warning">
          Esta colección no tiene documentos procesados. Sube un PDF o TXT y
          espera a que el estado sea <strong>Completado</strong> antes de
          consultar.
        </Alert>
      )}
      {parsedError && !errorDismissed && (
        <Alert
          variant={parsedError.variant}
          dismissible
          onClose={() => setErrorDismissed(true)}
        >
          {parsedError.text}
        </Alert>
      )}
      {isCancelled && (
        <Alert variant="secondary" dismissible onClose={reset}>
          Generación cancelada.
        </Alert>
      )}

      <div className="d-flex gap-4 align-items-start">
        {/* Query panel */}
        <div style={{ flex: "0 0 380px" }}>
          <p className="lm-section-title">Consulta</p>
          <Form onSubmit={handleGenerate}>
            <Form.Group className="mb-3">
              <Form.Control
                as="textarea"
                rows={5}
                value={query}
                onChange={(e) => setQuery(e.target.value.trim())}
                placeholder="Escribe tu consulta al mundo narrativo..."
                minLength={5}
                required
                disabled={isLoading || !hasCompletedDocs}
              />
              <TokenCounter text={query} />
            </Form.Group>
            <div className="d-flex gap-2">
              <Button
                variant="warning"
                type="submit"
                disabled={
                  isLoading || query.trim().length < 5 || !hasCompletedDocs
                }
              >
                {isLoading ? (
                  <>
                    <Spinner
                      animation="border"
                      size="sm"
                      className="me-2 lm-spinner-inline"
                    />
                    Generando...
                  </>
                ) : (
                  "✦ Generar"
                )}
              </Button>
              <Button
                variant="outline-secondary"
                type="button"
                onClick={handleRegenerate}
                disabled={
                  isLoading || lastQuery.trim().length < 5 || !hasCompletedDocs
                }
              >
                ↻ Regenerar
              </Button>
              {isLoading && (
                <Button
                  variant="outline-secondary"
                  type="button"
                  onClick={cancel}
                >
                  Cancelar
                </Button>
              )}
            </div>
          </Form>
        </div>

        {/* Result panel */}
        {isLoading && (
          <div style={{ flex: 1 }}>
            <div className="lm-llm-loading h-100">
              <div className="lm-llm-loading-bar" />
              <small className="text-muted">
                Analizando documentos y redactando respuesta...
              </small>
            </div>
          </div>
        )}
        {result && !isLoading ? (
          <div style={{ flex: 1 }}>
            <Accordion defaultActiveKey="result">
              <Accordion.Item
                eventKey="result"
                className="lm-content-accordion-item"
              >
                <Accordion.Header>
                  <div className="d-flex justify-content-between align-items-center w-100 me-2">
                    <em className="text-muted" style={{ fontSize: "0.88rem" }}>
                      {result.query}
                    </em>
                    <Badge
                      style={{
                        background: "var(--lm-accent-glow)",
                        color: "var(--lm-accent)",
                        border: "1px solid var(--lm-border-accent)",
                        fontSize: "0.65rem",
                      }}
                    >
                      {result.sources_count} fuentes
                    </Badge>
                  </div>
                </Accordion.Header>
                <Accordion.Body>
                  <MarkdownContent>{result.answer}</MarkdownContent>
                </Accordion.Body>
              </Accordion.Item>
            </Accordion>
          </div>
        ) : (
          !isLoading && (
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "4rem 2rem",
                border: "1px dashed var(--lm-border)",
                borderRadius: "var(--lm-radius-lg)",
              }}
            >
              <p
                className="text-muted mb-0"
                style={{ fontStyle: "italic", fontSize: "0.95rem" }}
              >
                El resultado aparecerá aquí…
              </p>
            </div>
          )
        )}
      </div>
    </>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CollectionDetailPage() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const [collection, setCollection] = useState<Collection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [documentsRefreshKey, setDocumentsRefreshKey] = useState(0);

  const fetchCollection = useCallback(async () => {
    if (!collectionId) return;
    setError(null);
    setLoading(true);
    try {
      const col = await getCollection(collectionId);
      setCollection(col);
    } catch (e) {
      setError(getErrorMessage(e, "Error al cargar la colección"));
    } finally {
      setLoading(false);
    }
  }, [collectionId]);

  useEffect(() => {
    fetchCollection();
  }, [fetchCollection]);

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!collection || !collectionId) return null;

  return (
    <div className="lm-page">
      <Breadcrumb>
        <Breadcrumb.Item linkAs={Link} linkProps={{ to: "/" }}>
          Colecciones
        </Breadcrumb.Item>
        <Breadcrumb.Item active>{collection.name}</Breadcrumb.Item>
      </Breadcrumb>

      <h2 className="mb-4">{collection.name}</h2>

      <Tabs defaultActiveKey="documents" className="mb-4">
        <Tab eventKey="documents" title="Documentos">
          <DocumentsTab
            collectionId={collectionId}
            onDocumentsMutated={() =>
              setDocumentsRefreshKey((current) => current + 1)
            }
          />
        </Tab>
        <Tab eventKey="entities" title="Entidades">
          <EntitiesTab collectionId={collectionId} />
        </Tab>
        <Tab eventKey="generate" title="Generar texto">
          <GenerateTab
            collectionId={collectionId}
            refreshKey={documentsRefreshKey}
          />
        </Tab>
      </Tabs>
    </div>
  );
}
