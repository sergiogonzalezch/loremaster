import { useEffect, useState, useCallback } from "react";
import {
  Alert,
  Button,
  Card,
  Form,
  Spinner,
} from "react-bootstrap";
import { buildPrompt, generateImages } from "../api/images";
import { getContents } from "../api/contents";
import type { EntityContent } from "../types";
import { CATEGORY_LABELS } from "../utils/constants";
import { getErrorMessage } from "../utils/errors";

interface Props {
  collectionId: string;
  entityId: string;
  onGenerated: () => void;
}

export default function ImageGenerator({
  collectionId,
  entityId,
  onGenerated,
}: Props) {
  const [confirmedContents, setConfirmedContents] = useState<
    EntityContent[]
  >([]);
  const [selectedContentId, setSelectedContentId] = useState("");
  const [promptData, setPromptData] = useState<{
    auto_prompt: string;
    prompt_source: string;
    prompt_source_label: string;
    prompt_strategy: string;
    token_count: number;
    truncated: boolean;
  } | null>(null);
  const [finalPrompt, setFinalPrompt] = useState("");
  const [batchSize, setBatchSize] = useState(4);
  const [loading, setLoading] = useState(false);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getContents(collectionId, entityId, {
      status: "confirmed",
      page_size: 50,
    })
      .then((data) => setConfirmedContents(data.data ?? []))
      .catch(() => {});
  }, [collectionId, entityId]);

  const handleBuildPrompt = useCallback(async () => {
    if (!selectedContentId) return;
    setBuilding(true);
    setError(null);
    try {
      const data = await buildPrompt(
        collectionId,
        entityId,
        selectedContentId,
      );
      setPromptData(data);
      setFinalPrompt(data.auto_prompt);
    } catch (e) {
      setError(getErrorMessage(e, "Error al construir prompt"));
    } finally {
      setBuilding(false);
    }
  }, [collectionId, entityId, selectedContentId]);

  const handleGenerate = useCallback(async () => {
    if (!finalPrompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await generateImages(collectionId, entityId, {
        content_id: selectedContentId,
        final_prompt: finalPrompt.trim(),
        batch_size: batchSize,
      });
      setPromptData(null);
      setSelectedContentId("");
      setFinalPrompt("");
      onGenerated();
    } catch (e) {
      setError(getErrorMessage(e, "Error al generar imágenes"));
    } finally {
      setLoading(false);
    }
  }, [
    collectionId,
    entityId,
    selectedContentId,
    finalPrompt,
    batchSize,
    onGenerated,
  ]);

  if (confirmedContents.length === 0) {
    return (
      <>
        <p className="lm-section-title">Generar imágenes</p>
        <div className="lm-empty">
          <span className="lm-empty-glyph">🎨</span>
          <p>No hay contenidos confirmados para generar imágenes.</p>
          <p>
            Confirma un contenido en la sección de contenidos primero.
          </p>
        </div>
      </>
    );
  }

  return (
    <>
      <p className="lm-section-title">Generar imágenes</p>
      <Card className="mb-3">
        <Card.Body>
          <Form.Group className="mb-3">
            <Form.Label>Contenido confirmado</Form.Label>
            <Form.Select
              value={selectedContentId}
              onChange={(e) => {
                setSelectedContentId(e.target.value);
                setPromptData(null);
                setFinalPrompt("");
              }}
              disabled={building || loading}
            >
              <option value="">Selecciona un contenido...</option>
              {confirmedContents.map((content) => (
                <option key={content.id} value={content.id}>
                  {CATEGORY_LABELS[content.category]} -{" "}
                  {content.content.substring(0, 50)}...
                </option>
              ))}
            </Form.Select>
          </Form.Group>

          <Button
            variant="outline-primary"
            onClick={handleBuildPrompt}
            disabled={!selectedContentId || building || loading}
            className="mb-3"
          >
            {building ? (
              <>
                <Spinner
                  animation="border"
                  size="sm"
                  className="me-1"
                />
                Construyendo prompt...
              </>
            ) : (
              "Construir prompt automático"
            )}
          </Button>

          {promptData && (
            <>
              <Alert variant="info" className="mb-3">
                <div className="d-flex justify-content-between align-items-start">
                  <div>
                    <strong>Prompt generado</strong>
                    <br />
                    <small className="text-muted">
                      Fuente: {promptData.prompt_source_label} | Estrategia:{" "}
                      {promptData.prompt_strategy} | Tokens:{" "}
                      {promptData.token_count}
                      {promptData.truncated && " (truncado)"}
                    </small>
                  </div>
                </div>
              </Alert>

              <Form.Group className="mb-3">
                <Form.Label>Prompt (puedes editarlo)</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={4}
                  value={finalPrompt}
                  onChange={(e) => setFinalPrompt(e.target.value)}
                  disabled={loading}
                  placeholder="Edita el prompt si deseas..."
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label>Número de imágenes (1-4)</Form.Label>
                <Form.Select
                  value={batchSize}
                  onChange={(e) => setBatchSize(Number(e.target.value))}
                  disabled={loading}
                  style={{ maxWidth: 100 }}
                >
                  {[1, 2, 3, 4].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>

              <Button
                variant="primary"
                onClick={handleGenerate}
                disabled={loading || !finalPrompt.trim()}
              >
                {loading ? (
                  <>
                    <Spinner
                      animation="border"
                      size="sm"
                      className="me-1"
                    />
                    Generando...
                  </>
                ) : (
                  `Generar ${batchSize} imagen${batchSize > 1 ? "es" : ""}`
                )}
              </Button>
            </>
          )}

          {error && (
            <Alert variant="danger" className="mt-3" dismissible onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
        </Card.Body>
      </Card>
    </>
  );
}