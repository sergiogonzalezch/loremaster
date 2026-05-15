import { useEffect, useState, useCallback } from "react";
import { Alert, Button, Card, Badge, Modal } from "react-bootstrap";
import LoadingSpinner from "./LoadingSpinner";
import SafeImage from "./SafeImage";
import { listImageGenerations, deleteImage, shareImage } from "../api/images";
import type { ImageGenerationItem, ImageRecord } from "../types";
import { formatDate } from "../utils/formatters";
import { CATEGORY_LABELS } from "../utils/constants";

const MEDIA_BASE = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"
).replace("/api/v1", "");

interface Props {
  collectionId: string;
  entityId: string;
  refreshTrigger: number;
}

export default function ImageGallery({
  collectionId,
  entityId,
  refreshTrigger,
}: Props) {
  const [generations, setGenerations] = useState<ImageGenerationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedGeneration, setSelectedGeneration] =
    useState<ImageGenerationItem | null>(null);
  const [selectedImage, setSelectedImage] = useState<ImageRecord | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [sharing, setSharing] = useState(false);

  const fetchGenerations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listImageGenerations(collectionId, entityId);
      setGenerations(data.generations);
    } catch {
      setError("Error al cargar las imágenes generadas");
    } finally {
      setLoading(false);
    }
  }, [collectionId, entityId]);

  useEffect(() => {
    const controller = new AbortController();
    fetchGenerations().catch(() => {});
    return () => controller.abort();
  }, [fetchGenerations, refreshTrigger]);

  const getImageUrl = (img: ImageRecord): string => {
    if (img.storage_path) {
      return `${MEDIA_BASE}/media/${img.storage_path}`;
    }
    return img.image_url || "";
  };

  const handleDownload = useCallback(async (img: ImageRecord) => {
    const fetchUrl = img.storage_path
      ? `/media/${img.storage_path}`
      : img.image_url || "";
    if (!fetchUrl) return;
    const response = await fetch(fetchUrl);
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = `${img.id}.${img.extension || "png"}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(blobUrl);
  }, []);

  const handleShareImage = useCallback(
    async (generationId: string, imageId: string, currentShared: boolean) => {
      setSharing(true);
      try {
        const updated = await shareImage(
          collectionId,
          entityId,
          generationId,
          imageId,
          { shared: !currentShared },
        );
        setSelectedImage(updated);
        await fetchGenerations();
      } catch {
        setError("Error al cambiar la visibilidad de la imagen");
      } finally {
        setSharing(false);
      }
    },
    [collectionId, entityId, fetchGenerations],
  );

  const handleDeleteImage = useCallback(
    async (generationId: string, imageId: string) => {
      setDeleting(true);
      try {
        await deleteImage(collectionId, entityId, generationId, imageId);
        await fetchGenerations();
        if (selectedGeneration) {
          const updated = await listImageGenerations(collectionId, entityId);
          const gen = updated.generations.find((g) => g.id === generationId);
          if (gen) {
            setSelectedGeneration(gen);
          } else {
            setSelectedGeneration(null);
          }
        }
      } catch {
        setError("Error al eliminar la imagen");
      } finally {
        setDeleting(false);
      }
    },
    [collectionId, entityId, fetchGenerations, selectedGeneration],
  );

  if (loading) {
    return <LoadingSpinner text="Cargando galería..." />;
  }

  if (error) {
    return <Alert variant="danger">{error}</Alert>;
  }

  if (generations.length === 0) {
    return (
      <div className="lm-empty">
        <span className="lm-empty-glyph">🖼️</span>
        <p>No hay imágenes generadas todavía.</p>
        <p>Selecciona un contenido confirmado y genera tu primera imagen.</p>
      </div>
    );
  }

  return (
    <>
      <p className="lm-section-title">Galería de imágenes</p>
      <p className="text-muted small mb-3">
        Historial de todas las imágenes generadas para esta entidad. Persiste
        entre sesiones.
      </p>
      <div className="d-flex flex-column gap-3">
        {generations.map((gen) => (
          <Card key={gen.id} className="lm-image-generation-card">
            <Card.Header className="d-flex justify-content-between align-items-center bg-light">
              <div>
                <Badge bg="secondary" className="me-2">
                  {gen.batch_size} imagenes
                </Badge>
                <Badge
                  bg={
                    gen.category === "extended_description"
                      ? "info"
                      : "secondary"
                  }
                >
                  {CATEGORY_LABELS[
                    gen.category as keyof typeof CATEGORY_LABELS
                  ] || gen.category}
                </Badge>
                <small className="text-muted ms-2">
                  {formatDate(gen.created_at)}
                </small>
              </div>
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => setSelectedGeneration(gen)}
              >
                Ver detalles
              </Button>
            </Card.Header>
            <Card.Body className="p-2">
              <div className="d-flex gap-2 overflow-auto py-1">
                {gen.images.map((img) => (
                  <div
                    key={img.id}
                    role="button"
                    tabIndex={0}
                    className="lm-image-thumbnail"
                    style={{ minWidth: 120, cursor: "pointer" }}
                    onClick={() => {
                      setSelectedGeneration(gen);
                      setSelectedImage(img);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        setSelectedGeneration(gen);
                        setSelectedImage(img);
                      }
                    }}
                  >
                    <SafeImage
                      src={getImageUrl(img)}
                      alt={`Imagen ${img.seed}`}
                      className="img-fluid rounded"
                      style={{ width: 120, height: 120, objectFit: "cover" }}
                    />
                    <small className="d-block text-center text-muted mt-1">
                      Seed: {img.seed}
                    </small>
                  </div>
                ))}
              </div>
            </Card.Body>
          </Card>
        ))}
      </div>

      <Modal
        show={selectedImage !== null}
        onHide={() => setSelectedImage(null)}
        size="xl"
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>Imagen generadata</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedImage && selectedGeneration && (
            <div className="text-center">
              <SafeImage
                src={getImageUrl(selectedImage)}
                alt={`Imagen seed ${selectedImage.seed}`}
                className="img-fluid rounded"
                style={{
                  maxWidth: "100%",
                  maxHeight: "60vh",
                  objectFit: "contain",
                }}
              />
              <div className="mt-4 text-start">
                <h5>Metadata</h5>
                <table className="table table-sm table-borderless">
                  <tbody>
                    <tr>
                      <td className="text-muted" style={{ width: 150 }}>
                        <strong>Seed:</strong>
                      </td>
                      <td>{selectedImage.seed}</td>
                    </tr>
                    <tr>
                      <td className="text-muted">
                        <strong>Backend:</strong>
                      </td>
                      <td>{selectedGeneration.backend}</td>
                    </tr>
                    <tr>
                      <td className="text-muted">
                        <strong>Resolución:</strong>
                      </td>
                      <td>
                        {selectedGeneration.width} x {selectedGeneration.height}
                      </td>
                    </tr>
                    <tr>
                      <td className="text-muted">
                        <strong>Creada:</strong>
                      </td>
                      <td>{formatDate(selectedImage.created_at)}</td>
                    </tr>
                    <tr>
                      <td className="text-muted">
                        <strong>Prompt (auto):</strong>
                      </td>
                      <td>
                        <small className="text-muted">
                          {selectedGeneration.auto_prompt || "-"}
                        </small>
                      </td>
                    </tr>
                    <tr>
                      <td className="text-muted">
                        <strong>Prompt final:</strong>
                      </td>
                      <td>
                        <small className="text-muted">
                          {selectedGeneration.final_prompt}
                        </small>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer className="d-flex justify-content-between">
          <div className="d-flex gap-2">
            {selectedImage && (
              <>
                <Button
                  variant={
                    selectedImage.is_shared ? "success" : "outline-secondary"
                  }
                  size="sm"
                  onClick={() =>
                    handleShareImage(
                      selectedGeneration!.id,
                      selectedImage!.id,
                      selectedImage!.is_shared,
                    )
                  }
                  disabled={sharing || deleting}
                >
                  {selectedImage.is_shared ? "✦ Compartida" : "Compartir"}
                </Button>
                <Button
                  variant="outline-danger"
                  size="sm"
                  onClick={() =>
                    handleDeleteImage(selectedGeneration!.id, selectedImage!.id)
                  }
                  disabled={deleting || sharing}
                >
                  Eliminar
                </Button>
              </>
            )}
          </div>
          <div className="d-flex gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() => selectedImage && handleDownload(selectedImage)}
            >
              Descargar imagen
            </Button>
            <Button variant="secondary" onClick={() => setSelectedImage(null)}>
              Cerrar
            </Button>
          </div>
        </Modal.Footer>
      </Modal>

      <Modal
        show={selectedGeneration !== null && selectedImage === null}
        onHide={() => setSelectedGeneration(null)}
        size="lg"
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>Detalles de generación</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedGeneration && (
            <>
              <div className="mb-3">
                <strong>Prompt original:</strong>
                <p className="text-muted small mb-1">
                  {selectedGeneration.auto_prompt}
                </p>
                <strong>Prompt final:</strong>
                <p className="text-muted small mb-0">
                  {selectedGeneration.final_prompt}
                </p>
              </div>
              <div className="mb-3">
                <Badge bg="secondary" className="me-2">
                  {selectedGeneration.batch_size} imágenes
                </Badge>
                <Badge bg="info">
                  {CATEGORY_LABELS[
                    selectedGeneration.category as keyof typeof CATEGORY_LABELS
                  ] || selectedGeneration.category}
                </Badge>
                <small className="text-muted ms-2">
                  {formatDate(selectedGeneration.created_at)}
                </small>
              </div>
              <div className="d-flex flex-wrap gap-3">
                {selectedGeneration.images.map((img) => (
                  <div
                    key={img.id}
                    role="button"
                    tabIndex={0}
                    className="text-center"
                    style={{ cursor: "pointer" }}
                    onClick={() => setSelectedImage(img)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ")
                        setSelectedImage(img);
                    }}
                  >
                    <SafeImage
                      src={getImageUrl(img)}
                      alt={`Imagen ${img.seed}`}
                      className="img-fluid rounded"
                      style={{
                        width: selectedGeneration.width / 2,
                        height: selectedGeneration.height / 2,
                        objectFit: "contain",
                      }}
                    />
                    <div className="mt-1">
                      <small className="text-muted d-block">
                        Seed: {img.seed}
                      </small>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button
            variant="secondary"
            onClick={() => setSelectedGeneration(null)}
          >
            Cerrar
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}
