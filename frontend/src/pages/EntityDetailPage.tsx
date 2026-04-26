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
  Nav,
  Pagination,
  Spinner,
} from "react-bootstrap";
import {
  getEntity,
  updateEntity,
  getCollection,
  generateContent,
  getEntityCategories,
} from "../api";
import { ApiAbortError } from "../api/apiClient";
import ContentCard from "../components/ContentCard";
import LoadingSpinner from "../components/LoadingSpinner";
import MarkdownContent from "../components/MarkdownContent";
import TokenCounter from "../components/TokenCounter";
import { useGenerate } from "../hooks/useGenerate";
import { useEntityContents } from "../hooks/useEntityContents";
import type { Collection, Entity, EntityContent, UpdateEntityRequest } from "../types";
import type { ContentCategory, EntityType } from "../utils/enums";
import { formatDate } from "../utils/formatters";
import { getErrorMessage, parseApiError } from "../utils/errors";
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

  const [categoryMap, setCategoryMap] = useState(ENTITY_CATEGORY_MAP);
  const [collection, setCollection] = useState<Collection | null>(null);
  const [entity, setEntity] = useState<Entity | null>(null);
  const [loadingEntity, setLoadingEntity] = useState(true);
  const [entityError, setEntityError] = useState<string | null>(null);

  useEffect(() => {
    getEntityCategories()
      .then(setCategoryMap)
      .catch(() => {}); // fallback: keep local constants if backend unreachable
  }, []);

  const {
    contents,
    setContents,
    meta: contentsMeta,
    loading: loadingContents,
    error: contentsError,
    refresh: refreshContents,
    setError: setContentsError,
  } = useEntityContents(collectionId, entityId);

  const [selectedCategory, setSelectedCategory] = useState<
    ContentCategory | ""
  >("");
  const [contentsCategoryFilter, setContentsCategoryFilter] = useState<
    ContentCategory | ""
  >("");
  const [contentsStatusFilter, setContentsStatusFilter] = useState<
    "pending" | "confirmed" | "discarded"
  >("pending");
  const [contentsPage, setContentsPage] = useState(1);
  const [contentsPageSize, setContentsPageSize] = useState(10);
  const [query, setQuery] = useState("");
  const [lastSubmittedQuery, setLastSubmittedQuery] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    refreshContents({
      signal: controller.signal,
      category: contentsCategoryFilter || undefined,
      status: contentsStatusFilter,
      page: contentsPage,
      page_size: contentsPageSize,
    });
    return () => controller.abort();
  }, [
    contentsCategoryFilter,
    contentsStatusFilter,
    contentsPage,
    contentsPageSize,
    refreshContents,
  ]);

  const availableCategories = useMemo<ContentCategory[]>(
    () => (entity ? (categoryMap[entity.type] ?? []) : []),
    [entity, categoryMap],
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

  const handleOptimisticUpdate = useCallback(
    (id: string, patch: Partial<EntityContent> | null) => {
      setContents((prev) => {
        if (patch === null) return prev.filter((c) => c.id !== id);
        const target = prev.find((c) => c.id === id);
        if (!target) return prev;
        return prev.map((c) => {
          if (c.id === id) return { ...c, ...patch };
          if (
            patch.status === "confirmed" &&
            c.category === target.category &&
            c.status === "pending"
          ) {
            return { ...c, status: "discarded" as const };
          }
          return c;
        });
      });
    },
    [setContents],
  );

  const handleContentAction = useCallback(async () => {
    await Promise.all([
      refreshContents({
        silent: true,
        category: contentsCategoryFilter || undefined,
        status: contentsStatusFilter,
        page: contentsPage,
        page_size: contentsPageSize,
      }),
      refreshEntityQuiet(),
    ]);
  }, [
    contentsCategoryFilter,
    contentsStatusFilter,
    contentsPage,
    contentsPageSize,
    refreshContents,
    refreshEntityQuiet,
  ]);

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
      { query: trimmedQuery },
    );
    if (result) {
      await refreshContents({
        category: contentsCategoryFilter || undefined,
        status: contentsStatusFilter,
        page: contentsPage,
        page_size: contentsPageSize,
      });
    }
  }

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
      { query: lastSubmittedQuery.trim() },
    );
    if (result) {
      await refreshContents({
        category: contentsCategoryFilter || undefined,
        status: contentsStatusFilter,
        page: contentsPage,
        page_size: contentsPageSize,
      });
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

  const contentsPaginationItems = (() => {
    const totalPages = contentsMeta.total_pages;
    const page = contentsPage;
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
  })();

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
            <Button variant="outline-secondary" size="sm" onClick={openEdit}>
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
                ? `Máximo ${MAX_PENDING_CONTENTS} contenidos pendientes por categoría`
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
            pendingInCategory > 0 && (
              <small className="text-muted">
                {pendingInCategory} / {MAX_PENDING_CONTENTS} borradores
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

      <p className="lm-section-title">Contenidos generados</p>
      <Nav
        variant="tabs"
        activeKey={contentsStatusFilter}
        className="mb-3"
        onSelect={(key) => {
          if (!key) return;
          setContentsStatusFilter(key as "pending" | "confirmed" | "discarded");
          setContentsPage(1);
        }}
      >
        <Nav.Item>
          <Nav.Link eventKey="pending">Borradores</Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link eventKey="confirmed">Confirmados</Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link eventKey="discarded">Descartados</Nav.Link>
        </Nav.Item>
      </Nav>
      <Card className="mb-3">
        <Card.Body>
          <div className="d-flex justify-content-between flex-wrap align-items-end">
            <Form.Group style={{ minWidth: 240 }}>
              <Form.Label>Filtrar por categoría</Form.Label>
              <Form.Select
                value={contentsCategoryFilter}
                onChange={(e) => {
                  setContentsCategoryFilter(
                    e.target.value as ContentCategory | "",
                  );
                  setContentsPage(1);
                }}
              >
                <option value="">Todas</option>
                {availableCategories.map((cat) => (
                  <option key={cat} value={cat}>
                    {CATEGORY_LABELS[cat]}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            <Form.Group style={{ minWidth: 130 }}>
              <Form.Label>Page size</Form.Label>
              <Form.Select
                value={String(contentsPageSize)}
                onChange={(e) => {
                  setContentsPageSize(Number(e.target.value));
                  setContentsPage(1);
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
        <>
          {contents.map((content) => (
            <ContentCard
              key={content.id}
              content={content}
              collectionId={collectionId}
              entityId={entityId}
              onAction={handleContentAction}
              onOptimisticUpdate={handleOptimisticUpdate}
            />
          ))}
          {contentsMeta.total_pages > 1 && (
            <div className="d-flex justify-content-center mt-3">
              <Pagination>
                <Pagination.First
                  onClick={() => setContentsPage(1)}
                  disabled={contentsPage <= 1}
                />
                <Pagination.Prev
                  onClick={() => setContentsPage((p) => Math.max(1, p - 1))}
                  disabled={contentsPage <= 1}
                />
                {contentsPaginationItems.map((item) =>
                  typeof item === "number" ? (
                    <Pagination.Item
                      key={item}
                      active={item === contentsPage}
                      onClick={() => setContentsPage(item)}
                    >
                      {item}
                    </Pagination.Item>
                  ) : (
                    <Pagination.Ellipsis key={item} disabled />
                  ),
                )}
                <Pagination.Next
                  onClick={() =>
                    setContentsPage((p) =>
                      Math.min(contentsMeta.total_pages, p + 1),
                    )
                  }
                  disabled={contentsPage >= contentsMeta.total_pages}
                />
                <Pagination.Last
                  onClick={() => setContentsPage(contentsMeta.total_pages)}
                  disabled={contentsPage >= contentsMeta.total_pages}
                />
              </Pagination>
            </div>
          )}
        </>
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
