import { useEffect, useState, useCallback } from "react";
import { Offcanvas, Nav, Button, Form, Alert, Spinner, Badge } from "react-bootstrap";
import { buildPrompt, generateImages, listImageGenerations } from "../api/images";
import { getContents } from "../api/contents";
import type { EntityContent, ImageGenerationItem } from "../types";
import { CATEGORY_LABELS } from "../utils/constants";
import { getErrorMessage } from "../utils/errors";
import { formatDate } from "../utils/formatters";

interface Props {
  collectionId: string;
  entityId: string;
  show: boolean;
  onHide: () => void;
  onGenerated: () => void;
}

export default function ImagePanel({
  collectionId,
  entityId,
  show,
  onHide,
  onGenerated,
}: Props) {
  const [activeTab, setActiveTab] = useState<"generar" | "historial">("generar");
  const [confirmedContent, setConfirmedContent] = useState<EntityContent | null>(null);
  const [promptData, setPromptData] = useState<{
    auto_prompt: string;
    prompt_source: string;
    prompt_source_label: string;
    token_count: number;
    truncated: boolean;
  } | null>(null);
  const [finalPrompt, setFinalPrompt] = useState("");
  const [batchSize, setBatchSize] = useState(4);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generations, setGenerations] = useState<ImageGenerationItem[]>([]);
  const [loadingGenerations, setLoadingGenerations] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setLoadingGenerations(true);
    try {
      const [contentsRes, generationsRes] = await Promise.all([
        getContents(collectionId, entityId, { status: "confirmed", page_size: 50 }),
        listImageGenerations(collectionId, entityId),
      ]);
      const contents = contentsRes.data ?? [];
      if (contents.length > 0) {
        setConfirmedContent(contents[0]);
      }
      setGenerations(generationsRes.generations);
    } catch (e) {
      setError("Error al cargar datos");
    } finally {
      setLoading(false);
      setLoadingGenerations(false);
    }
  }, [collectionId, entityId]);

  useEffect(() => {
    if (show) {
      fetchData();
    }
  }, [show, fetchData]);

  const handleBuildPrompt = useCallback(async () => {
    if (!confirmedContent) return;
    setBuilding(true);
    setError(null);
    try {
      const data = await buildPrompt(collectionId, entityId, confirmedContent.id);
      setPromptData(data);
      setFinalPrompt(data.auto_prompt);
    } catch (e) {
      setError(getErrorMessage(e, "Error al construir prompt"));
    } finally {
      setBuilding(false);
    }
  }, [collectionId, entityId, confirmedContent]);

  const handleGenerate = useCallback(async () => {
    if (!finalPrompt.trim() || !confirmedContent) return;
    setGenerating(true);
    setError(null);
    try {
      await generateImages(collectionId, entityId, {
        content_id: confirmedContent.id,
        final_prompt: finalPrompt.trim(),
        batch_size: batchSize,
      });
      setPromptData(null);
      setFinalPrompt("");
      onGenerated();
      const genRes = await listImageGenerations(collectionId, entityId);
      setGenerations(genRes.generations);
      setActiveTab("historial");
    } catch (e) {
      setError(getErrorMessage(e, "Error al generar imágenes"));
    } finally {
      setGenerating(false);
    }
  }, [collectionId, entityId, finalPrompt, batchSize, confirmedContent, onGenerated]);

  const renderGenerarTab = () => {
    if (loading) {
      return (
        <div className="text-center py-4">
          <Spinner animation="border" size="sm" className="me-2" />
          Cargando...
        </div>
      );
    }

    if (!confirmedContent) {
      return (
        <div className="lm-empty">
          <span className="lm-empty-glyph">🎨</span>
          <p>No hay contenidos confirmados.</p>
          <p className="small text-muted">
            Confirma un contenido en la sección de contenidos primero.
          </p>
        </div>
      );
    }

    return (
      <div>
        <div className="mb-3 p-3 border rounded bg-light">
          <div className="d-flex justify-content-between align-items-start mb-2">
            <Badge bg="secondary">
              {CATEGORY_LABELS[confirmedContent.category] || confirmedContent.category}
            </Badge>
            <small className="text-muted">{formatDate(confirmedContent.confirmed_at!)}</small>
          </div>
          <p className="mb-0 small" style={{ maxHeight: 80, overflow: "hidden" }}>
            {confirmedContent.content}
          </p>
        </div>

        <Button
          variant="outline-primary"
          onClick={handleBuildPrompt}
          disabled={!!promptData || building || generating}
          className="mb-3 w-100"
        >
          {building ? (
            <>
              <Spinner animation="border" size="sm" className="me-1" />
              Construyendo prompt...
            </>
          ) : promptData ? (
            "Prompt listo"
          ) : (
            "Construir prompt automático"
          )}
        </Button>

        {promptData && (
          <>
            <Alert variant="info" className="mb-3">
              <small className="text-muted">
                {promptData.prompt_source_label} | Tokens: {promptData.token_count}
                {promptData.truncated && " (truncado)"}
              </small>
            </Alert>

            <Form.Group className="mb-3">
              <Form.Control
                as="textarea"
                rows={4}
                value={finalPrompt}
                onChange={(e) => setFinalPrompt(e.target.value)}
                disabled={generating}
                placeholder="Edita el prompt si deseas..."
              />
            </Form.Group>

            <div className="d-flex align-items-center gap-3 mb-3">
              <Form.Label className="mb-0">Imágenes:</Form.Label>
              <Form.Select
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
                disabled={generating}
                style={{ width: "auto" }}
              >
                {[1, 2, 3, 4].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </Form.Select>
            </div>

            <Button
              variant="primary"
              onClick={handleGenerate}
              disabled={generating || !finalPrompt.trim()}
              className="w-100"
            >
              {generating ? (
                <>
                  <Spinner animation="border" size="sm" className="me-1" />
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
      </div>
    );
  };

  const renderHistorialTab = () => {
    if (loadingGenerations) {
      return (
        <div className="text-center py-4">
          <Spinner animation="border" size="sm" className="me-2" />
          Cargando...
        </div>
      );
    }

    if (generations.length === 0) {
      return (
        <div className="lm-empty">
          <span className="lm-empty-glyph">🖼️</span>
          <p>No hay imágenes generadas.</p>
        </div>
      );
    }

    return (
      <div className="d-flex flex-column gap-3">
        {generations.map((gen) => (
          <div key={gen.id} className="border rounded p-2">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <div>
                <Badge bg="secondary" className="me-2">
                  {gen.batch_size}
                </Badge>
                <Badge bg="info">
                  {CATEGORY_LABELS[gen.category as keyof typeof CATEGORY_LABELS] || gen.category}
                </Badge>
                <small className="text-muted ms-2">{formatDate(gen.created_at)}</small>
              </div>
            </div>
            <div className="d-flex gap-2 overflow-auto">
              {gen.images.map((img) => (
                <div key={img.id} style={{ minWidth: 80 }}>
                  <img
                    src={img.storage_path ? `http://localhost:8000/media/${img.storage_path}` : img.storage_path || ""}
                    alt=""
                    className="img-fluid rounded"
                    style={{ width: 80, height: 80, objectFit: "cover" }}
                  />
                  <small className="d-block text-center text-muted mt-1">{img.seed}</small>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <Offcanvas show={show} onHide={onHide} placement="end" style={{ width: 380 }}>
      <Offcanvas.Header closeButton>
        <Offcanvas.Title>Imágenes</Offcanvas.Title>
      </Offcanvas.Header>
      <Offcanvas.Body>
        <Nav variant="tabs" className="mb-3">
          <Nav.Item>
            <Nav.Link
              active={activeTab === "generar"}
              onClick={() => setActiveTab("generar")}
              style={{ cursor: "pointer" }}
            >
              Generar
            </Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link
              active={activeTab === "historial"}
              onClick={() => setActiveTab("historial")}
              style={{ cursor: "pointer" }}
            >
              Historial
            </Nav.Link>
          </Nav.Item>
        </Nav>

        {activeTab === "generar" ? renderGenerarTab() : renderHistorialTab()}
      </Offcanvas.Body>
    </Offcanvas>
  );
}