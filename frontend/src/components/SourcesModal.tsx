import { useEffect, useState } from "react";
import { ListGroup, Modal, Spinner } from "react-bootstrap";
import { getDocument } from "../api/documents";
import type { Document } from "../types";

interface SourcesModalProps {
  show: boolean;
  onHide: () => void;
  collectionId: string;
  sourceDocIds: string[];
}

type DocEntry = { id: string; doc: Document | null; missing: boolean };

export default function SourcesModal({
  show,
  onHide,
  collectionId,
  sourceDocIds,
}: SourcesModalProps) {
  const [entries, setEntries] = useState<DocEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!show || sourceDocIds.length === 0) return;

    setLoading(true);
    Promise.allSettled(sourceDocIds.map((id) => getDocument(collectionId, id))).then(
      (results) => {
        setEntries(
          sourceDocIds.map((id, i) => {
            const result = results[i];
            if (result.status === "fulfilled") return { id, doc: result.value, missing: false };
            return { id, doc: null, missing: true };
          }),
        );
        setLoading(false);
      },
    );
  }, [show, collectionId, sourceDocIds]);

  return (
    <Modal show={show} onHide={onHide} centered size="sm">
      <Modal.Header closeButton>
        <Modal.Title className="fs-6">Documentos fuente</Modal.Title>
      </Modal.Header>
      <Modal.Body className="py-2">
        {loading ? (
          <div className="text-center py-3">
            <Spinner animation="border" size="sm" />
          </div>
        ) : entries.length === 0 ? (
          <p className="text-muted small mb-0 py-1">Sin información de fuentes.</p>
        ) : (
          <ListGroup variant="flush">
            {entries.map(({ id, doc, missing }) => (
              <ListGroup.Item
                key={id}
                className="px-0 py-2 d-flex align-items-center gap-2"
              >
                <span
                  style={{ fontSize: "0.75rem", color: "var(--lm-text-muted)" }}
                >
                  📄
                </span>
                {missing ? (
                  <span className="text-muted small fst-italic">
                    Documento eliminado
                  </span>
                ) : (
                  <span className="small">{doc!.filename}</span>
                )}
              </ListGroup.Item>
            ))}
          </ListGroup>
        )}
      </Modal.Body>
    </Modal>
  );
}