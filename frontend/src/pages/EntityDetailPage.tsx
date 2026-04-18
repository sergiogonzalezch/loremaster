import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Alert,
  Badge,
  Breadcrumb,
  Button,
  Card,
  Form,
  Modal,
  Spinner,
} from "react-bootstrap";
import { getEntity, updateEntity, getCollection, generateDraft, getDrafts, updateDraftContent, confirmDraft, discardDraft, deleteDraft } from "../api";
import LoadingSpinner from "../components/LoadingSpinner";
import ConfirmModal from "../components/ConfirmModal";
import type { Collection, Draft, Entity, UpdateEntityRequest } from "../types";
import type { EntityType } from "../utils/enums";
import { formatDate } from "../utils/formatters";
import { getErrorMessage } from "../utils/errors";
import { ENTITY_TYPE_BADGE } from "../utils/constants";

// ─── Draft card ───────────────────────────────────────────────────────────────

interface DraftCardProps {
  draft: Draft;
  collectionId: string;
  entityId: string;
  onAction: () => void;
}

function DraftCard({ draft, collectionId, entityId, onAction }: DraftCardProps) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [showEdit, setShowEdit] = useState(false);
  const [editContent, setEditContent] = useState(draft.content);
  const [saving, setSaving] = useState(false);

  const [showDiscard, setShowDiscard] = useState(false);
  const [showDelete, setShowDelete] = useState(false);

  async function handleConfirm() {
    setBusy(true);
    setError(null);
    try {
      await confirmDraft(collectionId, entityId, draft.id);
      onAction();
    } catch (e) {
      setError(getErrorMessage(e, "Error al confirmar"));
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveEdit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await updateDraftContent(collectionId, entityId, draft.id, { content: editContent });
      setShowEdit(false);
      onAction();
    } catch (e) {
      setError(getErrorMessage(e, "Error al guardar"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDiscard() {
    setBusy(true);
    setError(null);
    try {
      await discardDraft(collectionId, entityId, draft.id);
      setShowDiscard(false);
      onAction();
    } catch (e) {
      setError(getErrorMessage(e, "Error al descartar"));
      setShowDiscard(false);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    setError(null);
    try {
      await deleteDraft(collectionId, entityId, draft.id);
      setShowDelete(false);
      onAction();
    } catch (e) {
      setError(getErrorMessage(e, "Error al eliminar"));
      setShowDelete(false);
    } finally {
      setBusy(false);
    }
  }

  const isPending = draft.status === "pending";
  const isConfirmed = draft.status === "confirmed";

  return (
    <>
      <Card className="mb-3">
        <Card.Header className="d-flex justify-content-between align-items-center">
          <em className="text-muted small">{draft.query}</em>
          {draft.status === "pending" && <Badge bg="warning" text="dark">Borrador</Badge>}
          {draft.status === "confirmed" && <Badge bg="success">Confirmado</Badge>}
          {draft.status === "discarded" && <Badge bg="secondary">Descartado</Badge>}
        </Card.Header>
        <Card.Body>
          {error && (
            <Alert variant="danger" onClose={() => setError(null)} dismissible className="py-2">
              {error}
            </Alert>
          )}
          <p className="mb-0" style={{ whiteSpace: "pre-wrap" }}>
            {draft.content}
          </p>
        </Card.Body>
        <Card.Footer>
          {isPending ? (
            <div className="d-flex gap-2">
              <Button variant="success" size="sm" onClick={handleConfirm} disabled={busy}>
                {busy ? <Spinner animation="border" size="sm" /> : "Confirmar"}
              </Button>
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => { setEditContent(draft.content); setShowEdit(true); }}
                disabled={busy}
              >
                Editar
              </Button>
              <Button
                variant="outline-warning"
                size="sm"
                onClick={() => setShowDiscard(true)}
                disabled={busy}
              >
                Descartar
              </Button>
              <Button
                variant="outline-danger"
                size="sm"
                onClick={() => setShowDelete(true)}
                disabled={busy}
              >
                Eliminar
              </Button>
            </div>
          ) : isConfirmed ? (
            <div className="d-flex align-items-center justify-content-between">
              {draft.confirmed_at && (
                <small className="text-muted">Confirmado el {formatDate(draft.confirmed_at, true)}</small>
              )}
              <div className="d-flex gap-2">
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={() => { setEditContent(draft.content); setShowEdit(true); }}
                  disabled={busy}
                >
                  Editar
                </Button>
                <Button
                  variant="outline-danger"
                  size="sm"
                  onClick={() => setShowDelete(true)}
                  disabled={busy}
                >
                  Eliminar
                </Button>
              </div>
            </div>
          ) : null}
        </Card.Footer>
      </Card>

      <Modal show={showEdit} onHide={() => setShowEdit(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Editar borrador</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSaveEdit}>
          <Modal.Body>
            <Form.Control
              as="textarea"
              rows={10}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              required
            />
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowEdit(false)} disabled={saving}>
              Cancelar
            </Button>
            <Button variant="warning" type="submit" disabled={saving || !editContent.trim()}>
              {saving ? "Guardando..." : "Guardar"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      <ConfirmModal
        show={showDiscard}
        title="Descartar borrador"
        message="¿Descartar este borrador? El contenido no se perderá pero no podrás confirmarlo."
        onConfirm={handleDiscard}
        onCancel={() => setShowDiscard(false)}
        variant="warning"
      />

      <ConfirmModal
        show={showDelete}
        title="Eliminar borrador"
        message="¿Eliminar este borrador permanentemente? Desaparecerá del listado."
        onConfirm={handleDelete}
        onCancel={() => setShowDelete(false)}
        variant="danger"
      />
    </>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function EntityDetailPage() {
  const { collectionId, entityId } = useParams<{ collectionId: string; entityId: string }>();

  const [collection, setCollection] = useState<Collection | null>(null);
  const [entity, setEntity] = useState<Entity | null>(null);
  const [loadingEntity, setLoadingEntity] = useState(true);
  const [entityError, setEntityError] = useState<string | null>(null);

  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loadingDrafts, setLoadingDrafts] = useState(true);
  const [draftsError, setDraftsError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const [showEdit, setShowEdit] = useState(false);
  const [editForm, setEditForm] = useState<UpdateEntityRequest>({
    type: "character",
    name: "",
    description: "",
  });
  const [saving, setSaving] = useState(false);

  async function fetchDrafts() {
    if (!collectionId || !entityId) return;
    setLoadingDrafts(true);
    setDraftsError(null);
    try {
      const res = await getDrafts(collectionId, entityId);
      setDrafts(res.data);
    } catch (e) {
      setDraftsError(getErrorMessage(e, "Error al cargar borradores"));
    } finally {
      setLoadingDrafts(false);
    }
  }

  useEffect(() => {
    if (!collectionId || !entityId) return;
    setLoadingEntity(true);
    Promise.all([
      getCollection(collectionId),
      getEntity(collectionId, entityId),
    ])
      .then(([col, ent]) => { setCollection(col); setEntity(ent); })
      .catch((e) => setEntityError(getErrorMessage(e, "Error al cargar")))
      .finally(() => setLoadingEntity(false));

    fetchDrafts();
  }, [collectionId, entityId]);

  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    if (!collectionId || !entityId) return;
    setGenerating(true);
    setGenerateError(null);
    try {
      await generateDraft(collectionId, entityId, { query });
      setQuery("");
      await fetchDrafts();
    } catch (err) {
      setGenerateError(getErrorMessage(err, "Error al generar borrador"));
    } finally {
      setGenerating(false);
    }
  }

  function openEdit() {
    if (!entity) return;
    setEditForm({ type: entity.type, name: entity.name, description: entity.description });
    setShowEdit(true);
  }

  async function handleSaveEntity(e: FormEvent) {
    e.preventDefault();
    if (!collectionId || !entityId) return;
    setSaving(true);
    try {
      const updated = await updateEntity(collectionId, entityId, editForm);
      setEntity(updated);
      setShowEdit(false);
    } catch (err) {
      setEntityError(getErrorMessage(err, "Error al actualizar entidad"));
    } finally {
      setSaving(false);
    }
  }

  if (loadingEntity) return <LoadingSpinner />;
  if (entityError) return <Alert variant="danger">{entityError}</Alert>;
  if (!entity || !collectionId || !entityId) return null;

  return (
    <>
      <Breadcrumb>
        <Breadcrumb.Item linkAs={Link} linkProps={{ to: "/" }}>
          Colecciones
        </Breadcrumb.Item>
        <Breadcrumb.Item linkAs={Link} linkProps={{ to: `/collections/${collectionId}` }}>
          {collection?.name ?? collectionId}
        </Breadcrumb.Item>
        <Breadcrumb.Item active>{entity.name}</Breadcrumb.Item>
      </Breadcrumb>

      <Card className="mb-4">
        <Card.Body>
          <div className="d-flex justify-content-between align-items-start">
            <div>
              <div className="mb-2">
                <Badge bg={ENTITY_TYPE_BADGE[entity.type]} className="me-2">
                  {entity.type}
                </Badge>
              </div>
              <h3 className="mb-1">{entity.name}</h3>
              <p className="text-muted mb-0">
                {entity.description || <em>Sin descripción</em>}
              </p>
            </div>
            <Button variant="outline-secondary" size="sm" onClick={openEdit}>
              Editar
            </Button>
          </div>
        </Card.Body>
      </Card>

      <h5 className="mb-3">Generar borrador</h5>
      {generateError && (
        <Alert variant="danger" onClose={() => setGenerateError(null)} dismissible>
          {generateError}
        </Alert>
      )}
      <Form onSubmit={handleGenerate} className="mb-4">
        <div className="d-flex gap-2 align-items-start">
          <Form.Control
            as="textarea"
            rows={2}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe qué quieres generar sobre esta entidad..."
            minLength={5}
            required
            disabled={generating}
          />
          <Button
            variant="warning"
            type="submit"
            disabled={generating || query.trim().length < 5}
            style={{ whiteSpace: "nowrap" }}
          >
            {generating ? (
              <>
                <Spinner animation="border" size="sm" className="me-1" />
                Generando...
              </>
            ) : (
              "Generar borrador"
            )}
          </Button>
        </div>
      </Form>

      <h5 className="mb-3">Borradores</h5>
      {draftsError && (
        <Alert variant="danger" onClose={() => setDraftsError(null)} dismissible>
          {draftsError}
        </Alert>
      )}
      {loadingDrafts ? (
        <LoadingSpinner text="Cargando borradores..." />
      ) : drafts.length === 0 ? (
        <p className="text-muted">No hay borradores todavía. Genera el primero arriba.</p>
      ) : (
        drafts.map((draft) => (
          <DraftCard
            key={draft.id}
            draft={draft}
            collectionId={collectionId}
            entityId={entityId}
            onAction={fetchDrafts}
          />
        ))
      )}

      <Modal show={showEdit} onHide={() => setShowEdit(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Editar entidad</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSaveEntity}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Tipo *</Form.Label>
              <Form.Select
                value={editForm.type}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, type: e.target.value as EntityType }))
                }
              >
                <option value="character">Personaje</option>
                <option value="scene">Escena</option>
                <option value="faction">Facción</option>
                <option value="item">Objeto</option>
              </Form.Select>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Nombre *</Form.Label>
              <Form.Control
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Descripción</Form.Label>
              <Form.Control
                as="textarea"
                rows={4}
                value={editForm.description}
                onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowEdit(false)} disabled={saving}>
              Cancelar
            </Button>
            <Button variant="warning" type="submit" disabled={saving || !editForm.name?.trim()}>
              {saving ? "Guardando..." : "Guardar"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </>
  );
}
