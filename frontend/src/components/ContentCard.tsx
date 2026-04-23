import { useState } from "react";
import type { FormEvent } from "react";
import { Alert, Badge, Button, Card, Form, Modal, Spinner } from "react-bootstrap";
import { confirmContent, discardContent, deleteContent, updateContent } from "../api/contents";
import ConfirmModal from "./ConfirmModal";
import MarkdownContent from "./MarkdownContent";
import type { EntityContent } from "../types";
import { CATEGORY_LABELS } from "../utils/constants";
import { formatDate } from "../utils/formatters";
import { getErrorMessage } from "../utils/errors";

interface ContentCardProps {
  content: EntityContent;
  collectionId: string;
  entityId: string;
  onAction: () => void;
}

export default function ContentCard({ content, collectionId, entityId, onAction }: ContentCardProps) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [showEdit, setShowEdit] = useState(false);
  const [editText, setEditText] = useState(content.content);
  const [saving, setSaving] = useState(false);

  const [showDiscard, setShowDiscard] = useState(false);
  const [showDelete, setShowDelete] = useState(false);

  async function handleConfirm() {
    setBusy(true);
    setError(null);
    try {
      await confirmContent(collectionId, entityId, content.id);
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
      await updateContent(collectionId, entityId, content.id, { content: editText });
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
      await discardContent(collectionId, entityId, content.id);
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
      await deleteContent(collectionId, entityId, content.id);
      setShowDelete(false);
      onAction();
    } catch (e) {
      setError(getErrorMessage(e, "Error al eliminar"));
      setShowDelete(false);
    } finally {
      setBusy(false);
    }
  }

  const isPending = content.status === "pending";
  const isConfirmed = content.status === "confirmed";

  return (
    <>
      <Card className="mb-3">
        <Card.Header className="d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center gap-2">
            <Badge bg="dark">
              {CATEGORY_LABELS[content.category]}
            </Badge>
            <small className="text-muted">{formatDate(content.created_at)}</small>
          </div>
          <div>
            {content.status === "pending" && <Badge bg="warning" text="dark">Borrador</Badge>}
            {content.status === "confirmed" && <Badge bg="success">Confirmado</Badge>}
            {content.status === "discarded" && <Badge bg="secondary">Descartado</Badge>}
          </div>
        </Card.Header>
        <Card.Body>
          {error && (
            <Alert variant="danger" onClose={() => setError(null)} dismissible className="py-2">
              {error}
            </Alert>
          )}
          <MarkdownContent>{content.content}</MarkdownContent>
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
                onClick={() => { setEditText(content.content); setShowEdit(true); }}
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
              {content.confirmed_at && (
                <small className="text-muted">Confirmado el {formatDate(content.confirmed_at, true)}</small>
              )}
              <div className="d-flex gap-2">
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={() => { setEditText(content.content); setShowEdit(true); }}
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
          <Modal.Title>Editar contenido</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSaveEdit}>
          <Modal.Body>
            <Form.Control
              as="textarea"
              rows={10}
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              required
            />
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowEdit(false)} disabled={saving}>
              Cancelar
            </Button>
            <Button variant="warning" type="submit" disabled={saving || !editText.trim()}>
              {saving ? "Guardando..." : "Guardar"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      <ConfirmModal
        show={showDiscard}
        title="Descartar contenido"
        message="¿Descartar este contenido? El texto no se perderá pero no podrás confirmarlo."
        onConfirm={handleDiscard}
        onCancel={() => setShowDiscard(false)}
        variant="warning"
      />

      <ConfirmModal
        show={showDelete}
        title="Eliminar contenido"
        message="¿Eliminar este contenido permanentemente? Desaparecerá del listado."
        onConfirm={handleDelete}
        onCancel={() => setShowDelete(false)}
        variant="danger"
      />
    </>
  );
}