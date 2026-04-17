import { useEffect, useRef, useState } from "react";
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
import type { Collection, Document, Entity, CreateEntityRequest } from "../types";
import { DocumentStatus, EntityType } from "../utils/enums";
import { formatDate } from "../utils/formatters";
import { getErrorMessage } from "../utils/errors";
import { ENTITY_TYPE_BADGE } from "../utils/constants";

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

  async function fetchDocuments() {
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
  }

  useEffect(() => { fetchDocuments(); }, [collectionId]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
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
        <p className="text-muted">No hay documentos en esta colección.</p>
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
                  {doc.status === DocumentStatus.Completed && <Badge bg="success">Completado</Badge>}
                  {doc.status === DocumentStatus.Failed && <Badge bg="danger">Error</Badge>}
                  {doc.status === DocumentStatus.Processing && (
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
    type: EntityType.Character,
    name: "",
    description: "",
  });
  const [creating, setCreating] = useState(false);

  async function fetchEntities() {
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
  }

  useEffect(() => { fetchEntities(); }, [collectionId]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await createEntity(collectionId, form);
      setShowCreate(false);
      setForm({ type: EntityType.Character, name: "", description: "" });
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
        <p className="text-muted">No hay entidades en esta colección.</p>
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
                  <Badge bg={ENTITY_TYPE_BADGE[entity.type]}>{entity.type}</Badge>
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
                <option value={EntityType.Character}>Personaje</option>
                <option value={EntityType.Scene}>Escena</option>
                <option value={EntityType.Faction}>Facción</option>
                <option value={EntityType.Item}>Objeto</option>
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ answer: string; query: string; sources_count: number } | null>(null);

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await generateText(collectionId, { query });
      setResult(res);
    } catch (err) {
      setError(getErrorMessage(err, "Error al generar texto"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          {error}
        </Alert>
      )}

      <Form onSubmit={handleGenerate} className="mb-4">
        <Form.Group className="mb-3">
          <Form.Label className="fw-semibold">Consulta</Form.Label>
          <Form.Control
            as="textarea"
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Escribe tu consulta al mundo narrativo..."
            minLength={5}
            required
          />
        </Form.Group>
        <Button
          variant="warning"
          type="submit"
          disabled={loading || query.trim().length < 5}
        >
          {loading ? (
            <>
              <Spinner animation="border" size="sm" className="me-2" />
              Generando...
            </>
          ) : (
            "Generar"
          )}
        </Button>
      </Form>

      {result && (
        <Card>
          <Card.Header className="d-flex justify-content-between align-items-center">
            <span className="fw-semibold">Resultado</span>
            <Badge bg="secondary">{result.sources_count} fuentes</Badge>
          </Card.Header>
          <Card.Body>
            <p className="text-muted mb-2">
              <small>Consulta: {result.query}</small>
            </p>
            <p className="mb-0" style={{ whiteSpace: "pre-wrap" }}>
              {result.answer}
            </p>
          </Card.Body>
        </Card>
      )}
    </>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CollectionDetailPage() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const [collection, setCollection] = useState<Collection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!collectionId) return;
    setLoading(true);
    getCollection(collectionId)
      .then(setCollection)
      .catch((e) => setError(getErrorMessage(e, "Error al cargar la colección")))
      .finally(() => setLoading(false));
  }, [collectionId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!collection || !collectionId) return null;

  return (
    <>
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
    </>
  );
}
