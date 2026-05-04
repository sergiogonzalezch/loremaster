import { useEffect, useState, useCallback } from "react";
import { Alert, Button, Card, Badge, Modal } from "react-bootstrap";
import LoadingSpinner from "./LoadingSpinner";
import { listImageGenerations, deleteImage } from "../api/images";
import type { ImageGenerationItem } from "../types";
import { formatDate } from "../utils/formatters";
import { CATEGORY_LABELS } from "../utils/constants";

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
  const [deleting, setDeleting] = useState(false);

  const fetchGenerations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listImageGenerations(collectionId, entityId);
      setGenerations(data.generations);
    } catch (e) {
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
      } catch (e) {
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
                    className="lm-image-thumbnail"
                    style={{ minWidth: 120 }}
                  >
                    <img
                      src={
                        img.storage_path
                          ? `http://localhost:8000/media/${img.storage_path}`
                          : img.storage_path || ""
                      }
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
        show={selectedGeneration !== null}
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
                  <div key={img.id} className="text-center">
                    <img
                      src={
                        img.storage_path
                          ? `http://localhost:8000/media/${img.storage_path}`
                          : img.storage_path || ""
                      }
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
                      <Button
                        variant="outline-danger"
                        size="sm"
                        onClick={() =>
                          handleDeleteImage(selectedGeneration.id, img.id)
                        }
                        disabled={deleting}
                      >
                        Eliminar
                      </Button>
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
