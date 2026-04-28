import { useState } from "react";
import type { FormEvent } from "react";
import { Button, Form, Modal } from "react-bootstrap";
import { updateEntity } from "../api";
import type { Entity, UpdateEntityRequest } from "../types";
import type { EntityType } from "../utils/enums";
import { getErrorMessage } from "../utils/errors";
import { ENTITY_TYPE_LABELS } from "../utils/constants";

interface Props {
  show: boolean;
  entity: Entity;
  collectionId: string;
  entityId: string;
  onClose: () => void;
  onSaved: (updated: Entity) => void;
  onError: (message: string) => void;
}

export default function EntityEditForm({
  show,
  entity,
  collectionId,
  entityId,
  onClose,
  onSaved,
  onError,
}: Props) {
  const [editForm, setEditForm] = useState<UpdateEntityRequest>({
    type: entity.type,
    name: entity.name,
    description: entity.description,
  });
  const [saving, setSaving] = useState(false);

  function handleShow() {
    setEditForm({
      type: entity.type,
      name: entity.name,
      description: entity.description,
    });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await updateEntity(collectionId, entityId, editForm);
      onSaved(updated);
    } catch (err) {
      onError(getErrorMessage(err, "Error al actualizar entidad"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal show={show} onHide={onClose} onShow={handleShow} centered>
      <Modal.Header closeButton>
        <Modal.Title>Editar entidad</Modal.Title>
      </Modal.Header>
      <Form onSubmit={handleSubmit}>
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
          <Button variant="secondary" onClick={onClose} disabled={saving}>
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
  );
}
