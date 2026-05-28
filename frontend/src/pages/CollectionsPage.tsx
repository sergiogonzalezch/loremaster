import { useCallback, useEffect, useReducer } from "react";
import type { FormEvent, Reducer } from "react";
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
import {
  getCollections,
  createCollection,
  updateCollection,
  deleteCollection,
  bulkDeleteCollections,
} from "../api/collections";
import { ApiAbortError } from "../api/apiClient";
import LoadingSpinner from "../components/LoadingSpinner";
import ConfirmModal from "../components/ConfirmModal";
import type { Collection } from "../types";
import { formatDate } from "../utils/formatters";
import { parseApiError } from "../utils/errors";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { usePagination } from "../hooks/usePagination";
import { useDeleteConfirm } from "../hooks/useDeleteConfirm";

// ── Reducers ─────────────────────────────────────────────────────────────────

type FiltersState = {
  name: string;
  createdAfter: string;
  createdBefore: string;
  order: "asc" | "desc";
};

type FiltersAction =
  | { type: "SET_NAME"; value: string }
  | { type: "SET_AFTER"; value: string }
  | { type: "SET_BEFORE"; value: string }
  | { type: "SET_ORDER"; value: "asc" | "desc" }
  | { type: "RESET" };

const filtersReducer: Reducer<FiltersState, FiltersAction> = (
  state,
  action,
) => {
  switch (action.type) {
    case "SET_NAME":
      return { ...state, name: action.value };
    case "SET_AFTER":
      return { ...state, createdAfter: action.value };
    case "SET_BEFORE":
      return { ...state, createdBefore: action.value };
    case "SET_ORDER":
      return { ...state, order: action.value };
    case "RESET":
      return { name: "", createdAfter: "", createdBefore: "", order: "desc" };
  }
};

type ListState = {
  collections: Collection[];
  totalPages: number;
  loading: boolean;
  error: { variant: "warning" | "danger"; text: string } | null;
};

type ListAction =
  | { type: "FETCH_START" }
  | { type: "FETCH_SUCCESS"; collections: Collection[]; totalPages: number }
  | {
      type: "FETCH_ERROR";
      error: { variant: "warning" | "danger"; text: string };
    }
  | {
      type: "SHOW_ERROR";
      error: { variant: "warning" | "danger"; text: string };
    }
  | { type: "DISMISS_ERROR" };

const listReducer: Reducer<ListState, ListAction> = (state, action) => {
  switch (action.type) {
    case "FETCH_START":
      return { ...state, loading: true, error: null };
    case "FETCH_SUCCESS":
      return {
        collections: action.collections,
        totalPages: action.totalPages,
        loading: false,
        error: null,
      };
    case "FETCH_ERROR":
      return { ...state, loading: false, error: action.error };
    case "SHOW_ERROR":
      return { ...state, error: action.error };
    case "DISMISS_ERROR":
      return { ...state, error: null };
  }
};

type BulkState = {
  selectedIds: Set<string>;
  bulkDeleting: boolean;
  showBulkConfirm: boolean;
};

type BulkAction =
  | { type: "TOGGLE_ONE"; id: string }
  | { type: "REMOVE_ONE"; id: string }
  | { type: "CLEAR" }
  | { type: "OPEN_CONFIRM" }
  | { type: "CLOSE_CONFIRM" }
  | { type: "DELETE_START" }
  | { type: "DELETE_DONE" };

const bulkReducer: Reducer<BulkState, BulkAction> = (state, action) => {
  switch (action.type) {
    case "TOGGLE_ONE": {
      const next = new Set(state.selectedIds);
      if (next.has(action.id)) next.delete(action.id);
      else next.add(action.id);
      return { ...state, selectedIds: next };
    }
    case "REMOVE_ONE": {
      if (!state.selectedIds.has(action.id)) return state;
      const next = new Set(state.selectedIds);
      next.delete(action.id);
      return { ...state, selectedIds: next };
    }
    case "CLEAR":
      return { ...state, selectedIds: new Set() };
    case "OPEN_CONFIRM":
      return { ...state, showBulkConfirm: true };
    case "CLOSE_CONFIRM":
      return { ...state, showBulkConfirm: false };
    case "DELETE_START":
      return { ...state, bulkDeleting: true };
    case "DELETE_DONE":
      return {
        selectedIds: new Set(),
        bulkDeleting: false,
        showBulkConfirm: false,
      };
  }
};

type CreateState = {
  show: boolean;
  name: string;
  description: string;
  creating: boolean;
};
type CreateAction =
  | { type: "OPEN" }
  | { type: "CLOSE" }
  | { type: "SET_NAME"; value: string }
  | { type: "SET_DESCRIPTION"; value: string }
  | { type: "SUBMIT_START" }
  | { type: "SUBMIT_DONE" };

const createReducer: Reducer<CreateState, CreateAction> = (state, action) => {
  switch (action.type) {
    case "OPEN":
      return { ...state, show: true };
    case "CLOSE":
      return { show: false, name: "", description: "", creating: false };
    case "SET_NAME":
      return { ...state, name: action.value };
    case "SET_DESCRIPTION":
      return { ...state, description: action.value };
    case "SUBMIT_START":
      return { ...state, creating: true };
    case "SUBMIT_DONE":
      return { show: false, name: "", description: "", creating: false };
  }
};

type EditState = {
  target: Collection | null;
  name: string;
  description: string;
  editing: boolean;
};
type EditAction =
  | { type: "OPEN"; target: Collection }
  | { type: "CLOSE" }
  | { type: "SET_NAME"; value: string }
  | { type: "SET_DESCRIPTION"; value: string }
  | { type: "SUBMIT_START" }
  | { type: "SUBMIT_DONE" };

const editReducer: Reducer<EditState, EditAction> = (state, action) => {
  switch (action.type) {
    case "OPEN":
      return {
        target: action.target,
        name: action.target.name,
        description: action.target.description,
        editing: false,
      };
    case "CLOSE":
      return { target: null, name: "", description: "", editing: false };
    case "SET_NAME":
      return { ...state, name: action.value };
    case "SET_DESCRIPTION":
      return { ...state, description: action.value };
    case "SUBMIT_START":
      return { ...state, editing: true };
    case "SUBMIT_DONE":
      return { target: null, name: "", description: "", editing: false };
  }
};

/**
 * Página de listado y gestión de colecciones.
 *
 * Muestra las colecciones del usuario autenticado con filtros por nombre,
 * rango de fechas y orden. Permite crear, editar y eliminar colecciones,
 * así como navegar al detalle de cada una.
 */
export default function CollectionsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [list, dispatchList] = useReducer(listReducer, {
    collections: [],
    totalPages: 0,
    loading: true,
    error: null,
  });
  const { collections, totalPages, loading, error } = list;

  const [bulk, dispatchBulk] = useReducer(bulkReducer, {
    selectedIds: new Set<string>(),
    bulkDeleting: false,
    showBulkConfirm: false,
  });

  const [create, dispatchCreate] = useReducer(createReducer, {
    show: false,
    name: "",
    description: "",
    creating: false,
  });

  const [edit, dispatchEdit] = useReducer(editReducer, {
    target: null,
    name: "",
    description: "",
    editing: false,
  });

  const [filters, dispatchFilters] = useReducer(filtersReducer, {
    name: searchParams.get("name") ?? "",
    createdAfter: searchParams.get("created_after")?.slice(0, 10) ?? "",
    createdBefore: searchParams.get("created_before")?.slice(0, 10) ?? "",
    order: (searchParams.get("order") as "asc" | "desc") ?? "desc",
  });
  const { name, createdAfter, createdBefore, order } = filters;

  const page = Number(searchParams.get("page") ?? 1);
  const pageSize = Number(searchParams.get("page_size") ?? 12);

  const debouncedName = useDebouncedValue(name);

  /**
   * Actualiza los parámetros de búsqueda de la URL sincronizando
   * el estado del filtro con la query string.
   *
   * @param updates - Mapa de clave-valor con los parámetros a modificar.
   */
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

  /**
   * Carga las colecciones desde la API aplicando los filtros
   * y paginación actuales.
   *
   * @param signal - Señal de aborto para cancelar la petición.
   */
  const fetchCollections = useCallback(
    async (signal?: AbortSignal) => {
      dispatchList({ type: "FETCH_START" });
      try {
        const res = await getCollections(
          {
            page,
            page_size: pageSize,
            name: debouncedName || undefined,
            created_after: createdAfter || undefined,
            created_before: createdBefore || undefined,
            order,
          },
          signal,
        );
        dispatchList({
          type: "FETCH_SUCCESS",
          collections: res.data,
          totalPages: res.meta.total_pages,
        });
        if (res.meta.total_pages > 0 && page > res.meta.total_pages) {
          setParam({ page: String(res.meta.total_pages) });
        }
      } catch (e) {
        if (e instanceof ApiAbortError) return;
        dispatchList({
          type: "FETCH_ERROR",
          error: parseApiError(e, "Error al cargar las colecciones"),
        });
      }
    },
    [
      page,
      pageSize,
      debouncedName,
      createdAfter,
      createdBefore,
      order,
      setParam,
    ],
  );

  const deleteConfirm = useDeleteConfirm<Collection>({
    onDelete: async (col) => {
      await deleteCollection(col.id);
      dispatchBulk({ type: "REMOVE_ONE", id: col.id });
      await fetchCollections();
    },
    onError: (e) =>
      dispatchList({
        type: "SHOW_ERROR",
        error: parseApiError(e, "Error al eliminar la colección"),
      }),
  });

  useEffect(() => {
    const controller = new AbortController();
    fetchCollections(controller.signal);
    return () => controller.abort();
  }, [fetchCollections]);

  useEffect(() => {
    window.dispatchEvent(
      new CustomEvent("lm:collections", {
        detail: { collections },
      }),
    );
  }, [collections]);

  // Clear collection stars when leaving this page
  useEffect(() => {
    return () => {
      window.dispatchEvent(
        new CustomEvent("lm:collections", {
          detail: { collections: [] },
        }),
      );
    };
  }, []);

  async function handleBulkDelete() {
    dispatchBulk({ type: "DELETE_START" });
    try {
      await bulkDeleteCollections([...bulk.selectedIds]);
      dispatchBulk({ type: "DELETE_DONE" });
      await fetchCollections();
    } catch (e) {
      dispatchList({
        type: "SHOW_ERROR",
        error: parseApiError(
          e,
          "Error al eliminar las colecciones seleccionadas",
        ),
      });
      dispatchBulk({ type: "DELETE_DONE" });
    }
  }

  async function handleSaveEdit(e: FormEvent) {
    e.preventDefault();
    if (!edit.target) return;
    dispatchEdit({ type: "SUBMIT_START" });
    try {
      await updateCollection(edit.target.id, {
        name: edit.name.trim(),
        description: edit.description.trim(),
      });
      dispatchEdit({ type: "SUBMIT_DONE" });
      await fetchCollections();
    } catch (e) {
      dispatchList({
        type: "SHOW_ERROR",
        error: parseApiError(e, "Error al actualizar la colección."),
      });
      dispatchEdit({ type: "SUBMIT_DONE" });
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    dispatchCreate({ type: "SUBMIT_START" });
    try {
      await createCollection({
        name: create.name,
        description: create.description,
      });
      dispatchCreate({ type: "SUBMIT_DONE" });
      await fetchCollections();
    } catch (e) {
      dispatchList({
        type: "SHOW_ERROR",
        error: parseApiError(e, "Error al crear la colección"),
      });
      dispatchCreate({ type: "SUBMIT_DONE" });
    }
  }

  const paginationItems = usePagination(page, totalPages);

  return (
    <div className="lm-page">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Colecciones</h2>
        <div className="d-flex gap-2 align-items-center">
          {bulk.selectedIds.size > 0 && (
            <Button
              variant="danger"
              onClick={() => dispatchBulk({ type: "OPEN_CONFIRM" })}
              disabled={bulk.bulkDeleting}
            >
              Eliminar seleccionadas ({bulk.selectedIds.size})
            </Button>
          )}
          <Button
            variant="warning"
            onClick={() => dispatchCreate({ type: "OPEN" })}
          >
            + Nueva colección
          </Button>
        </div>
      </div>

      <Card className="mb-3">
        <Card.Body>
          <Row className="g-3">
            <Col md={4}>
              <Form.Label>Buscar por nombre</Form.Label>
              <Form.Control
                value={name}
                onChange={(e) => {
                  dispatchFilters({ type: "SET_NAME", value: e.target.value });
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
                  dispatchFilters({ type: "SET_AFTER", value: e.target.value });
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
                  dispatchFilters({
                    type: "SET_BEFORE",
                    value: e.target.value,
                  });
                  setParam({
                    page: "1",
                    created_before: e.target.value || null,
                  });
                }}
              />
            </Col>
            <Col md={2}>
              <Form.Label>Orden</Form.Label>
              <Form.Select
                value={order}
                onChange={(e) => {
                  const val = e.target.value as "asc" | "desc";
                  dispatchFilters({ type: "SET_ORDER", value: val });
                  setParam({ page: "1", order: val });
                }}
              >
                <option value="desc">Más recientes</option>
                <option value="asc">Más antiguos</option>
              </Form.Select>
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
                dispatchFilters({ type: "RESET" });
                setParam({
                  page: "1",
                  page_size: String(pageSize),
                  name: null,
                  created_after: null,
                  created_before: null,
                  order: null,
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
          onClose={() => dispatchList({ type: "DISMISS_ERROR" })}
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
                    <div className="d-flex align-items-start justify-content-between gap-2 mb-1">
                      <div className="d-flex align-items-start gap-2">
                        <Form.Check
                          type="checkbox"
                          checked={bulk.selectedIds.has(col.id)}
                          onClick={(e) => e.stopPropagation()}
                          onChange={() =>
                            dispatchBulk({ type: "TOGGLE_ONE", id: col.id })
                          }
                          className="mt-1 flex-shrink-0"
                        />
                        <Card.Title className="mb-0">{col.name}</Card.Title>
                      </div>
                    </div>
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
                    <div className="mt-2 d-flex gap-3">
                      <small className="text-muted">
                        <strong>{col.document_count}</strong>{" "}
                        {col.document_count === 1 ? "documento" : "documentos"}
                      </small>
                      <small className="text-muted">
                        <strong>{col.entity_count}</strong>{" "}
                        {col.entity_count === 1 ? "entidad" : "entidades"}
                      </small>
                    </div>
                  </Card.Body>
                  <Card.Footer className="d-flex justify-content-between align-items-center">
                    <small className="text-muted">
                      {col.updated_at
                        ? `Editada ${formatDate(col.updated_at)}`
                        : formatDate(col.created_at)}
                    </small>
                    <div className="d-flex gap-2">
                      <Button
                        variant="outline-secondary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          dispatchEdit({ type: "OPEN", target: col });
                        }}
                      >
                        Editar
                      </Button>
                      <Button
                        variant="outline-danger"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteConfirm.open(col);
                        }}
                        disabled={deleteConfirm.deleting}
                      >
                        Eliminar
                      </Button>
                    </div>
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
        show={deleteConfirm.target !== null}
        title="Eliminar colección"
        message={`¿Estás seguro de que quieres eliminar "${deleteConfirm.target?.name}"? Esta acción eliminará todos sus documentos y entidades.`}
        onConfirm={deleteConfirm.handleConfirm}
        onCancel={deleteConfirm.cancel}
        loading={deleteConfirm.deleting}
      />

      <ConfirmModal
        show={bulk.showBulkConfirm}
        title="Eliminar colecciones seleccionadas"
        message={`¿Eliminar ${bulk.selectedIds.size} colección${bulk.selectedIds.size !== 1 ? "es" : ""}? Se eliminarán todos sus documentos y entidades.`}
        onConfirm={handleBulkDelete}
        onCancel={() => dispatchBulk({ type: "CLOSE_CONFIRM" })}
        loading={bulk.bulkDeleting}
      />

      <Modal
        show={!!edit.target}
        onHide={() => dispatchEdit({ type: "CLOSE" })}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>Editar colección</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSaveEdit}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Nombre *</Form.Label>
              <Form.Control
                type="text"
                value={edit.name}
                onChange={(e) =>
                  dispatchEdit({ type: "SET_NAME", value: e.target.value })
                }
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Descripción</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={edit.description}
                onChange={(e) =>
                  dispatchEdit({
                    type: "SET_DESCRIPTION",
                    value: e.target.value,
                  })
                }
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button
              variant="secondary"
              onClick={() => dispatchEdit({ type: "CLOSE" })}
              disabled={edit.editing}
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={edit.editing || !edit.name.trim()}
            >
              {edit.editing ? "Guardando..." : "Guardar"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      <Modal
        show={create.show}
        onHide={() => dispatchCreate({ type: "CLOSE" })}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>Nueva colección</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleCreate}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Nombre *</Form.Label>
              <Form.Control
                type="text"
                value={create.name}
                onChange={(e) =>
                  dispatchCreate({ type: "SET_NAME", value: e.target.value })
                }
                placeholder="Nombre de la colección"
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Descripción</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={create.description}
                onChange={(e) =>
                  dispatchCreate({
                    type: "SET_DESCRIPTION",
                    value: e.target.value,
                  })
                }
                placeholder="Descripción opcional"
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button
              variant="secondary"
              onClick={() => dispatchCreate({ type: "CLOSE" })}
              disabled={create.creating}
            >
              Cancelar
            </Button>
            <Button
              variant="warning"
              type="submit"
              disabled={create.creating || !create.name.trim()}
            >
              {create.creating ? "Creando..." : "Crear"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </div>
  );
}
