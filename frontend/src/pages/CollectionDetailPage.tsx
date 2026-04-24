import { useCallback, useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import {
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
} from "react-bootstrap";
import { getCollection, getDocuments, uploadDocument, deleteDocument, getEntities, createEntity, deleteEntity, generateText } from "../api";
import LoadingSpinner from "../components/LoadingSpinner";
import ConfirmModal from "../components/ConfirmModal";
import MarkdownContent from "../components/MarkdownContent";
import TokenCounter from "../components/TokenCounter";
import { useGenerate } from "../hooks/useGenerate";
import type { Collection, Document, Entity, CreateEntityRequest } from "../types";
import type { EntityType } from "../utils/enums";
import { formatDate } from "../utils/formatters";
import { getErrorMessage, parseApiError } from "../utils/errors";
import { ENTITY_TYPE_BADGE, ENTITY_TYPE_LABELS } from "../utils/constants";

// ─── Documents tab ──────────────────────────────────────────────────────────

function DocumentsTab({ collectionId }: { collectionId: string }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ type: "success" | "danger"; text: string } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDocuments(collectionId);
      setDocuments(res.data);
    } catch (e) {
      setError(getErrorMessage(e, "Error al cargar documentos"));
    } finally {
      setLoading(false);
    }
  }, [collectionId]);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  const hasProcessing = documents.some((d) => d.status === "processing");
  useEffect(() => {
    if (!hasProcessing) return;
    const interval = setInterval(fetchDocuments, 3000);
    return () => clearInterval(interval);
  }, [hasProcessing, fetchDocuments]);

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg(null);
    try {
      await uploadDocument(collectionId, file);
      setUploadMsg({ type: "success", text: `"${file.name}" subido correctamente.` });
      await fetchDocuments();
    } catch (err) {
      setUploadMsg({ type: "danger", text: getErrorMessage(err, "Error al subir") });
    } finally {
      setUploading(false);
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
    } catch (e) {
      setError(getErrorMessage(e, "Error al eliminar documento"));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="mb-3">
        <Form.Label className="fw-semibold">Subir documento (PDF o TXT)</Form.Label>
        <div className="d-flex align-items-center gap-2">
          <Form.Control
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt"
            onChange={handleUpload}
            disabled={uploading}
            style={{ maxWidth: 360 }}
          />
          {uploading && <Spinner animation="border" size="sm" />}
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
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          {error}
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
        <Table striped hover responsive>
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
                  {doc.status === "completed" && <Badge bg="success">Completado</Badge>}
                  {doc.status === "failed" && <Badge bg="danger">Error</Badge>}
                  {doc.status === "processing" && (
                    <Badge bg="secondary">Procesando</Badge>
                  )}
                </td>
                <td>{formatDate(doc.created_at)}</td>
                <td>
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
    </>
  );
}

// ─── Entities tab ────────────────────────────────────────────────────────────

function EntitiesTab({ collectionId }: { collectionId: string }) {
  const navigate = useNavigate();
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Entity | null>(null);
  const [deleting, setDeleting] = useState(false);

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
      const res = await getEntities(collectionId);
      setEntities(res.data);
    } catch (e) {
      setError(getErrorMessage(e, "Error al cargar entidades"));
    } finally {
      setLoading(false);
    }
  }, [collectionId]);

  useEffect(() => { fetchEntities(); }, [fetchEntities]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await createEntity(collectionId, form);
      setShowCreate(false);
      setForm({ type: "character", name: "", description: "" });
      await fetchEntities();
    } catch (err) {
      setError(getErrorMessage(err, "Error al crear entidad"));
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
      setError(getErrorMessage(e, "Error al eliminar entidad"));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="d-flex justify-content-end mb-3">
        <Button variant="warning" onClick={() => setShowCreate(true)}>
          + Nueva entidad
        </Button>
      </div>

      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          {error}
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
        <Table striped hover responsive>
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
                      navigate(`/collections/${collectionId}/entities/${entity.id}`)
                    }
                  >
                    {entity.name}
                  </span>
                </td>
                <td>
                  <Badge bg={ENTITY_TYPE_BADGE[entity.type]}>{ENTITY_TYPE_LABELS[entity.type]}</Badge>
                </td>
                <td
                  style={{
                    maxWidth: 300,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {entity.description || <span className="text-muted">Sin descripción</span>}
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
                onChange={(e) => setForm((f) => ({ ...f, type: e.target.value as EntityType }))}
              >
                {(Object.keys(ENTITY_TYPE_LABELS) as EntityType[]).map((t) => (
                  <option key={t} value={t}>{ENTITY_TYPE_LABELS[t]}</option>
                ))}
              </Form.Select>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Nombre *</Form.Label>
              <Form.Control
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
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
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Descripción opcional"
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowCreate(false)} disabled={creating}>
              Cancelar
            </Button>
            <Button variant="warning" type="submit" disabled={creating || !form.name.trim()}>
              {creating ? "Creando..." : "Crear"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </>
  );
}

// ─── Generate tab ────────────────────────────────────────────────────────────

function GenerateTab({ collectionId }: { collectionId: string }) {
  const [query, setQuery] = useState("");
  const [errorDismissed, setErrorDismissed] = useState(false);
  const [hasCompletedDocs, setHasCompletedDocs] = useState<boolean | null>(null);
  const { data: result, error, isLoading, isCancelled, run, cancel, reset } = useGenerate(generateText);
  const parsedError = error ? parseApiError(error) : null;

  useEffect(() => { if (error) setErrorDismissed(false); }, [error]);

  useEffect(() => {
    getDocuments(collectionId)
      .then((res) => setHasCompletedDocs(res.data.some((d) => d.status === "completed")))
      .catch(() => setHasCompletedDocs(false));
  }, [collectionId]);

  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    await run(collectionId, { query });
  }

  return (
    <>
      {hasCompletedDocs === false && (
        <Alert variant="warning">
          Esta colección no tiene documentos procesados. Sube un PDF o TXT y espera a que el estado sea <strong>Completado</strong> antes de consultar.
        </Alert>
      )}
      {parsedError && !errorDismissed && (
        <Alert variant={parsedError.variant} dismissible onClose={() => setErrorDismissed(true)}>
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
                onChange={(e) => setQuery(e.target.value)}
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
                disabled={isLoading || query.trim().length < 5 || !hasCompletedDocs}
              >
                {isLoading ? (
                  <>
                    <Spinner animation="border" size="sm" className="me-2" />
                    Generando...
                  </>
                ) : (
                  "✦ Generar"
                )}
              </Button>
              {isLoading && (
                <Button variant="outline-secondary" type="button" onClick={cancel}>
                  Cancelar
                </Button>
              )}
            </div>
          </Form>
        </div>

        {/* Result panel */}
        {result ? (
          <div style={{ flex: 1 }}>
            <Card>
              <Card.Header className="d-flex justify-content-between align-items-center">
                <em className="text-muted" style={{ fontSize: "0.88rem" }}>{result.query}</em>
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
              </Card.Header>
              <Card.Body>
                <MarkdownContent>{result.answer}</MarkdownContent>
              </Card.Body>
            </Card>
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
              <p className="text-muted mb-0" style={{ fontStyle: "italic", fontSize: "0.95rem" }}>
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
          <DocumentsTab collectionId={collectionId} />
        </Tab>
        <Tab eventKey="entities" title="Entidades">
          <EntitiesTab collectionId={collectionId} />
        </Tab>
        <Tab eventKey="generate" title="Generar texto">
          <GenerateTab collectionId={collectionId} />
        </Tab>
      </Tabs>
    </div>
  );
}
