import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  Accordion,
  Alert,
  Badge,
  Button,
  Form,
  Spinner,
} from "react-bootstrap";
import { generateText } from "../../api/generate";
import MarkdownContent from "../../components/MarkdownContent";
import TokenCounter from "../../components/TokenCounter";
import { useGenerate } from "../../hooks/useGenerate";
import { useCollectionDocumentsStatus } from "../../hooks/useCollectionDocumentsStatus";
import { parseApiError } from "../../utils/errors";

interface Props {
  collectionId: string;
  refreshKey: number;
}

/**
 * Pestaña de generación de texto dentro del detalle de una colección.
 *
 * Permite realizar consultas RAG sobre los documentos procesados de la
 * colección, mostrando la respuesta generada por el LLM junto con el
 * número de fuentes consultadas.
 *
 * @param collectionId - Identificador de la colección.
 * @param refreshKey - Clave que fuerza la recarga del estado de documentos.
 */
export default function GenerateTab({ collectionId, refreshKey }: Props) {
  const [query, setQuery] = useState("");
  const [lastQuery, setLastQuery] = useState("");
  const [errorDismissed, setErrorDismissed] = useState(false);
  const { hasCompletedDocs, refresh } =
    useCollectionDocumentsStatus(collectionId);
  const {
    data: result,
    error,
    isLoading,
    isCancelled,
    run,
    cancel,
    reset,
  } = useGenerate(generateText);
  const parsedError = error ? parseApiError(error) : null;

  useEffect(() => {
    if (error) setErrorDismissed(false);
  }, [error]);

  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal);
    return () => controller.abort();
  }, [refreshKey, refresh]);

  /**
   * Envía la consulta al backend para generar texto basado en RAG.
   *
   * @param e - Evento del formulario de consulta.
   */
  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 5) return;
    setLastQuery(trimmedQuery);
    await run(collectionId, { query: trimmedQuery });
  }

  /**
   * Reenvía la última consulta para regenerar la respuesta.
   */
  async function handleRegenerate() {
    if (lastQuery.trim().length < 5 || !hasCompletedDocs) return;
    await run(collectionId, { query: lastQuery.trim() });
  }

  return (
    <>
      {hasCompletedDocs === false && (
        <Alert variant="warning">
          Esta colección no tiene documentos procesados. Sube un PDF o TXT y
          espera a que el estado sea <strong>Completado</strong> antes de
          consultar.
        </Alert>
      )}
      {parsedError && !errorDismissed && (
        <Alert
          variant={parsedError.variant}
          dismissible
          onClose={() => setErrorDismissed(true)}
        >
          {parsedError.text}
        </Alert>
      )}
      {isCancelled && (
        <Alert variant="secondary" dismissible onClose={reset}>
          Generación cancelada.
        </Alert>
      )}

      <div className="d-flex gap-4 align-items-start">
        {/* Query panel */}
        <div style={{ flex: "0 0 380px" }}>
          <p className="lm-section-title">Consulta</p>
          <Form onSubmit={handleGenerate}>
            <Form.Group className="mb-3">
              <Form.Control
                as="textarea"
                rows={5}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Escribe tu consulta al mundo narrativo..."
                minLength={5}
                required
                disabled={isLoading || !hasCompletedDocs}
              />
              <TokenCounter text={query} />
            </Form.Group>
            <div className="d-flex gap-2">
              <Button
                variant="warning"
                type="submit"
                disabled={
                  isLoading || query.trim().length < 5 || !hasCompletedDocs
                }
              >
                {isLoading ? (
                  <>
                    <Spinner
                      animation="border"
                      size="sm"
                      className="me-2 lm-spinner-inline"
                    />
                    Generando…
                  </>
                ) : (
                  "✦ Generar"
                )}
              </Button>
              <Button
                variant="outline-secondary"
                type="button"
                onClick={handleRegenerate}
                disabled={
                  isLoading || lastQuery.trim().length < 5 || !hasCompletedDocs
                }
              >
                ↻ Regenerar
              </Button>
              {isLoading && (
                <Button
                  variant="outline-secondary"
                  type="button"
                  onClick={cancel}
                >
                  Cancelar
                </Button>
              )}
            </div>
          </Form>
        </div>

        {/* Result panel */}
        {isLoading && (
          <div style={{ flex: 1 }}>
            <div className="lm-llm-loading h-100">
              <div className="lm-llm-loading-bar" />
              <small className="text-muted">
                Analizando documentos y redactando respuesta…
              </small>
            </div>
          </div>
        )}
        {result && !isLoading ? (
          <div style={{ flex: 1 }}>
            <Accordion defaultActiveKey="result">
              <Accordion.Item
                eventKey="result"
                className="lm-content-accordion-item"
              >
                <Accordion.Header>
                  <div className="d-flex justify-content-between align-items-center w-100 me-2">
                    <em className="text-muted" style={{ fontSize: "0.88rem" }}>
                      {result.query}
                    </em>
                    <Badge
                      style={{
                        background: "var(--lm-accent-glow)",
                        color: "var(--lm-accent)",
                        border: "1px solid var(--lm-border-accent)",
                        fontSize: "0.65rem",
                      }}
                    >
                      {result.sources_count} fuentes
                    </Badge>
                  </div>
                </Accordion.Header>
                <Accordion.Body>
                  <MarkdownContent>{result.answer}</MarkdownContent>
                </Accordion.Body>
              </Accordion.Item>
            </Accordion>
          </div>
        ) : (
          !isLoading && (
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "4rem 2rem",
                border: "1px dashed var(--lm-border)",
                borderRadius: "var(--lm-radius-lg)",
              }}
            >
              <p
                className="text-muted mb-0"
                style={{ fontStyle: "italic", fontSize: "0.95rem" }}
              >
                El resultado aparecerá aquí…
              </p>
            </div>
          )
        )}
      </div>
    </>
  );
}
