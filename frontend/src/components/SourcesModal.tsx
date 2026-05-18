import { useEffect, useState } from "react";
import { Accordion, Badge, Modal, Spinner } from "react-bootstrap";
import { getContentChunks } from "../api/contents";
import type { ContentChunkItem } from "../types";

interface SourcesModalProps {
  show: boolean;
  onHide: () => void;
  collectionId: string;
  entityId: string;
  contentId: string;
}

export default function SourcesModal({
  show,
  onHide,
  collectionId,
  entityId,
  contentId,
}: SourcesModalProps) {
  const [chunks, setChunks] = useState<ContentChunkItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!show) return;
    const controller = new AbortController();
    setLoading(true);
    getContentChunks(collectionId, entityId, contentId, controller.signal)
      .then((res) => {
        setChunks(res.chunks);
      })
      .catch(() => {
        setChunks([]);
      })
      .finally(() => {
        setLoading(false);
      });
    return () => controller.abort();
  }, [show, collectionId, entityId, contentId]);

  const grouped = chunks.reduce<Record<string, ContentChunkItem[]>>((acc, chunk) => {
    const key = chunk.filename ?? "Documento eliminado";
    (acc[key] ??= []).push(chunk);
    return acc;
  }, {});

  return (
    <Modal show={show} onHide={onHide} centered size="lg">
      <Modal.Header closeButton>
        <Modal.Title className="fs-6">Fuentes RAG</Modal.Title>
      </Modal.Header>
      <Modal.Body className="py-2">
        {loading ? (
          <div className="text-center py-3">
            <Spinner animation="border" size="sm" />
          </div>
        ) : chunks.length === 0 ? (
          <p className="text-muted small mb-0 py-1">Sin información de fuentes.</p>
        ) : (
          <Accordion flush>
            {Object.entries(grouped).map(([filename, items]) => (
              <Accordion.Item key={filename} eventKey={filename}>
                <Accordion.Header>
                  <span className="small">
                    📄 {filename}
                    <Badge bg="secondary" className="ms-2">
                      {items.length}
                    </Badge>
                  </span>
                </Accordion.Header>
                <Accordion.Body className="p-0">
                  {items.map((chunk) => (
                    <div
                      key={chunk.id}
                      className="px-3 py-2 small"
                      style={{
                        color: "var(--lm-text-muted)",
                        borderBottom: "1px solid var(--lm-border)",
                      }}
                    >
                      {chunk.score !== null && (
                        <span
                          className="badge me-2"
                          style={{
                            fontSize: "0.7rem",
                            background: "var(--lm-accent-glow)",
                            color: "var(--lm-accent)",
                            border: "1px solid var(--lm-border-accent)",
                          }}
                        >
                          {(chunk.score * 100).toFixed(0)}%
                        </span>
                      )}
                      {chunk.chunk_text}
                    </div>
                  ))}
                </Accordion.Body>
              </Accordion.Item>
            ))}
          </Accordion>
        )}
      </Modal.Body>
    </Modal>
  );
}
