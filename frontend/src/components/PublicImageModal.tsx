import { useCallback } from "react";
import { Modal, Button } from "react-bootstrap";
import { Link } from "react-router-dom";
import { formatDate } from "../utils/formatters";
import { ENTITY_TYPE_LABELS } from "../utils/constants";
import SafeImage from "./SafeImage";
import { resolveImageUrl } from "../utils/media";

interface Props {
  show: boolean;
  onHide: () => void;
  imageUrl: string | null;
  storagePath: string | null;
  seed: number;
  autoPrompt: string;
  finalPrompt: string;
  entityName: string;
  entityType: string;
  ownerUsername: string;
  ownerDisplayName: string | null;
  createdAt: string;
}

export default function PublicImageModal({
  show,
  onHide,
  imageUrl,
  storagePath,
  seed,
  autoPrompt,
  finalPrompt,
  entityName,
  entityType,
  ownerUsername,
  createdAt,
}: Props) {
  // imageUrl tiene prioridad (URL completa de S3/Floci devuelta por el backend).
  // Para imágenes antiguas con image_url null, el backend aplica el fallback
  // build_storage_url. El segundo término es fallback solo para dev local.
  const resolvedUrl = resolveImageUrl(imageUrl, storagePath);

  const handleDownload = useCallback(async () => {
    const fetchUrl = resolveImageUrl(imageUrl, storagePath);
    if (!fetchUrl) return;
    const response = await fetch(fetchUrl);
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = `${entityName.replace(/\s+/g, "_")}_seed${seed}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(blobUrl);
  }, [imageUrl, storagePath, entityName, seed]);

  return (
    <Modal show={show} onHide={onHide} size="xl" centered>
      <Modal.Header closeButton>
        <div className="d-flex flex-column gap-1">
          <Modal.Title
            style={{ fontFamily: "var(--lm-font-head)", fontSize: "1.1rem" }}
          >
            {entityName}
          </Modal.Title>
          <div style={{ fontSize: "0.78rem" }}>
            <span className="text-muted me-1">
              {ENTITY_TYPE_LABELS[
                entityType as keyof typeof ENTITY_TYPE_LABELS
              ] ?? entityType}
              {" · "}
            </span>
            <Link
              to={`/users/${ownerUsername}`}
              onClick={onHide}
              style={{ color: "var(--lm-accent)", textDecoration: "none" }}
            >
              @{ownerUsername}
            </Link>
          </div>
        </div>
      </Modal.Header>
      <Modal.Body>
        <div className="text-center">
          {resolvedUrl ? (
            <SafeImage
              src={resolvedUrl}
              alt={`${entityName} seed ${seed}`}
              className="img-fluid rounded"
              style={{
                maxWidth: "100%",
                maxHeight: "60vh",
                objectFit: "contain",
              }}
            />
          ) : (
            <div
              style={{
                height: 300,
                background: "var(--lm-surface)",
                borderRadius: 8,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--lm-muted)",
              }}
            >
              Imagen no disponible
            </div>
          )}

          <div className="mt-4 text-start">
            <table className="table table-sm table-borderless">
              <tbody>
                <tr>
                  <td className="text-muted" style={{ width: 130 }}>
                    <strong>Seed:</strong>
                  </td>
                  <td>
                    <small className="text-muted">{seed}</small>
                  </td>
                </tr>
                <tr>
                  <td className="text-muted">
                    <strong>Creada:</strong>
                  </td>
                  <td>
                    <small className="text-muted">
                      {formatDate(createdAt)}
                    </small>
                  </td>
                </tr>
                <tr>
                  <td className="text-muted">
                    <strong>Prompt (auto):</strong>
                  </td>
                  <td>
                    <small className="text-muted">{autoPrompt || "—"}</small>
                  </td>
                </tr>
                <tr>
                  <td className="text-muted">
                    <strong>Prompt final:</strong>
                  </td>
                  <td>
                    <small className="text-muted">{finalPrompt}</small>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </Modal.Body>
      <Modal.Footer className="d-flex justify-content-end gap-2">
        <Button
          variant="primary"
          size="sm"
          onClick={handleDownload}
          disabled={!resolvedUrl}
        >
          Descargar imagen
        </Button>
        <Button variant="secondary" size="sm" onClick={onHide}>
          Cerrar
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
