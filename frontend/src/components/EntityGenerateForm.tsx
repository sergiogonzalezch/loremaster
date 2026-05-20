import { useState, type FormEvent } from "react";
import { Alert, Button, Form, Spinner } from "react-bootstrap";
import type { ContentCategory } from "../utils/enums";
import { CATEGORY_LABELS } from "../utils/constants";
import { parseApiError } from "../utils/errors";
import ModelSelector from "./ModelSelector";
import TokenCounter from "./TokenCounter";

interface Props {
  availableCategories: ContentCategory[];
  selectedCategory: ContentCategory | "";
  onCategoryChange: (cat: ContentCategory) => void;
  generating: boolean;
  generateError: unknown;
  generateCancelled: boolean;
  pendingInCategoryCount: number;
  maxPendingContents: number;
  onSubmit: (query: string, model: string | undefined) => Promise<void>;
  onCancel: () => void;
  onDismissError: () => void;
}

export default function EntityGenerateForm({
  availableCategories,
  selectedCategory,
  onCategoryChange,
  generating,
  generateError,
  generateCancelled,
  pendingInCategoryCount,
  maxPendingContents,
  onSubmit,
  onCancel,
  onDismissError,
}: Props) {
  const [query, setQuery] = useState("");
  const [lastSubmittedQuery, setLastSubmittedQuery] = useState("");
  const [selectedModel, setSelectedModel] = useState<string | undefined>(undefined);

  const pendingLimitReached =
    selectedCategory !== "" && pendingInCategoryCount >= maxPendingContents;
  const alertConfig =
    generateError != null
      ? parseApiError(generateError, "Error al generar contenido")
      : null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 5 || selectedCategory === "") return;
    setLastSubmittedQuery(trimmed);
    await onSubmit(trimmed, selectedModel);
  }

  function handleRegenerate() {
    if (lastSubmittedQuery.trim().length >= 5 && selectedCategory !== "") {
      void onSubmit(lastSubmittedQuery, selectedModel);
    }
  }

  return (
    <>
      <p className="lm-section-title">Generar contenido</p>
      {alertConfig != null && (
        <Alert variant={alertConfig.variant} onClose={onDismissError} dismissible>
          {alertConfig.text}
        </Alert>
      )}
      {generateCancelled && (
        <Alert variant="secondary" dismissible>
          Generación cancelada.
        </Alert>
      )}
      {pendingLimitReached && (
        <Alert variant="warning">
          Ya tienes {pendingInCategoryCount} contenidos pendientes en esta categoría (máximo{" "}
          {maxPendingContents}). Confirma o descarta alguno antes de generar uno nuevo.
        </Alert>
      )}
      <Form onSubmit={handleSubmit} className="mb-4">
        <div className="d-flex gap-3 flex-wrap mb-2">
          <Form.Group>
            <Form.Label className="fw-semibold">Categoría</Form.Label>
            <Form.Select
              value={selectedCategory}
              onChange={(e) => onCategoryChange(e.target.value as ContentCategory)}
              disabled={generating}
              style={{ maxWidth: 280 }}
            >
              {availableCategories.map((cat) => (
                <option key={cat} value={cat}>
                  {CATEGORY_LABELS[cat]}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
          <ModelSelector disabled={generating} onChange={setSelectedModel} />
        </div>
        <div className="d-flex gap-2 align-items-start flex-wrap">
          <Form.Control
            as="textarea"
            rows={2}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe qué quieres generar sobre esta entidad..."
            minLength={5}
            required
            disabled={generating || pendingLimitReached}
          />
          <Button
            variant="warning"
            type="submit"
            disabled={
              generating ||
              pendingLimitReached ||
              query.trim().length < 5 ||
              selectedCategory === ""
            }
            style={{ whiteSpace: "nowrap" }}
            title={
              pendingLimitReached
                ? `Máximo ${maxPendingContents} contenidos pendientes por categoría`
                : undefined
            }
          >
            {generating ? (
              <>
                <Spinner
                  animation="border"
                  size="sm"
                  className="me-1 lm-spinner-inline"
                />
                Generando…
              </>
            ) : (
              "Generar"
            )}
          </Button>
          <Button
            variant="outline-secondary"
            type="button"
            onClick={handleRegenerate}
            disabled={
              generating ||
              pendingLimitReached ||
              lastSubmittedQuery.trim().length < 5 ||
              selectedCategory === ""
            }
            title={
              lastSubmittedQuery
                ? `Reutilizar último prompt: "${lastSubmittedQuery}"`
                : "Genera contenido una vez para habilitar regenerar"
            }
          >
            ↻ Regenerar
          </Button>
          {generating && (
            <Button
              variant="outline-secondary"
              type="button"
              onClick={onCancel}
              style={{ whiteSpace: "nowrap" }}
            >
              Cancelar
            </Button>
          )}
        </div>
        <div className="d-flex justify-content-between mt-1">
          <TokenCounter text={query} />
          {selectedCategory !== "" &&
            !pendingLimitReached &&
            pendingInCategoryCount > 0 && (
              <small className="text-muted">
                {pendingInCategoryCount} / {maxPendingContents} borradores pendientes en esta
                categoría.
              </small>
            )}
        </div>
      </Form>
      {generating && (
        <div className="lm-llm-loading mb-4">
          <div className="lm-llm-loading-bar" />
          <small className="text-muted">
            Procesando prompt con el modelo y preparando un nuevo borrador…
          </small>
        </div>
      )}
    </>
  );
}
