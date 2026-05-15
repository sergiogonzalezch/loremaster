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
  Spinner,
} from "react-bootstrap";
import {
  getEntity,
  getCollection,
  generateContent,
  getEntityCategories,
  getLimits,
} from "../api";
import { ApiAbortError } from "../api/apiClient";
import EntityContentsPanel from "../components/EntityContentsPanel";
import ImagePanel from "../components/ImagePanel";
import EntityEditForm from "../components/EntityEditForm";
import LoadingSpinner from "../components/LoadingSpinner";
import MarkdownContent from "../components/MarkdownContent";
import ModelSelector from "../components/ModelSelector";
import TokenCounter from "../components/TokenCounter";
import { useGenerate } from "../hooks/useGenerate";
import type { Collection, Entity, EntityContent } from "../types";
import type { ContentCategory } from "../utils/enums";
import { formatDate } from "../utils/formatters";
import { getErrorMessage, parseApiError } from "../utils/errors";
import {
  CATEGORY_LABELS,
  ENTITY_CATEGORY_MAP,
  ENTITY_TYPE_BADGE,
  ENTITY_TYPE_LABELS,
} from "../utils/constants";

/**
 * Página de detalle de una entidad.
 *
 * Muestra la información de la entidad, permite generar contenido
 * para diferentes categorías, gestionar borradores pendientes y
 * generar imágenes asociadas a los contenidos confirmados.
 */
export default function EntityDetailPage() {
  const { collectionId, entityId } = useParams<{
    collectionId: string;
    entityId: string;
  }>();

  const [categoryMap, setCategoryMap] = useState(ENTITY_CATEGORY_MAP);
  const [maxPendingContents, setMaxPendingContents] = useState(5);
  const [collection, setCollection] = useState<Collection | null>(null);
  const [entity, setEntity] = useState<Entity | null>(null);
  const [loadingEntity, setLoadingEntity] = useState(true);
  const [entityError, setEntityError] = useState<string | null>(null);

  useEffect(() => {
    getEntityCategories()
      .then(setCategoryMap)
      .catch(() => {}); // fallback: keep local constants if backend unreachable
    getLimits()
      .then((l) => setMaxPendingContents(l.max_pending_contents))
      .catch(() => {}); // fallback: keep default 5 if backend unreachable
  }, []);

  const [selectedCategory, setSelectedCategory] = useState<
    ContentCategory | ""
  >("");
  const [pendingInCategoryCount, setPendingInCategoryCount] = useState(0);
  const [query, setQuery] = useState("");
  const [lastSubmittedQuery, setLastSubmittedQuery] = useState("");
  const [showEdit, setShowEdit] = useState(false);
  const [showImagePanel, setShowImagePanel] = useState(false);
  const [selectedContentForImage, setSelectedContentForImage] =
    useState<EntityContent | null>(null);
  const [contentsRefreshTrigger, setContentsRefreshTrigger] = useState(0);
  const [selectedModel, setSelectedModel] = useState<string | undefined>(
    undefined,
  );

  const availableCategories = useMemo<ContentCategory[]>(
    () => (entity ? (categoryMap[entity.type] ?? []) : []),
    [entity, categoryMap],
  );

  const pendingLimitReached =
    selectedCategory !== "" && pendingInCategoryCount >= maxPendingContents;

  const {
    error: generateError,
    isLoading: generating,
    isCancelled: generateCancelled,
    run: runGenerateContent,
    cancel: cancelGenerate,
    reset: resetGenerate,
  } = useGenerate(generateContent);

  /**
   * Carga la colección y la entidad desde la API.
   *
   * @param signal - Señal de aborto para cancelar la petición.
   */
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

  /**
   * Refresca silenciosamente los datos de la entidad sin mostrar
   * estados de carga ni sobrescribir errores existentes.
   */
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

  /**
   * Actualiza el conteo de contenidos pendientes en la categoría seleccionada.
   *
   * @param count - Número de contenidos pendientes.
   */
  const handlePendingCountChange = useCallback((count: number) => {
    setPendingInCategoryCount(count);
  }, []);

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

  useEffect(() => {
    if (availableCategories.length > 0 && selectedCategory === "") {
      setSelectedCategory(availableCategories[0]);
    }
  }, [availableCategories, selectedCategory]);

  /**
   * Genera un nuevo contenido para la entidad en la categoría seleccionada.
   *
   * @param e - Evento del formulario de generación.
   */
  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    if (
      !collectionId ||
      !entityId ||
      selectedCategory === "" ||
      query.trim().length < 5
    ) {
      return;
    }
    const trimmedQuery = query.trim();
    setLastSubmittedQuery(trimmedQuery);
    const result = await runGenerateContent(
      collectionId,
      entityId,
      selectedCategory,
      { query: trimmedQuery, model: selectedModel },
    );
    if (result) {
      setContentsRefreshTrigger((t) => t + 1);
    }
  }

  /**
   * Reenvía el último prompt para regenerar contenido en la categoría activa.
   */
  async function handleRegenerate() {
    if (
      !collectionId ||
      !entityId ||
      selectedCategory === "" ||
      lastSubmittedQuery.trim().length < 5
    ) {
      return;
    }
    const result = await runGenerateContent(
      collectionId,
      entityId,
      selectedCategory,
      { query: lastSubmittedQuery.trim(), model: selectedModel },
    );
    if (result) {
      setContentsRefreshTrigger((t) => t + 1);
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
              <div className="mt-2 d-flex gap-3">
                <small className="text-muted">
                  Creada: {formatDate(entity.created_at)}
                </small>
                {entity.updated_at && (
                  <small className="text-muted">
                    Editada: {formatDate(entity.updated_at, true)}
                  </small>
                )}
              </div>
            </div>
            <Button
              variant="outline-secondary"
              size="sm"
              onClick={() => setShowEdit(true)}
            >
              Editar
            </Button>
          </div>
        </Card.Body>
      </Card>

      <p className="lm-section-title">Generar contenido</p>
      {generateError != null &&
        (() => {
          const { variant, text } = parseApiError(
            generateError,
            "Error al generar contenido",
          );
          return (
            <Alert variant={variant} onClose={resetGenerate} dismissible>
              {text}
            </Alert>
          );
        })()}
      {generateCancelled && (
        <Alert variant="secondary" dismissible>
          Generación cancelada.
        </Alert>
      )}
      {pendingLimitReached && (
        <Alert variant="warning">
          Ya tienes {pendingInCategoryCount} contenidos pendientes en esta
          categoría (máximo {maxPendingContents}). Confirma o descarta alguno
          antes de generar uno nuevo.
        </Alert>
      )}

      <Form onSubmit={handleGenerate} className="mb-4">
        <div className="d-flex gap-3 flex-wrap mb-2">
          <Form.Group>
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
          <ModelSelector disabled={generating} onChange={setSelectedModel} />
        </div>
        <div className="d-flex gap-2 align-items-start flex-wrap">
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
                ? `Máximo ${maxPendingContents} contenidos pendientes por categoría`
                : undefined
            }
          >
            {generating ? (
              <>
                <Spinner
                  animation="border"
                  size="sm"
                  className="me-1 lm-spinner-inline"
                />
                Generando...
              </>
            ) : (
              "Generar"
            )}
          </Button>
          <Button
            variant="outline-secondary"
            type="button"
            onClick={handleRegenerate}
            disabled={
              generating ||
              pendingLimitReached ||
              lastSubmittedQuery.trim().length < 5 ||
              selectedCategory === ""
            }
            title={
              lastSubmittedQuery
                ? `Reutilizar último prompt: "${lastSubmittedQuery}"`
                : "Genera contenido una vez para habilitar regenerar"
            }
          >
            ↻ Regenerar
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
            pendingInCategoryCount > 0 && (
              <small className="text-muted">
                {pendingInCategoryCount} / {maxPendingContents} borradores
                pendientes en esta categoría.
              </small>
            )}
        </div>
      </Form>
      {generating && (
        <div className="lm-llm-loading mb-4">
          <div className="lm-llm-loading-bar" />
          <small className="text-muted">
            Procesando prompt con el modelo y preparando un nuevo borrador...
          </small>
        </div>
      )}

      <EntityContentsPanel
        collectionId={collectionId}
        entityId={entityId}
        availableCategories={availableCategories}
        selectedCategory={selectedCategory}
        refreshTrigger={contentsRefreshTrigger}
        onRefreshEntity={refreshEntityQuiet}
        onPendingCountChange={handlePendingCountChange}
        onOpenImagePanel={(content) => {
          setSelectedContentForImage(content);
          setShowImagePanel(true);
        }}
      />

      <ImagePanel
        collectionId={collectionId}
        entityId={entityId}
        show={showImagePanel}
        onHide={() => {
          setShowImagePanel(false);
          setSelectedContentForImage(null);
        }}
        onGenerated={() => {}}
        initialContent={selectedContentForImage}
      />

      <EntityEditForm
        show={showEdit}
        entity={entity}
        collectionId={collectionId}
        entityId={entityId}
        onClose={() => setShowEdit(false)}
        onSaved={(updated) => {
          setEntity(updated);
          setShowEdit(false);
        }}
        onError={setEntityError}
      />
    </div>
  );
}
