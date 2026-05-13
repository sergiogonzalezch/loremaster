import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
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
import { getEntities, createEntity, deleteEntity, bulkDeleteEntities } from "../../api";
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

/**
 * Pestaña de entidades dentro del detalle de una colección.
 *
 * Lista las entidades de la colección con filtros por nombre y tipo,
 * permite crear nuevas entidades y navegar al detalle de cada una.
 *
 * @param collectionId - Identificador de la colección.
 */
export default function EntitiesTab({ collectionId }: Props) {
  const navigate = useNavigate();
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);
  const deleteConfirm = useDeleteConfirm<Entity>({
    onDelete: async (entity) => {
      await deleteEntity(collectionId, entity.id);
      await fetchEntities();
    },
    onError: (e) => setError(parseApiError(e, "Error al eliminar entidad")),
  });
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [showBulkConfirm, setShowBulkConfirm] = useState(false);
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

  /**
   * Carga la lista de entidades aplicando filtros y paginación.
   */
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

  const allOnPageSelected =
    entities.length > 0 && entities.every((e) => selectedIds.has(e.id));

  function toggleSelectAll() {
    if (allOnPageSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(entities.map((e) => e.id)));
    }
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleBulkDelete() {
    setBulkDeleting(true);
    try {
      await bulkDeleteEntities(collectionId, [...selectedIds]);
      setSelectedIds(new Set());
      setShowBulkConfirm(false);
      await fetchEntities();
    } catch (e) {
      setError(parseApiError(e, "Error al eliminar las entidades seleccionadas"));
      setShowBulkConfirm(false);
    } finally {
      setBulkDeleting(false);
    }
  }

  /**
   * Crea una nueva entidad en la colección con los datos del formulario.
   *
   * @param e - Evento del formulario de creación.
   */
  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await createEntity(collectionId, form);
      setShowCreate(false);
      setForm({ type: "character", name: "", description: "" });
      await fetchEntities();
    } catch (err) {
      setError(parseApiError(err, "Error al crear entidad"));
    } finally {
      setCreating(false);
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
                onChange={(e) => {
                  setNameFilter(e.target.value);
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
            <OrderSelect
              value={order}
              onChange={(o) => {
                setOrder(o);
                setPage(1);
              }}
            />
            <PageSizeSelect
              value={pageSize}
              onChange={(size) => {
                setPageSize(size);
                setPage(1);
              }}
            />
          </div>
        </Card.Body>
      </Card>

      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          {selectedIds.size > 0 && (
            <Button
              variant="danger"
              size="sm"
              onClick={() => setShowBulkConfirm(true)}
              disabled={bulkDeleting}
            >
              Eliminar seleccionadas ({selectedIds.size})
            </Button>
          )}
        </div>
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
              <th></th>
            </tr>
          </thead>
          <tbody>
            {entities.map((entity) => (
              <tr key={entity.id}>
                <td>
                  <Form.Check
                    type="checkbox"
                    checked={selectedIds.has(entity.id)}
                    onChange={() => toggleSelect(entity.id)}
                  />
                </td>
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
        show={showBulkConfirm}
        title="Eliminar entidades seleccionadas"
        message={`¿Eliminar ${selectedIds.size} entidad${selectedIds.size !== 1 ? "es" : ""}? También se eliminarán todos sus drafts.`}
        onConfirm={handleBulkDelete}
        onCancel={() => setShowBulkConfirm(false)}
        loading={bulkDeleting}
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
                  setForm((f) => ({ ...f, name: e.target.value }))
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
                  setForm((f) => ({ ...f, description: e.target.value }))
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
      <PaginationControls
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
      />
    </>
  );
}
