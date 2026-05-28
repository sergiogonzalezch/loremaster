import { useEffect, useCallback, useMemo, useReducer } from "react";
import { Link, useParams } from "react-router-dom";
import { Alert, Breadcrumb } from "react-bootstrap";
import { getEntity } from "../api/entities";
import { getCollection } from "../api/collections";
import { generateContent, getContents } from "../api/contents";
import { getEntityCategories, getLimits } from "../api/metadata";
import { ApiAbortError } from "../api/apiClient";
import EntityContentsPanel from "../components/EntityContentsPanel";
import EntityEditForm from "../components/EntityEditForm";
import EntityGenerateForm from "../components/EntityGenerateForm";
import EntityHeaderCard from "../components/EntityHeaderCard";
import ImagePanel from "../components/ImagePanel";
import LoadingSpinner from "../components/LoadingSpinner";
import { useGenerate } from "../hooks/useGenerate";
import type { Collection, Entity, EntityContent } from "../types";
import type { ContentCategory } from "../utils/enums";
import { getErrorMessage } from "../utils/errors";
import { ENTITY_CATEGORY_MAP } from "../utils/constants";

// ---------------------------------------------------------------------------
// Entity loading reducer — groups the 4 tightly-coupled load states
// ---------------------------------------------------------------------------

type EntityLoadState = {
  entity: Entity | null;
  collection: Collection | null;
  loading: boolean;
  error: string | null;
};

type EntityLoadAction =
  | { type: "FETCH_START" }
  | { type: "FETCH_SUCCESS"; entity: Entity; collection: Collection }
  | { type: "FETCH_ERROR"; error: string }
  | { type: "UPDATE_ENTITY"; entity: Entity };

function entityLoadReducer(
  state: EntityLoadState,
  action: EntityLoadAction,
): EntityLoadState {
  switch (action.type) {
    case "FETCH_START":
      return { ...state, loading: true, error: null };
    case "FETCH_SUCCESS":
      return {
        loading: false,
        error: null,
        entity: action.entity,
        collection: action.collection,
      };
    case "FETCH_ERROR":
      return { ...state, loading: false, error: action.error };
    case "UPDATE_ENTITY":
      return { ...state, entity: action.entity };
  }
}

// ---------------------------------------------------------------------------
// Page UI reducer — groups the remaining coordinated UI state
// ---------------------------------------------------------------------------

type PageUIState = {
  categoryMap: typeof ENTITY_CATEGORY_MAP;
  maxPendingContents: number;
  selectedCategory: ContentCategory | "";
  pendingInCategoryCount: number;
  showEdit: boolean;
  imagePanel: { show: boolean; content: EntityContent | null };
  contentsRefreshTrigger: number;
};

type PageUIAction =
  | {
      type: "SET_CONFIG";
      categoryMap: typeof ENTITY_CATEGORY_MAP;
      maxPendingContents: number;
    }
  | { type: "SET_CATEGORY"; category: ContentCategory | "" }
  | { type: "SET_PENDING_COUNT"; count: number }
  | { type: "SET_EDIT"; show: boolean }
  | { type: "OPEN_IMAGE_PANEL"; content: EntityContent }
  | { type: "CLOSE_IMAGE_PANEL" }
  | { type: "BUMP_REFRESH" };

function pageUIReducer(state: PageUIState, action: PageUIAction): PageUIState {
  switch (action.type) {
    case "SET_CONFIG":
      return {
        ...state,
        categoryMap: action.categoryMap,
        maxPendingContents: action.maxPendingContents,
      };
    case "SET_CATEGORY":
      return { ...state, selectedCategory: action.category };
    case "SET_PENDING_COUNT":
      return { ...state, pendingInCategoryCount: action.count };
    case "SET_EDIT":
      return { ...state, showEdit: action.show };
    case "OPEN_IMAGE_PANEL":
      return { ...state, imagePanel: { show: true, content: action.content } };
    case "CLOSE_IMAGE_PANEL":
      return { ...state, imagePanel: { show: false, content: null } };
    case "BUMP_REFRESH":
      return {
        ...state,
        contentsRefreshTrigger: state.contentsRefreshTrigger + 1,
      };
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function EntityDetailPage() {
  const { collectionId, entityId } = useParams<{
    collectionId: string;
    entityId: string;
  }>();

  const [entityLoad, dispatchEntity] = useReducer(entityLoadReducer, {
    entity: null,
    collection: null,
    loading: true,
    error: null,
  });
  const {
    entity,
    collection,
    loading: loadingEntity,
    error: entityError,
  } = entityLoad;

  const [ui, dispatchUI] = useReducer(pageUIReducer, {
    categoryMap: ENTITY_CATEGORY_MAP,
    maxPendingContents: 5,
    selectedCategory: "",
    pendingInCategoryCount: 0,
    showEdit: false,
    imagePanel: { show: false, content: null },
    contentsRefreshTrigger: 0,
  });
  const {
    categoryMap,
    maxPendingContents,
    selectedCategory,
    pendingInCategoryCount,
    showEdit,
    imagePanel,
    contentsRefreshTrigger,
  } = ui;

  useEffect(() => {
    getEntityCategories()
      .then((map) => {
        getLimits()
          .then((l) =>
            dispatchUI({
              type: "SET_CONFIG",
              categoryMap: map,
              maxPendingContents: l.max_pending_contents,
            }),
          )
          .catch(() =>
            dispatchUI({
              type: "SET_CONFIG",
              categoryMap: map,
              maxPendingContents: 5,
            }),
          );
      })
      .catch(() => {}); // fallback: keep local constants if backend unreachable
  }, []);

  const availableCategories = useMemo<ContentCategory[]>(
    () => (entity ? (categoryMap[entity.type] ?? []) : []),
    [entity, categoryMap],
  );

  const {
    error: generateError,
    isLoading: generating,
    isCancelled: generateCancelled,
    run: runGenerateContent,
    cancel: cancelGenerate,
    reset: resetGenerate,
  } = useGenerate(generateContent);

  const fetchEntityData = useCallback(
    async (signal?: AbortSignal) => {
      if (!collectionId || !entityId) return;
      dispatchEntity({ type: "FETCH_START" });
      try {
        const [col, ent] = await Promise.all([
          getCollection(collectionId, signal),
          getEntity(collectionId, entityId, signal),
        ]);
        dispatchEntity({ type: "FETCH_SUCCESS", entity: ent, collection: col });
      } catch (e) {
        if (e instanceof ApiAbortError) return;
        dispatchEntity({
          type: "FETCH_ERROR",
          error: getErrorMessage(e, "Error al cargar"),
        });
      }
    },
    [collectionId, entityId],
  );

  // Notificada por EntityContentsPanel tras cualquier acción de contenido
  // (confirm/discard/edit/share/delete). Refresca la entity y dispara
  // BUMP_REFRESH para que el efecto de pendingCount se re-ejecute.
  const handleContentMutated = useCallback(async () => {
    if (!collectionId || !entityId) return;
    try {
      const ent = await getEntity(collectionId, entityId);
      dispatchEntity({ type: "UPDATE_ENTITY", entity: ent });
    } catch (e) {
      if (!(e instanceof ApiAbortError)) {
        // silent: la acción principal ya reporta errores
      }
    }
    dispatchUI({ type: "BUMP_REFRESH" });
  }, [collectionId, entityId]);

  useEffect(() => {
    const controller = new AbortController();
    fetchEntityData(controller.signal);
    return () => controller.abort();
  }, [fetchEntityData]);

  useEffect(() => {
    resetGenerate();
  }, [entityId, resetGenerate]);

  // Primitivos estables: el efecto solo se re-ejecuta cuando cambian id/tipo o categoryMap.
  // Evita re-renders por cambio de referencia del objeto entity al re-fetchear los mismos datos.
  const currentEntityId = entity?.id;
  const currentEntityType = entity?.type;
  useEffect(() => {
    const cats = currentEntityType
      ? (categoryMap[currentEntityType] ?? [])
      : [];
    dispatchUI({ type: "SET_CATEGORY", category: cats[0] ?? "" });
  }, [currentEntityId, currentEntityType, categoryMap]);

  // El padre dueño del count: lo refresca cuando cambia la categoría o
  // contentsRefreshTrigger (bumpeado tras generar/confirmar/descartar).
  // Evita el anti-patrón prop-callback-in-effect.
  useEffect(() => {
    if (!collectionId || !entityId || !selectedCategory) {
      dispatchUI({ type: "SET_PENDING_COUNT", count: 0 });
      return;
    }
    const controller = new AbortController();
    getContents(
      collectionId,
      entityId,
      { category: selectedCategory, status: "pending", page: 1, page_size: 1 },
      controller.signal,
    )
      .then((res) =>
        dispatchUI({ type: "SET_PENDING_COUNT", count: res.meta.total }),
      )
      .catch((e) => {
        if (!(e instanceof ApiAbortError)) {
          dispatchUI({ type: "SET_PENDING_COUNT", count: 0 });
        }
      });
    return () => controller.abort();
  }, [collectionId, entityId, selectedCategory, contentsRefreshTrigger]);

  async function handleGenerateSubmit(
    queryText: string,
    model: string | undefined,
  ) {
    if (!collectionId || !entityId || selectedCategory === "") return;
    const result = await runGenerateContent(
      collectionId,
      entityId,
      selectedCategory,
      { query: queryText, model },
    );
    if (result) dispatchUI({ type: "BUMP_REFRESH" });
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

      <EntityHeaderCard
        entity={entity}
        onEdit={() => dispatchUI({ type: "SET_EDIT", show: true })}
      />

      <EntityGenerateForm
        availableCategories={availableCategories}
        selectedCategory={selectedCategory}
        onCategoryChange={(cat) =>
          dispatchUI({ type: "SET_CATEGORY", category: cat })
        }
        generating={generating}
        generateError={generateError}
        generateCancelled={generateCancelled}
        pendingInCategoryCount={pendingInCategoryCount}
        maxPendingContents={maxPendingContents}
        onSubmit={handleGenerateSubmit}
        onCancel={cancelGenerate}
        onDismissError={resetGenerate}
      />

      <EntityContentsPanel
        collectionId={collectionId}
        entityId={entityId}
        availableCategories={availableCategories}
        refreshTrigger={contentsRefreshTrigger}
        onContentMutated={handleContentMutated}
        onOpenImagePanel={(content) =>
          dispatchUI({ type: "OPEN_IMAGE_PANEL", content })
        }
      />

      <ImagePanel
        key={imagePanel.content?.id ?? "none"}
        collectionId={collectionId}
        entityId={entityId}
        show={imagePanel.show}
        onHide={() => dispatchUI({ type: "CLOSE_IMAGE_PANEL" })}
        onGenerated={() => {}}
        initialContent={imagePanel.content}
      />

      <EntityEditForm
        show={showEdit}
        entity={entity}
        collectionId={collectionId}
        entityId={entityId}
        onClose={() => dispatchUI({ type: "SET_EDIT", show: false })}
        onSaved={(updated) => {
          dispatchEntity({ type: "UPDATE_ENTITY", entity: updated });
          dispatchUI({ type: "SET_EDIT", show: false });
        }}
        onError={(msg) => dispatchEntity({ type: "FETCH_ERROR", error: msg })}
      />
    </div>
  );
}
