import { useState } from "react";
import type { FormEvent } from "react";
import {
  Accordion,
  Alert,
  Badge,
  Button,
  Card,
  Form,
  Modal,
  Spinner,
} from "react-bootstrap";
import {
  confirmContent,
  discardContent,
  deleteContent,
  updateContent,
} from "../api/contents";
import ConfirmModal from "./ConfirmModal";
import { useDeleteConfirm } from "../hooks/useDeleteConfirm";
import { useNavigate } from "react-router-dom";
import MarkdownContent from "./MarkdownContent";
import type { EntityContent } from "../types";
import { CATEGORY_LABELS } from "../utils/constants";
import { formatDate } from "../utils/formatters";
import { parseApiError } from "../utils/errors";

interface ContentCardProps {
  content: EntityContent;
  collectionId: string;
  entityId: string;
  onAction: () => void;
  onOptimisticUpdate?: (
    id: string,
    patch: Partial<EntityContent> | null,
  ) => void;
}

export default function ContentCard({
  content,
  collectionId,
  entityId,
  onAction,
  onOptimisticUpdate,
}: ContentCardProps) {
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  const [showEdit, setShowEdit] = useState(false);
  const [editText, setEditText] = useState(content.content);
  const [saving, setSaving] = useState(false);

  const [showDiscard, setShowDiscard] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const navigate = useNavigate();

  const deleteConfirm = useDeleteConfirm<EntityContent>({
    onDelete: async (c) => {
      setError(null);
      onOptimisticUpdate?.(c.id, null);
      await deleteContent(collectionId, entityId, c.id);
      onAction();
    },
    onError: (e) => {
      onOptimisticUpdate?.(content.id, content);
      setError(parseApiError(e, "Error al eliminar"));
    },
  });

  async function handleConfirm() {
    setBusy(true);
    setError(null);
    onOptimisticUpdate?.(content.id, { status: "confirmed" });
    try {
      await confirmContent(collectionId, entityId, content.id);
      onAction();
    } catch (e) {
      onOptimisticUpdate?.(content.id, content);
      setError(parseApiError(e, "Error al confirmar"));
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveEdit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    onOptimisticUpdate?.(content.id, {
      content: editText,
      updated_at: new Date().toISOString(),
    });
    try {
      await updateContent(collectionId, entityId, content.id, {
        content: editText,
      });
      setShowEdit(false);
      onAction();
    } catch (e) {
      onOptimisticUpdate?.(content.id, content);
      setError(parseApiError(e, "Error al guardar"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDiscard() {
    setBusy(true);
    setError(null);
    onOptimisticUpdate?.(content.id, { status: "discarded" });
    try {
      await discardContent(collectionId, entityId, content.id);
      setShowDiscard(false);
      onAction();
    } catch (e) {
      onOptimisticUpdate?.(content.id, content);
      setError(parseApiError(e, "Error al descartar"));
      setShowDiscard(false);
    } finally {
      setBusy(false);
    }
  }

  const isPending = content.status === "pending";
  const isConfirmed = content.status === "confirmed";

  return (
    <>
      <Card className="mb-3">
        <Card.Header className="p-0">
          <Accordion activeKey={isExpanded ? "content" : undefined}>
            <Accordion.Item
              eventKey="content"
              className="lm-content-accordion-item"
            >
              <Accordion.Header onClick={() => setIsExpanded((open) => !open)}>
                <div className="d-flex justify-content-between align-items-center w-100 me-2">
                  <div className="d-flex flex-column gap-1">
                    <div className="d-flex align-items-center gap-2">
                      <Badge bg="dark">
                        {CATEGORY_LABELS[content.category]}
                      </Badge>
                      <small className="text-muted">
                        {formatDate(content.created_at)}
                      </small>
                    </div>
                    <small
                      className="text-muted fst-italic"
                      style={{
                        maxWidth: 420,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      "{content.query}"
                    </small>
                  </div>
                  <div className="d-flex align-items-center gap-2">
                    <Badge
                      style={{
                        background: "var(--lm-accent-glow)",
                        color: "var(--lm-accent)",
                        border: "1px solid var(--lm-border-accent)",
                        fontSize: "0.65rem",
                      }}
                    >
                      {content.sources_count} fuentes
                    </Badge>
                    {content.token_count > 0 && (
                      <Badge
                        style={{
                          background: "var(--lm-accent-glow)",
                          color: "var(--lm-accent)",
                          border: "1px solid var(--lm-border-accent)",
                          fontSize: "0.65rem",
                        }}
                      >
                        ~{content.token_count} tokens
                      </Badge>
                    )}
                    {content.was_edited && (
                      <Badge
                        style={{
                          background: "rgba(201,162,39,0.1)",
                          color: "#c9a227",
                          border: "1px solid rgba(201,162,39,0.3)",
                          fontSize: "0.6rem",
                        }}
                        title="Editado por el usuario. Output original del LLM preservado para auditoría."
                      >
                        ✎ editado
                      </Badge>
                    )}
                    {content.status === "pending" && (
                      <Badge bg="warning" text="dark">
                        Borrador
                      </Badge>
                    )}
                    {content.status === "confirmed" && (
                      <Badge bg="success">Confirmado</Badge>
                    )}
                    {content.status === "discarded" && (
                      <Badge bg="secondary">Descartado</Badge>
                    )}
                    <small className="text-muted">
                      {isExpanded ? "Ocultar" : "Ver contenido"}
                    </small>
                  </div>
                </div>
              </Accordion.Header>
              <Accordion.Body>
                {error && (
                  <Alert
                    variant={error.variant}
                    onClose={() => setError(null)}
                    dismissible
                    className="py-2"
                  >
                    {error.text}
                  </Alert>
                )}
                <MarkdownContent>{content.content}</MarkdownContent>
                {content.was_edited && content.raw_content && (
                  <details className="mt-3">
                    <summary
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--lm-text-muted)",
                        cursor: "pointer",
                        userSelect: "none",
                      }}
                    >
                      Ver output original del LLM
                    </summary>
                    <div
                      className="mt-2 p-2"
                      style={{
                        borderLeft: "2px solid rgba(201,162,39,0.3)",
                        fontSize: "0.88rem",
                        color: "var(--lm-text-muted)",
                        fontStyle: "italic",
                      }}
                    >
                      <MarkdownContent>{content.raw_content}</MarkdownContent>
                    </div>
                  </details>
                )}
              </Accordion.Body>
            </Accordion.Item>
          </Accordion>
        </Card.Header>
        <Card.Footer>
          {content.updated_at && (
            <small className="text-muted d-block mb-2">
              Editado: {formatDate(content.updated_at, true)}
            </small>
          )}
          {isPending ? (
            <div className="d-flex gap-2">
              <Button
                variant="success"
                size="sm"
                onClick={handleConfirm}
                disabled={busy || deleteConfirm.deleting}
              >
                {busy ? <Spinner animation="border" size="sm" /> : "Confirmar"}
              </Button>
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => {
                  setEditText(content.content);
                  setShowEdit(true);
                }}
                disabled={busy || deleteConfirm.deleting}
              >
                Editar
              </Button>

              <Button
                variant="outline-warning"
                size="sm"
                onClick={() => setShowDiscard(true)}
                disabled={busy || deleteConfirm.deleting}
              >
                Descartar
              </Button>
              <Button
                variant="outline-danger"
                size="sm"
                onClick={() => deleteConfirm.open(content)}
                disabled={busy || deleteConfirm.deleting}
              >
                Eliminar
              </Button>
            </div>
          ) : content.status === "discarded" ? (
            <div className="d-flex justify-content-end">
              <Button
                variant="outline-danger"
                size="sm"
                onClick={() => deleteConfirm.open(content)}
                disabled={busy || deleteConfirm.deleting}
              >
                Eliminar
              </Button>
            </div>
          ) : isConfirmed ? (
            <div className="d-flex align-items-center justify-content-between">
              {content.confirmed_at && (
                <small className="text-muted">
                  Confirmado el {formatDate(content.confirmed_at, true)}
                </small>
              )}
              <div className="d-flex gap-2">
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={() => {
                    setEditText(content.content);
                    setShowEdit(true);
                  }}
                  disabled={busy || deleteConfirm.deleting}
                >
                  Editar
                </Button>
                <Button
                  variant="outline-danger"
                  size="sm"
                  onClick={() => deleteConfirm.open(content)}
                  disabled={busy || deleteConfirm.deleting}
                >
                  Eliminar
                </Button>
              </div>
            </div>
          ) : null}
        </Card.Footer>
      </Card>

      <Modal
        show={showEdit}
        onHide={() => setShowEdit(false)}
        centered
        size="lg"
      >
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
              disabled={saving || !editText.trim()}
            >
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
        show={deleteConfirm.target !== null}
        title="Eliminar contenido"
        message="¿Eliminar este contenido permanentemente? Desaparecerá del listado."
        onConfirm={deleteConfirm.handleConfirm}
        onCancel={deleteConfirm.cancel}
        variant="danger"
        loading={deleteConfirm.deleting}
      />
    </>
  );
}
