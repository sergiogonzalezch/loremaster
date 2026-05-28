import { useState, useCallback, useReducer } from "react";
import {
  Offcanvas,
  Nav,
  Button,
  Form,
  Alert,
  Spinner,
  Badge,
  Modal,
} from "react-bootstrap";
import {
  buildPrompt,
  generateImages,
  listImageGenerations,
  deleteImage,
  shareImage,
} from "../api/images";
import type { EntityContent, ImageGenerationItem } from "../types";
import { CATEGORY_LABELS } from "../utils/constants";
import { getErrorMessage } from "../utils/errors";
import { formatDate } from "../utils/formatters";
import { resolveImageUrl, downloadImage } from "../utils/media";

interface Props {
  collectionId: string;
  entityId: string;
  show: boolean;
  onHide: () => void;
  onGenerated: () => void;
  initialContent?: EntityContent | null;
}

type ImageItem = ImageGenerationItem["images"][0];

// ── Reducers ─────────────────────────────────────────────────────────────────

type GenState = {
  promptData: { auto_prompt: string; token_count: number } | null;
  finalPrompt: string;
  batchSize: number;
  building: boolean;
  generating: boolean;
};

type GenAction =
  | { type: "BUILD_START" }
  | {
      type: "BUILD_SUCCESS";
      promptData: { auto_prompt: string; token_count: number };
    }
  | { type: "BUILD_ERROR" }
  | { type: "SET_FINAL_PROMPT"; value: string }
  | { type: "SET_BATCH_SIZE"; value: number }
  | { type: "GENERATE_START" }
  | { type: "GENERATE_DONE" }
  | { type: "REUSE_FROM_HISTORY"; finalPrompt: string; autoPrompt: string };

function genReducer(state: GenState, action: GenAction): GenState {
  switch (action.type) {
    case "BUILD_START":
      return { ...state, building: true };
    case "BUILD_SUCCESS":
      return {
        ...state,
        building: false,
        promptData: action.promptData,
        finalPrompt: action.promptData.auto_prompt,
      };
    case "BUILD_ERROR":
      return { ...state, building: false };
    case "SET_FINAL_PROMPT":
      return { ...state, finalPrompt: action.value };
    case "SET_BATCH_SIZE":
      return { ...state, batchSize: action.value };
    case "GENERATE_START":
      return { ...state, generating: true };
    case "GENERATE_DONE":
      return { ...state, generating: false };
    case "REUSE_FROM_HISTORY":
      return {
        ...state,
        finalPrompt: action.finalPrompt,
        promptData: {
          auto_prompt: action.autoPrompt,
          token_count: Math.ceil(action.finalPrompt.length / 4),
        },
      };
  }
}

type ModalState = {
  show: boolean;
  selectedImage: ImageItem | null;
  selectedGen: ImageGenerationItem | null;
  sharing: boolean;
};

type ModalAction =
  | { type: "OPEN"; image: ImageItem; gen: ImageGenerationItem }
  | { type: "CLOSE" }
  | { type: "SHARE_START" }
  | { type: "SHARE_DONE"; updatedImage: ImageItem }
  | { type: "SHARE_ERROR" };

function modalReducer(state: ModalState, action: ModalAction): ModalState {
  switch (action.type) {
    case "OPEN":
      return {
        show: true,
        selectedImage: action.image,
        selectedGen: action.gen,
        sharing: false,
      };
    case "CLOSE":
      return { ...state, show: false };
    case "SHARE_START":
      return { ...state, sharing: true };
    case "SHARE_DONE":
      return { ...state, sharing: false, selectedImage: action.updatedImage };
    case "SHARE_ERROR":
      return { ...state, sharing: false };
  }
}

// ── Sub-componente ────────────────────────────────────────────────────────────

function ImageGrid({
  gen,
  onDelete,
  onSelect,
}: {
  gen: ImageGenerationItem;
  onDelete: (generationId: string, imageId: string) => void;
  onSelect: (gen: ImageGenerationItem, img: ImageItem) => void;
}) {
  if (!gen) return null;
  const images = gen.images;
  const count = images.length;

  const getImageUrl = (img: ImageItem) =>
    resolveImageUrl(img.image_url, img.storage_path);

  const getGridClass = () => {
    switch (count) {
      case 1:
        return "grid-1";
      case 2:
        return "grid-2";
      case 3:
        return "grid-3";
      case 4:
        return "grid-4";
      default:
        return "grid-1";
    }
  };

  return (
    <div className={`image-grid ${getGridClass()}`}>
      {images.map((img) => {
        const url = getImageUrl(img);
        return (
          <div key={img.id} className="image-cell position-relative">
            {url ? (
              <button
                type="button"
                aria-label="Ver imagen"
                className="p-0 border-0 bg-transparent d-block"
                style={{ width: "100%", height: "100%", cursor: "pointer" }}
                onClick={() => onSelect(gen, img)}
              >
                <img
                  src={url}
                  alt=""
                  className="img-fluid rounded"
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              </button>
            ) : (
              <div className="image-placeholder">
                <span>Generando…</span>
              </div>
            )}
            <button
              type="button"
              aria-label="Eliminar imagen"
              className="image-delete-btn"
              onClick={() => onDelete(gen.id, img.id)}
              title="Eliminar"
            >
              ×
            </button>
            <small className="d-block text-center text-muted mt-1">
              {img.seed}
            </small>
          </div>
        );
      })}
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────

export default function ImagePanel({
  collectionId,
  entityId,
  show,
  onHide,
  onGenerated,
  initialContent,
}: Props) {
  const confirmedContent = initialContent ?? null;

  const [activeTab, setActiveTab] = useState<"generar" | "historial">(
    "generar",
  );
  const [error, setError] = useState<string | null>(null);
  const [generations, setGenerations] = useState<ImageGenerationItem[]>([]);
  const [loadingGenerations, setLoadingGenerations] = useState(false);
  const [seedBase, setSeedBase] = useState(
    () => Math.floor(Math.random() * 999983) + 1,
  );

  const [gen, dispatchGen] = useReducer(genReducer, {
    promptData: null,
    finalPrompt: "",
    batchSize: 4,
    building: false,
    generating: false,
  });

  const [imageModal, dispatchModal] = useReducer(modalReducer, {
    show: false,
    selectedImage: null,
    selectedGen: null,
    sharing: false,
  });

  const fetchData = useCallback(async () => {
    setLoadingGenerations(true);
    try {
      const res = await listImageGenerations(collectionId, entityId);
      setGenerations(res.generations);
    } catch {
      setError("Error al cargar historial");
    } finally {
      setLoadingGenerations(false);
    }
  }, [collectionId, entityId]);

  // Se invoca cuando el Offcanvas termina de abrirse — sin efecto reactivo
  const handleShow = useCallback(() => {
    void fetchData();
  }, [fetchData]);

  // Se invoca al cerrar — limpia error sin efecto
  const handleHide = useCallback(() => {
    setError(null);
    onHide();
  }, [onHide]);

  const handleDeleteImage = useCallback(
    async (generationId: string, imageId: string) => {
      try {
        await deleteImage(collectionId, entityId, generationId, imageId);
        dispatchModal({ type: "CLOSE" });
        await fetchData();
      } catch (e) {
        setError(getErrorMessage(e, "Error al eliminar imagen"));
      }
    },
    [collectionId, entityId, fetchData],
  );

  const handleSelectImage = useCallback(
    (g: ImageGenerationItem, img: ImageItem) => {
      dispatchModal({ type: "OPEN", image: img, gen: g });
    },
    [],
  );

  const randomizeSeedBase = useCallback(
    () => setSeedBase(Math.floor(Math.random() * 999983) + 1),
    [],
  );

  const handleRegenFromHistory = useCallback(
    (g: ImageGenerationItem) => {
      dispatchGen({
        type: "REUSE_FROM_HISTORY",
        finalPrompt: g.final_prompt,
        autoPrompt: g.auto_prompt,
      });
      setSeedBase(Math.floor(Math.random() * 999983) + 1);
      dispatchModal({ type: "CLOSE" });
      setActiveTab("generar");
    },
    [],
  );

  const handleShareImage = useCallback(
    async (g: ImageGenerationItem, img: ImageItem) => {
      dispatchModal({ type: "SHARE_START" });
      try {
        const updated = await shareImage(collectionId, entityId, g.id, img.id, {
          shared: !img.is_shared,
        });
        dispatchModal({ type: "SHARE_DONE", updatedImage: updated });
        await fetchData();
      } catch (e) {
        dispatchModal({ type: "SHARE_ERROR" });
        setError(getErrorMessage(e, "Error al cambiar la visibilidad"));
      }
    },
    [collectionId, entityId, fetchData],
  );

  const handleDownload = useCallback(async (img: ImageItem) => {
    const url = resolveImageUrl(img.image_url, img.storage_path);
    await downloadImage(url, `${img.id}.png`);
  }, []);

  const handleBuildPrompt = useCallback(async () => {
    if (!confirmedContent) return;
    dispatchGen({ type: "BUILD_START" });
    setError(null);
    try {
      const data = await buildPrompt(collectionId, entityId, confirmedContent.id);
      dispatchGen({ type: "BUILD_SUCCESS", promptData: data });
    } catch (e) {
      dispatchGen({ type: "BUILD_ERROR" });
      setError(getErrorMessage(e, "Error al construir prompt"));
    }
  }, [collectionId, entityId, confirmedContent]);

  const handleGenerate = useCallback(async () => {
    if (!gen.finalPrompt.trim() || !confirmedContent) return;
    dispatchGen({ type: "GENERATE_START" });
    setError(null);
    try {
      await generateImages(collectionId, entityId, {
        content_id: confirmedContent.id,
        auto_prompt: gen.promptData?.auto_prompt || gen.finalPrompt,
        final_prompt: gen.finalPrompt.trim(),
        batch_size: gen.batchSize,
        seed_base: seedBase,
      });
      onGenerated();
      const genRes = await listImageGenerations(collectionId, entityId);
      setGenerations(genRes.generations);
      setActiveTab("historial");
      setSeedBase(Math.floor(Math.random() * 999983) + 1);
    } catch (e) {
      setError(getErrorMessage(e, "Error al generar imágenes"));
    } finally {
      dispatchGen({ type: "GENERATE_DONE" });
    }
  }, [
    collectionId,
    entityId,
    gen.finalPrompt,
    gen.batchSize,
    gen.promptData,
    seedBase,
    confirmedContent,
    onGenerated,
  ]);

  const renderGenerarTab = () => {
    if (!confirmedContent) {
      return (
        <div className="lm-empty">
          <span className="lm-empty-glyph">🖼️</span>
          <p>No hay contenidos confirmados.</p>
          <p className="small text-muted">
            Confirma un contenido en la sección de contenidos primero.
          </p>
        </div>
      );
    }

    return (
      <div className="d-flex flex-column gap-3">
        <div className="lm-card p-3">
          <div className="d-flex justify-content-between align-items-start mb-2">
            <Badge bg="secondary">
              {CATEGORY_LABELS[confirmedContent.category] ||
                confirmedContent.category}
            </Badge>
            <small className="text-muted">
              {formatDate(confirmedContent.confirmed_at!)}
            </small>
          </div>
          <div
            className="text-muted small"
            style={{
              maxHeight: 100,
              overflow: "auto",
              whiteSpace: "pre-wrap",
              lineHeight: 1.5,
            }}
          >
            {confirmedContent.content}
          </div>
        </div>

        <div className="d-flex gap-2">
          <Button
            variant="outline-primary"
            onClick={handleBuildPrompt}
            disabled={!!gen.promptData || gen.building || gen.generating}
            className="flex-grow-1"
          >
            {gen.building ? (
              <>
                <Spinner animation="border" size="sm" className="me-1" />
                Construyendo…
              </>
            ) : gen.promptData ? (
              "Listo"
            ) : (
              "Crear prompt visual"
            )}
          </Button>
          {gen.promptData && (
            <Button
              variant="outline-secondary"
              onClick={handleBuildPrompt}
              disabled={gen.building || gen.generating}
              size="sm"
            >
              ↻ Nuevo auto-prompt
            </Button>
          )}
        </div>

        {gen.promptData && (
          <>
            <div className="text-muted small">
              {gen.promptData.token_count} tokens
            </div>

            <Form.Group>
              <Form.Label className="small text-muted mb-1">Prompt</Form.Label>
              <Form.Control
                as="textarea"
                rows={6}
                value={gen.finalPrompt}
                onChange={(e) =>
                  dispatchGen({ type: "SET_FINAL_PROMPT", value: e.target.value })
                }
                disabled={gen.generating}
                placeholder="Edita el prompt si deseas..."
                className="lm-input"
              />
            </Form.Group>

            <div className="d-flex flex-wrap align-items-center gap-3">
              <div className="d-flex align-items-center gap-2">
                <Form.Label className="mb-0 small text-muted">
                  Imágenes:
                </Form.Label>
                <Form.Select
                  value={gen.batchSize}
                  onChange={(e) =>
                    dispatchGen({
                      type: "SET_BATCH_SIZE",
                      value: Number(e.target.value),
                    })
                  }
                  disabled={gen.generating}
                  className="lm-select"
                  style={{ width: "auto" }}
                  size="sm"
                >
                  {[1, 2, 3, 4].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </Form.Select>
              </div>
              <div className="d-flex align-items-center gap-2">
                <Form.Label className="mb-0 small text-muted">Seed:</Form.Label>
                <Form.Control
                  type="number"
                  value={seedBase}
                  onChange={(e) => setSeedBase(Number(e.target.value))}
                  disabled={gen.generating}
                  size="sm"
                  style={{ width: 120 }}
                />
                <Button
                  variant="outline-secondary"
                  size="sm"
                  onClick={randomizeSeedBase}
                  disabled={gen.generating}
                  title="Seed aleatorio"
                >
                  🎲
                </Button>
              </div>
            </div>

            <Button
              variant="primary"
              onClick={handleGenerate}
              disabled={gen.generating || !gen.finalPrompt.trim()}
              className="lm-btn"
            >
              {gen.generating ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  Generando…
                </>
              ) : (
                `Generar ${gen.batchSize} imagen${gen.batchSize > 1 ? "es" : ""}`
              )}
            </Button>
          </>
        )}

        {error && (
          <Alert
            variant="danger"
            className="mt-2"
            dismissible
            onClose={() => setError(null)}
          >
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
          Cargando…
        </div>
      );
    }

    if (generations.length === 0) {
      return (
        <div className="lm-empty">
          <span className="lm-empty-glyph">🖼️</span>
          <p>No hay imagenes generadas.</p>
        </div>
      );
    }

    return (
      <div
        className="d-flex flex-column gap-3"
        style={{ maxHeight: "calc(100vh - 220px)", overflowY: "auto" }}
      >
        {generations.map((g) => (
          <div key={g.id} className="lm-card p-3">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <div>
                <Badge bg="secondary" className="me-2">
                  {g.batch_size}
                </Badge>
                <Badge bg="info">
                  {CATEGORY_LABELS[g.category as keyof typeof CATEGORY_LABELS] ||
                    g.category}
                </Badge>
                <small className="text-muted ms-2">
                  {formatDate(g.created_at)}
                </small>
              </div>
            </div>
            <ImageGrid
              gen={g}
              onDelete={handleDeleteImage}
              onSelect={handleSelectImage}
            />
          </div>
        ))}
      </div>
    );
  };

  return (
    <Offcanvas
      show={show}
      onHide={handleHide}
      onShow={handleShow}
      placement="end"
      className="lm-offcanvas"
      style={{ width: 480 }}
    >
      <Offcanvas.Header
        closeButton
        className="lm-offcanvas-header border-bottom"
      >
        <Offcanvas.Title className="mb-0">Generar imagenes</Offcanvas.Title>
      </Offcanvas.Header>
      <Offcanvas.Body className="p-3">
        <Nav variant="tabs" className="lm-tabs mb-3">
          <Nav.Item>
            <Nav.Link
              active={activeTab === "generar"}
              onClick={() => setActiveTab("generar")}
            >
              Generar
            </Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link
              active={activeTab === "historial"}
              onClick={() => setActiveTab("historial")}
            >
              Historial
            </Nav.Link>
          </Nav.Item>
        </Nav>

        {activeTab === "generar" ? renderGenerarTab() : renderHistorialTab()}
      </Offcanvas.Body>

      <Modal
        show={imageModal.show}
        onHide={() => dispatchModal({ type: "CLOSE" })}
        onExited={() => dispatchModal({ type: "CLOSE" })}
        size="xl"
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title className="small text-muted">
            Seed: {imageModal.selectedImage?.seed}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body className="p-2">
          {imageModal.selectedImage && imageModal.selectedGen && (
            <>
              <div className="text-center">
                <img
                  src={resolveImageUrl(
                    imageModal.selectedImage.image_url,
                    imageModal.selectedImage.storage_path,
                  )}
                  alt={`Imagen seed ${imageModal.selectedImage.seed}`}
                  className="img-fluid rounded"
                  style={{ maxHeight: "65vh", objectFit: "contain" }}
                />
              </div>
              <div className="mt-3 px-1">
                <small className="text-muted">
                  <strong>Prompt:</strong> {imageModal.selectedGen.final_prompt}
                </small>
              </div>
            </>
          )}
        </Modal.Body>
        <Modal.Footer className="d-flex justify-content-between">
          <Button
            variant="outline-danger"
            size="sm"
            onClick={() =>
              imageModal.selectedGen &&
              imageModal.selectedImage &&
              handleDeleteImage(
                imageModal.selectedGen.id,
                imageModal.selectedImage.id,
              )
            }
            disabled={imageModal.sharing}
          >
            Eliminar
          </Button>
          <div className="d-flex gap-2">
            {imageModal.selectedGen && imageModal.selectedImage && (
              <Button
                variant={
                  imageModal.selectedImage.is_shared
                    ? "success"
                    : "outline-secondary"
                }
                size="sm"
                onClick={() =>
                  handleShareImage(imageModal.selectedGen!, imageModal.selectedImage!)
                }
                disabled={imageModal.sharing}
                title={
                  imageModal.selectedImage.is_shared
                    ? "Imagen visible en el feed público"
                    : "Compartir en el feed público"
                }
              >
                {imageModal.sharing
                  ? "..."
                  : imageModal.selectedImage.is_shared
                    ? "✦ Compartida"
                    : "Compartir"}
              </Button>
            )}
            {imageModal.selectedGen && (
              <Button
                variant="outline-primary"
                size="sm"
                onClick={() => handleRegenFromHistory(imageModal.selectedGen!)}
                disabled={imageModal.sharing}
                title="Reutilizar prompt en el tab de generar"
              >
                ↻ Regenerar
              </Button>
            )}
            {imageModal.selectedImage && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => handleDownload(imageModal.selectedImage!)}
                disabled={imageModal.sharing}
              >
                Descargar
              </Button>
            )}
            <Button
              variant="secondary"
              onClick={() => dispatchModal({ type: "CLOSE" })}
              disabled={imageModal.sharing}
            >
              Cerrar
            </Button>
          </div>
        </Modal.Footer>
      </Modal>
    </Offcanvas>
  );
}