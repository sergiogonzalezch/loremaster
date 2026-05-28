import { useCallback, useEffect, useReducer, useState } from "react";
import type { FormEvent, Reducer } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Badge,
  Button,
  Card,
  Form,
  Modal,
  Table,
} from "react-bootstrap";
import {
  getEntities,
  createEntity,
  deleteEntity,
  bulkDeleteEntities,
} from "../../api/entities";
import { OrderSelect, PageSizeSelect } from "../../components/FilterBar";
import LoadingSpinner from "../../components/LoadingSpinner";
import ConfirmModal from "../../components/ConfirmModal";
import PaginationControls from "../../components/PaginationControls";
import { useDeleteConfirm } from "../../hooks/useDeleteConfirm";
import type { Entity, CreateEntityRequest } from "../../types";
import type { EntityType } from "../../utils/enums";
import { formatDate } from "../../utils/formatters";
import { parseApiError } from "../../utils/errors";
import { ENTITY_TYPE_BADGE, ENTITY_TYPE_LABELS } from "../../utils/constants";

interface Props {
  collectionId: string;
}

// ── Reducers ─────────────────────────────────────────────────────────────────

type FiltersState = {
  nameFilter: string;
  typeFilter: "" | EntityType;
  order: "asc" | "desc";
  page: number;
  pageSize: number;
  totalPages: number;
};

type FiltersAction =
  | { type: "SET_NAME"; value: string }
  | { type: "SET_TYPE"; value: "" | EntityType }
  | { type: "SET_ORDER"; value: "asc" | "desc" }
  | { type: "SET_PAGE"; value: number }
  | { type: "SET_PAGE_SIZE"; value: number }
  | { type: "SET_TOTAL_PAGES"; value: number };

const filtersReducer: Reducer<FiltersState, FiltersAction> = (
  state,
  action,
) => {
  switch (action.type) {
    case "SET_NAME":
      return { ...state, nameFilter: action.value, page: 1 };
    case "SET_TYPE":
      return { ...state, typeFilter: action.value, page: 1 };
    case "SET_ORDER":
      return { ...state, order: action.value, page: 1 };
    case "SET_PAGE":
      return { ...state, page: action.value };
    case "SET_PAGE_SIZE":
      return { ...state, pageSize: action.value, page: 1 };
    case "SET_TOTAL_PAGES":
      return { ...state, totalPages: action.value };
  }
};

type BulkState = {
  selectedIds: Set<string>;
  bulkDeleting: boolean;
  showBulkConfirm: boolean;
};

type BulkAction =
  | { type: "TOGGLE_ONE"; id: string }
  | { type: "SET_ALL"; ids: string[] }
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
    case "SET_ALL":
      return { ...state, selectedIds: new Set(action.ids) };
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
        ...state,
        bulkDeleting: false,
        selectedIds: new Set(),
        showBulkConfirm: false,
      };
  }
};

type CreateState = {
  show: boolean;
  form: CreateEntityRequest;
  creating: boolean;
};

type CreateAction =
  | { type: "OPEN" }
  | { type: "CLOSE" }
  | { type: "FIELD"; patch: Partial<CreateEntityRequest> }
  | { type: "SUBMIT_START" }
  | { type: "SUBMIT_DONE" };

const initialForm: CreateEntityRequest = {
  type: "character",
  name: "",
  description: "",
};

const createReducer: Reducer<CreateState, CreateAction> = (state, action) => {
  switch (action.type) {
    case "OPEN":
      return { ...state, show: true };
    case "CLOSE":
      return { show: false, form: initialForm, creating: false };
    case "FIELD":
      return { ...state, form: { ...state.form, ...action.patch } };
    case "SUBMIT_START":
      return { ...state, creating: true };
    case "SUBMIT_DONE":
      return { show: false, form: initialForm, creating: false };
  }
};

// ── Componente ────────────────────────────────────────────────────────────────

/**
 * Pestaña de entidades dentro del detalle de una colección.
 */
export default function EntitiesTab({ collectionId }: Props) {
  const navigate = useNavigate();
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);

  const [filters, dispatchFilters] = useReducer(filtersReducer, {
    nameFilter: "",
    typeFilter: "",
    order: "desc",
    page: 1,
    pageSize: 10,
    totalPages: 0,
  });
  const { nameFilter, typeFilter, order, page, pageSize, totalPages } = filters;

  const [bulk, dispatchBulk] = useReducer(bulkReducer, {
    selectedIds: new Set<string>(),
    bulkDeleting: false,
    showBulkConfirm: false,
  });

  const [create, dispatchCreate] = useReducer(createReducer, {
    show: false,
    form: initialForm,
    creating: false,
  });

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
      dispatchFilters({ type: "SET_TOTAL_PAGES", value: res.meta.total_pages });
    } catch (e) {
      setError(parseApiError(e, "Error al cargar entidades"));
    } finally {
      setLoading(false);
    }
  }, [collectionId, nameFilter, order, page, pageSize, typeFilter]);

  const deleteConfirm = useDeleteConfirm<Entity>({
    onDelete: async (entity) => {
      await deleteEntity(collectionId, entity.id);
      await fetchEntities();
    },
    onError: (e) => setError(parseApiError(e, "Error al eliminar entidad")),
  });

  useEffect(() => {
    fetchEntities();
  }, [fetchEntities]);

  const allOnPageSelected =
    entities.length > 0 && entities.every((e) => bulk.selectedIds.has(e.id));

  function toggleSelectAll() {
    if (allOnPageSelected) {
      dispatchBulk({ type: "CLEAR" });
    } else {
      dispatchBulk({ type: "SET_ALL", ids: entities.map((e) => e.id) });
    }
  }

  async function handleBulkDelete() {
    dispatchBulk({ type: "DELETE_START" });
    try {
      await bulkDeleteEntities(collectionId, [...bulk.selectedIds]);
      dispatchBulk({ type: "DELETE_DONE" });
      await fetchEntities();
    } catch (e) {
      setError(
        parseApiError(e, "Error al eliminar las entidades seleccionadas"),
      );
      dispatchBulk({ type: "DELETE_DONE" });
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    dispatchCreate({ type: "SUBMIT_START" });
    try {
      await createEntity(collectionId, create.form);
      dispatchCreate({ type: "SUBMIT_DONE" });
      await fetchEntities();
    } catch (err) {
      setError(parseApiError(err, "Error al crear entidad"));
      dispatchCreate({ type: "SUBMIT_DONE" });
    }
  }

  return (
    <>
      <Card className="mb-3">
        <Card.Body>
          <div className="d-flex gap-3 flex-wrap align-items-end">
            <Form.Group style={{ minWidth: 220 }}>
              <Form.Label>Buscar entidad</Form.Label>
              <Form.Control
                value={nameFilter}
                onChange={(e) =>
                  dispatchFilters({ type: "SET_NAME", value: e.target.value })
                }
                placeholder="Ej. Aria"
              />
            </Form.Group>
            <Form.Group style={{ minWidth: 180 }}>
              <Form.Label>Tipo</Form.Label>
              <Form.Select
                value={typeFilter}
                onChange={(e) =>
                  dispatchFilters({
                    type: "SET_TYPE",
                    value: e.target.value as "" | EntityType,
                  })
                }
              >
                <option value="">Todos</option>
                {(Object.keys(ENTITY_TYPE_LABELS) as EntityType[]).map((t) => (
                  <option key={t} value={t}>
                    {ENTITY_TYPE_LABELS[t]}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            <OrderSelect
              value={order}
              onChange={(o) => dispatchFilters({ type: "SET_ORDER", value: o })}
            />
            <PageSizeSelect
              value={pageSize}
              onChange={(size) =>
                dispatchFilters({ type: "SET_PAGE_SIZE", value: size })
              }
            />
          </div>
        </Card.Body>
      </Card>

      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          {bulk.selectedIds.size > 0 && (
            <Button
              variant="danger"
              size="sm"
              onClick={() => dispatchBulk({ type: "OPEN_CONFIRM" })}
              disabled={bulk.bulkDeleting}
            >
              Eliminar seleccionadas ({bulk.selectedIds.size})
            </Button>
          )}
        </div>
        <Button
          variant="warning"
          onClick={() => dispatchCreate({ type: "OPEN" })}
        >
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
              <th style={{ width: 40 }}>
                <Form.Check
                  type="checkbox"
                  checked={allOnPageSelected}
                  onChange={toggleSelectAll}
                />
              </th>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Descripción</th>
              <th>Creada</th>
              <th aria-label="Acciones"></th>
            </tr>
          </thead>
          <tbody>
            {entities.map((entity) => (
              <tr key={entity.id}>
                <td>
                  <Form.Check
                    type="checkbox"
                    checked={bulk.selectedIds.has(entity.id)}
                    onChange={() =>
                      dispatchBulk({ type: "TOGGLE_ONE", id: entity.id })
                    }
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="btn btn-link p-0 text-primary fw-semibold"
                    style={{ cursor: "pointer", textDecoration: "none" }}
                    onClick={() =>
                      navigate(
                        `/collections/${collectionId}/entities/${entity.id}`,
                      )
                    }
                  >
                    {entity.name}
                  </button>
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
                  <div>{formatDate(entity.created_at)}</div>
                  {entity.updated_at && (
                    <small className="text-muted">
                      Editada: {formatDate(entity.updated_at)}
                    </small>
                  )}
                </td>
                <td>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => deleteConfirm.open(entity)}
                    disabled={deleteConfirm.deleting}
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
        show={deleteConfirm.target !== null}
        title="Eliminar entidad"
        message={`¿Eliminar la entidad "${deleteConfirm.target?.name}"? También se eliminarán todos sus drafts.`}
        onConfirm={deleteConfirm.handleConfirm}
        onCancel={deleteConfirm.cancel}
        loading={deleteConfirm.deleting}
      />

      <ConfirmModal
        show={bulk.showBulkConfirm}
        title="Eliminar entidades seleccionadas"
        message={`¿Eliminar ${bulk.selectedIds.size} entidad${bulk.selectedIds.size !== 1 ? "es" : ""}? También se eliminarán todos sus drafts.`}
        onConfirm={handleBulkDelete}
        onCancel={() => dispatchBulk({ type: "CLOSE_CONFIRM" })}
        loading={bulk.bulkDeleting}
      />

      <Modal
        show={create.show}
        onHide={() => dispatchCreate({ type: "CLOSE" })}
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>Nueva entidad</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleCreate}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Tipo *</Form.Label>
              <Form.Select
                value={create.form.type}
                onChange={(e) =>
                  dispatchCreate({
                    type: "FIELD",
                    patch: { type: e.target.value as EntityType },
                  })
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
                value={create.form.name}
                onChange={(e) =>
                  dispatchCreate({
                    type: "FIELD",
                    patch: { name: e.target.value },
                  })
                }
                placeholder="Nombre de la entidad"
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Descripción</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={create.form.description}
                onChange={(e) =>
                  dispatchCreate({
                    type: "FIELD",
                    patch: { description: e.target.value },
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
              disabled={create.creating || !create.form.name.trim()}
            >
              {create.creating ? "Creando..." : "Crear"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
      <PaginationControls
        page={page}
        totalPages={totalPages}
        onPageChange={(p) => dispatchFilters({ type: "SET_PAGE", value: p })}
      />
    </>
  );
}
