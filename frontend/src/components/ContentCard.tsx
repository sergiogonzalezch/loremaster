import { useReducer, useState } from "react";
import type { FormEvent, Reducer } from "react";
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
  shareContent,
} from "../api/contents";
import ConfirmModal from "./ConfirmModal";
import SourcesModal from "./SourcesModal";
import { useDeleteConfirm } from "../hooks/useDeleteConfirm";
import MarkdownContent from "./MarkdownContent";
import type { EntityContent } from "../types";
import { CATEGORY_LABELS } from "../utils/constants";
import { formatDate } from "../utils/formatters";
import { parseApiError } from "../utils/errors";

// Estado UI agrupado: modales y expansión cambian de forma independiente
// pero comparten el mismo dominio de "controles visuales del card".
type UIState = {
  expanded: boolean;
  showDiscard: boolean;
  showSources: boolean;
};

type UIAction =
  | { type: "TOGGLE_EXPAND" }
  | { type: "OPEN_DISCARD" }
  | { type: "CLOSE_DISCARD" }
  | { type: "OPEN_SOURCES" }
  | { type: "CLOSE_SOURCES" };

const uiReducer: Reducer<UIState, UIAction> = (state, action) => {
  switch (action.type) {
    case "TOGGLE_EXPAND":
      return { ...state, expanded: !state.expanded };
    case "OPEN_DISCARD":
      return { ...state, showDiscard: true };
    case "CLOSE_DISCARD":
      return { ...state, showDiscard: false };
    case "OPEN_SOURCES":
      return { ...state, showSources: true };
    case "CLOSE_SOURCES":
      return { ...state, showSources: false };
  }
};

type EditState = { show: boolean; text: string; saving: boolean };

type EditAction =
  | { type: "OPEN"; text: string }
  | { type: "CLOSE" }
  | { type: "SET_TEXT"; value: string }
  | { type: "SAVE_START" }
  | { type: "SAVE_DONE" };

const editReducer: Reducer<EditState, EditAction> = (state, action) => {
  switch (action.type) {
    case "OPEN":
      return { show: true, text: action.text, saving: false };
    case "CLOSE":
      return { show: false, text: "", saving: false };
    case "SET_TEXT":
      return { ...state, text: action.value };
    case "SAVE_START":
      return { ...state, saving: true };
    case "SAVE_DONE":
      return { show: false, text: "", saving: false };
  }
};

interface ContentCardProps {
  content: EntityContent;
  collectionId: string;
  entityId: string;
  onAction: () => void;
  onOptimisticUpdate?: (
    id: string,
    patch: Partial<EntityContent> | null,
  ) => void;
  onOpenImagePanel?: (content: EntityContent) => void;
}

export default function ContentCard({
  content,
  collectionId,
  entityId,
  onAction,
  onOptimisticUpdate,
  onOpenImagePanel,
}: ContentCardProps) {
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [edit, dispatchEdit] = useReducer(editReducer, {
    show: false,
    text: "",
    saving: false,
  });
  const [ui, dispatchUI] = useReducer(uiReducer, {
    expanded: false,
    showDiscard: false,
    showSources: false,
  });

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
    dispatchEdit({ type: "SAVE_START" });
    onOptimisticUpdate?.(content.id, {
      content: edit.text,
      updated_at: new Date().toISOString(),
    });
    try {
      await updateContent(collectionId, entityId, content.id, {
        content: edit.text,
      });
      dispatchEdit({ type: "SAVE_DONE" });
      onAction();
    } catch (e) {
      onOptimisticUpdate?.(content.id, content);
      setError(parseApiError(e, "Error al guardar"));
      dispatchEdit({ type: "SAVE_DONE" });
    }
  }

  async function handleShare() {
    setBusy(true);
    setError(null);
    const next = !content.is_shared;
    onOptimisticUpdate?.(content.id, { is_shared: next });
    try {
      await shareContent(collectionId, entityId, content.id, { shared: next });
      onAction();
    } catch (e) {
      onOptimisticUpdate?.(content.id, content);
      setError(parseApiError(e, "Error al cambiar visibilidad"));
    } finally {
      setBusy(false);
    }
  }

  async function handleDiscard() {
    setBusy(true);
    setError(null);
    onOptimisticUpdate?.(content.id, { status: "discarded" });
    try {
      await discardContent(collectionId, entityId, content.id);
      dispatchUI({ type: "CLOSE_DISCARD" });
      onAction();
    } catch (e) {
      onOptimisticUpdate?.(content.id, content);
      setError(parseApiError(e, "Error al descartar"));
      dispatchUI({ type: "CLOSE_DISCARD" });
    } finally {
      setBusy(false);
    }
  }

  const isPending = content.status === "pending";
  const isConfirmed = content.status === "confirmed";
  const supportsImage = ["extended_description", "backstory", "scene"].includes(
    content.category,
  );

  return (
    <>
      <Card className="mb-3">
        <Card.Header className="p-0">
          <Accordion activeKey={ui.expanded ? "content" : undefined}>
            <Accordion.Item
              eventKey="content"
              className="lm-content-accordion-item"
            >
              <Accordion.Header onClick={() => dispatchUI({ type: "TOGGLE_EXPAND" })}>
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
                        fontSize: "0.75rem",
                      }}
                    >
                      {content.sources_count} fuentes
                    </Badge>
                    {content.model_used && (
                      <Badge
                        style={{
                          background: "transparent",
                          color: "var(--lm-text-muted, #888)",
                          border: "1px solid var(--lm-border, #444)",
                          fontSize: "0.75rem",
                        }}
                        title={`Generado con ${content.model_used}`}
                      >
                        {content.model_used}
                      </Badge>
                    )}
                    {content.token_count > 0 && (
                      <Badge
                        style={{
                          background: "var(--lm-accent-glow)",
                          color: "var(--lm-accent)",
                          border: "1px solid var(--lm-border-accent)",
                          fontSize: "0.75rem",
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
                          fontSize: "0.75rem",
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
                      {ui.expanded ? "Ocultar" : "Ver contenido"}
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
                onClick={() =>
                  dispatchEdit({ type: "OPEN", text: content.content })
                }
                disabled={busy || deleteConfirm.deleting}
              >
                Editar
              </Button>

              <Button
                variant="outline-warning"
                size="sm"
                onClick={() => dispatchUI({ type: "OPEN_DISCARD" })}
                disabled={busy || deleteConfirm.deleting}
              >
                Descartar
              </Button>
              {content.sources_count > 0 && (
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={() => dispatchUI({ type: "OPEN_SOURCES" })}
                  disabled={busy || deleteConfirm.deleting}
                >
                  Fuentes
                </Button>
              )}
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
            <div className="d-flex justify-content-end gap-2">
              {content.sources_count > 0 && (
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={() => dispatchUI({ type: "OPEN_SOURCES" })}
                  disabled={busy || deleteConfirm.deleting}
                >
                  Fuentes
                </Button>
              )}
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
                  onClick={() =>
                    dispatchEdit({ type: "OPEN", text: content.content })
                  }
                  disabled={busy || deleteConfirm.deleting}
                >
                  Editar
                </Button>
                <Button
                  variant={content.is_shared ? "success" : "outline-secondary"}
                  size="sm"
                  onClick={handleShare}
                  disabled={busy || deleteConfirm.deleting}
                  title={
                    content.is_shared
                      ? "Este contenido es visible en el feed público"
                      : "Compartir en el feed público"
                  }
                >
                  {content.is_shared ? "✦ Compartido" : "Compartir"}
                </Button>
                {onOpenImagePanel && supportsImage && (
                  <Button
                    variant="outline-primary"
                    size="sm"
                    onClick={() => onOpenImagePanel(content)}
                    disabled={busy || deleteConfirm.deleting}
                  >
                    Imagen
                  </Button>
                )}
                {content.sources_count > 0 && (
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    onClick={() => dispatchUI({ type: "OPEN_SOURCES" })}
                    disabled={busy || deleteConfirm.deleting}
                  >
                    Fuentes
                  </Button>
                )}
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
        show={edit.show}
        onHide={() => dispatchEdit({ type: "CLOSE" })}
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
              value={edit.text}
              onChange={(e) =>
                dispatchEdit({ type: "SET_TEXT", value: e.target.value })
              }
              required
            />
          </Modal.Body>
          <Modal.Footer>
            <Button
              variant="secondary"
              onClick={() => dispatchEdit({ type: "CLOSE" })}
              disabled={edit.saving}
            >
              Cancelar
            </Button>
            <Button
              variant="warning"
              type="submit"
              disabled={edit.saving || !edit.text.trim()}
            >
              {edit.saving ? "Guardando..." : "Guardar"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      <ConfirmModal
        show={ui.showDiscard}
        title="Descartar contenido"
        message="¿Descartar este contenido? El texto no se perderá pero no podrás confirmarlo."
        onConfirm={handleDiscard}
        onCancel={() => dispatchUI({ type: "CLOSE_DISCARD" })}
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

      {ui.showSources && (
        <SourcesModal
          show={ui.showSources}
          onHide={() => dispatchUI({ type: "CLOSE_SOURCES" })}
          collectionId={collectionId}
          entityId={content.entity_id}
          contentId={content.id}
        />
      )}
    </>
  );
}
