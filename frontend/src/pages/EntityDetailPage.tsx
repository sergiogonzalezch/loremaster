import { useEffect, useState, useCallback, useMemo } from "react";
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
import {
  getEntity,
  updateEntity,
  getCollection,
  generateContent,
} from "../api";
import { ApiAbortError } from "../api/apiClient";
import ContentCard from "../components/ContentCard";
import LoadingSpinner from "../components/LoadingSpinner";
import MarkdownContent from "../components/MarkdownContent";
import TokenCounter from "../components/TokenCounter";
import { useGenerate } from "../hooks/useGenerate";
import { useEntityContents } from "../hooks/useEntityContents";
import type { Collection, Entity, UpdateEntityRequest } from "../types";
import type { ContentCategory, EntityType } from "../utils/enums";
import { getErrorMessage } from "../utils/errors";
import {
  CATEGORY_LABELS,
  ENTITY_CATEGORY_MAP,
  ENTITY_TYPE_BADGE,
  ENTITY_TYPE_LABELS,
  MAX_PENDING_CONTENTS,
} from "../utils/constants";

export default function EntityDetailPage() {
  const { collectionId, entityId } = useParams<{
    collectionId: string;
    entityId: string;
  }>();

  const [collection, setCollection] = useState<Collection | null>(null);
  const [entity, setEntity] = useState<Entity | null>(null);
  const [loadingEntity, setLoadingEntity] = useState(true);
  const [entityError, setEntityError] = useState<string | null>(null);

  const {
    contents,
    loading: loadingContents,
    error: contentsError,
    refresh: refreshContents,
    setError: setContentsError,
  } = useEntityContents(collectionId, entityId);

  const [selectedCategory, setSelectedCategory] = useState<
    ContentCategory | ""
  >("");
  const [query, setQuery] = useState("");


  useEffect(() => {
    const controller = new AbortController();
    refreshContents({ signal: controller.signal });
    return () => controller.abort();
  }, [refreshContents]);

  const availableCategories = useMemo<ContentCategory[]>(
    () => (entity ? (ENTITY_CATEGORY_MAP[entity.type] ?? []) : []),
    [entity],
  );

  const pendingInCategory = contents.filter(
    (c) => c.status === "pending" && c.category === selectedCategory,
  ).length;
  const pendingLimitReached =
    selectedCategory !== "" && pendingInCategory >= MAX_PENDING_CONTENTS;

  const {
    error: generateError,
    isLoading: generating,
    isCancelled: generateCancelled,
    run: runGenerateContent,
    cancel: cancelGenerate,
    reset: resetGenerate,
  } = useGenerate(generateContent);

  const [showEdit, setShowEdit] = useState(false);
  const [editForm, setEditForm] = useState<UpdateEntityRequest>({
    type: "character",
    name: "",
    description: "",
  });
  const [saving, setSaving] = useState(false);

  const fetchEntityData = useCallback(
    async (signal?: AbortSignal) => {
      if (!collectionId || !entityId) return;
      setEntityError(null);
      setLoadingEntity(true);
      try {
        const [col, ent] = await Promise.all([
          getCollection(collectionId, signal),
          getEntity(collectionId, entityId, signal),
        ]);
        setCollection(col);
        setEntity(ent);
      } catch (e) {
        if (e instanceof ApiAbortError) return;
        setEntityError(getErrorMessage(e, "Error al cargar"));
      } finally {
        setLoadingEntity(false);
      }
    },
    [collectionId, entityId],
  );

  const refreshEntityQuiet = useCallback(async () => {
    if (!collectionId || !entityId) return;
    try {
      const ent = await getEntity(collectionId, entityId);
      setEntity(ent);
    } catch (e) {
      if (!(e instanceof ApiAbortError)) {
        // silent: la acción principal ya reporta errores
      }
    }
  }, [collectionId, entityId]);

  const handleContentAction = useCallback(async () => {
    await Promise.all([refreshContents(), refreshEntityQuiet()]);
  }, [refreshContents, refreshEntityQuiet]);

  useEffect(() => {
    const controller = new AbortController();
    fetchEntityData(controller.signal);
    return () => controller.abort();
  }, [fetchEntityData]);

  useEffect(() => {
    resetGenerate();
  }, [entityId, resetGenerate]);

  useEffect(() => {
    setSelectedCategory("");
  }, [entity?.type]);

  // Inicializar la categoría seleccionada cuando se cargan las categorías disponibles
  useEffect(() => {
    if (availableCategories.length > 0 && selectedCategory === "") {
      setSelectedCategory(availableCategories[0]);
    }
  }, [availableCategories, selectedCategory]);

  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    if (!collectionId || !entityId || selectedCategory === "") return;
    const result = await runGenerateContent(
      collectionId,
      entityId,
      selectedCategory,
      { query },
    );
    if (result) {
      setQuery("");
      await refreshContents();
    }
  }

  function openEdit() {
    if (!entity) return;
    setEditForm({
      type: entity.type,
      name: entity.name,
      description: entity.description,
    });
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
    <div className="lm-page">
      <Breadcrumb>
        <Breadcrumb.Item linkAs={Link} linkProps={{ to: "/" }}>
          Colecciones
        </Breadcrumb.Item>
        <Breadcrumb.Item
          linkAs={Link}
          linkProps={{ to: `/collections/${collectionId}` }}
        >
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
                  {ENTITY_TYPE_LABELS[entity.type]}
                </Badge>
              </div>
              <h3 className="mb-1">{entity.name}</h3>
              {entity.description ? (
                <MarkdownContent>{entity.description}</MarkdownContent>
              ) : (
                <p className="text-muted mb-0">
                  <em>Sin descripción</em>
                </p>
              )}
            </div>
            <Button variant="outline-secondary" size="sm" onClick={openEdit}>
              Editar
            </Button>
          </div>
        </Card.Body>
      </Card>

      <p className="lm-section-title">Generar contenido</p>
      {generateError != null && (
        <Alert variant="danger" onClose={resetGenerate} dismissible>
          {getErrorMessage(generateError, "Error al generar contenido")}
        </Alert>
      )}
      {generateCancelled && (
        <Alert variant="secondary" dismissible>
          Generación cancelada.
        </Alert>
      )}
      {pendingLimitReached && (
        <Alert variant="warning">
          Ya tienes {pendingInCategory} contenidos pendientes en esta categoría
          (máximo {MAX_PENDING_CONTENTS}). Confirma o descarta alguno antes de
          generar uno nuevo.
        </Alert>
      )}

      <Form onSubmit={handleGenerate} className="mb-4">
        <Form.Group className="mb-2">
          <Form.Label className="fw-semibold">Categoría</Form.Label>
          <Form.Select
            value={selectedCategory}
            onChange={(e) =>
              setSelectedCategory(e.target.value as ContentCategory)
            }
            disabled={generating}
            style={{ maxWidth: 280 }}
          >
            {availableCategories.map((cat) => (
              <option key={cat} value={cat}>
                {CATEGORY_LABELS[cat]}
              </option>
            ))}
          </Form.Select>
        </Form.Group>
        <div className="d-flex gap-2 align-items-start">
          <Form.Control
            as="textarea"
            rows={2}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe qué quieres generar sobre esta entidad..."
            minLength={5}
            required
            disabled={generating || pendingLimitReached}
          />
          <Button
            variant="warning"
            type="submit"
            disabled={
              generating ||
              pendingLimitReached ||
              query.trim().length < 5 ||
              selectedCategory === ""
            }
            style={{ whiteSpace: "nowrap" }}
            title={
              pendingLimitReached
                ? `Máximo ${MAX_PENDING_CONTENTS} contenidos pendientes por categoría`
                : undefined
            }
          >
            {generating ? (
              <>
                <Spinner animation="border" size="sm" className="me-1" />
                Generando...
              </>
            ) : (
              "Generar"
            )}
          </Button>
          {generating && (
            <Button
              variant="outline-secondary"
              type="button"
              onClick={cancelGenerate}
              style={{ whiteSpace: "nowrap" }}
            >
              Cancelar
            </Button>
          )}
        </div>
        <div className="d-flex justify-content-between mt-1">
          <TokenCounter text={query} />
          {selectedCategory !== "" &&
            !pendingLimitReached &&
            pendingInCategory > 0 && (
              <small className="text-muted">
                {pendingInCategory} / {MAX_PENDING_CONTENTS} borradores
                pendientes en esta categoría.
              </small>
            )}
        </div>
      </Form>

      <p className="lm-section-title">Contenidos generados</p>
      {contentsError && (
        <Alert
          variant="danger"
          onClose={() => setContentsError(null)}
          dismissible
        >
          {contentsError}
        </Alert>
      )}
      {loadingContents ? (
        <LoadingSpinner text="Cargando contenidos..." />
      ) : contents.length === 0 ? (
        <div className="lm-empty">
          <span className="lm-empty-glyph">✦</span>
          <p>No hay contenidos todavía.</p>
          <p>Genera el primero usando el formulario de arriba.</p>
        </div>
      ) : (
        contents.map((content) => (
          <ContentCard
            key={content.id}
            content={content}
            collectionId={collectionId}
            entityId={entityId}
            onAction={handleContentAction}
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
                  setEditForm((f) => ({
                    ...f,
                    type: e.target.value as EntityType,
                  }))
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
                value={editForm.name}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, name: e.target.value }))
                }
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Descripción</Form.Label>
              <Form.Control
                as="textarea"
                rows={4}
                value={editForm.description}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, description: e.target.value }))
                }
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button
              variant="secondary"
              onClick={() => setShowEdit(false)}
              disabled={saving}
            >
              Cancelar
            </Button>
            <Button
              variant="warning"
              type="submit"
              disabled={saving || !editForm.name?.trim()}
            >
              {saving ? "Guardando..." : "Guardar"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </div>
  );
}
