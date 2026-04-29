// src/components/ImagePreviewCard.tsx

import { useState } from "react";
import { Alert, Badge, Button, Card, Spinner } from "react-bootstrap";
import { generateImage } from "../api/images";
import type { GenerateImageResponse } from "../types";
import { parseApiError } from "../utils/errors";

interface Props {
  collectionId: string;
  entityId: string;
  confirmedContentId?: string;     // si viene de un ContentCard confirmado
  entityName: string;
}

export default function ImagePreviewCard({
  collectionId,
  entityId,
  confirmedContentId,
  entityName,
}: Props) {
  const [result, setResult] = useState<GenerateImageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const res = await generateImage(collectionId, entityId, {
        content_id: confirmedContentId,
      });
      setResult(res);
    } catch (e) {
      setError(parseApiError(e, "Error al generar preview"));
    } finally {
      setLoading(false);
    }
  }

  const tokenWarning = result && result.token_count > 100;

  return (
    <Card className="mb-3">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <span style={{ fontFamily: "var(--lm-font-head)", fontSize: "0.85rem" }}>
          Preview de imagen
        </span>
        <div className="d-flex gap-2 align-items-center">
          {result && (
            <Badge bg="secondary" style={{ fontSize: "0.6rem" }}>
              {result.backend.toUpperCase()}
            </Badge>
          )}
          {result?.truncated && (
            <Badge
              bg="warning"
              text="dark"
              style={{ fontSize: "0.6rem" }}
              title="El contenido fue truncado para respetar el límite de tokens"
            >
              prompt truncado
            </Badge>
          )}
        </div>
      </Card.Header>

      <Card.Body>
        {error && (
          <Alert
            variant={error.variant}
            onClose={() => setError(null)}
            dismissible
            className="py-2"
          >
            {error.text}
          </Alert>
        )}

        {/* Imagen / placeholder */}
        {result ? (
          <div className="text-center mb-3">
            <img
              src={result.image_url}
              alt={`Preview de ${entityName}`}
              style={{
                width: "100%",
                maxWidth: 320,
                aspectRatio: "1/1",
                borderRadius: "var(--lm-radius-lg)",
                border: "1px solid var(--lm-border)",
                objectFit: "cover",
              }}
            />
            <div className="mt-2 d-flex justify-content-center gap-2">
              <small className="text-muted">
                ~{result.token_count} tokens
              </small>
              {tokenWarning && (
                <small className="text-warning">
                  (considera usar contenido más conciso)
                </small>
              )}
            </div>
          </div>
        ) : (
          <div
            style={{
              width: "100%",
              aspectRatio: "1/1",
              maxWidth: 320,
              margin: "0 auto 1rem",
              border: "1px dashed var(--lm-border)",
              borderRadius: "var(--lm-radius-lg)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <span className="text-muted" style={{ fontSize: "0.85rem" }}>
              Sin preview generado
            </span>
          </div>
        )}

        {/* Prompt visual colapsable */}
        {result && (
          <details
            open={showPrompt}
            onToggle={(e) =>
              setShowPrompt((e.target as HTMLDetailsElement).open)
            }
          >
            <summary
              style={{
                fontSize: "0.75rem",
                color: "var(--lm-text-muted)",
                cursor: "pointer",
                userSelect: "none",
                marginBottom: "0.5rem",
              }}
            >
              Ver prompt visual generado
            </summary>
            <code
              style={{
                display: "block",
                fontSize: "0.78rem",
                color: "var(--lm-text-muted)",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid var(--lm-border)",
                borderRadius: "var(--lm-radius)",
                padding: "0.65rem",
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {result.visual_prompt}
            </code>
            <div className="mt-1 d-flex gap-3">
              <small className="text-muted">
                fuente:{" "}
                <strong>
                  {result.prompt_source === "content"
                    ? "contenido RAG"
                    : result.prompt_source === "description"
                    ? "descripción de entidad"
                    : "solo nombre"}
                </strong>
              </small>
            </div>
          </details>
        )}
      </Card.Body>

      <Card.Footer>
        <Button
          variant="outline-secondary"
          size="sm"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? (
            <>
              <Spinner animation="border" size="sm" className="me-1" />
              Generando...
            </>
          ) : result ? (
            "↻ Regenerar preview"
          ) : (
            "✦ Generar preview"
          )}
        </Button>
      </Card.Footer>
    </Card>
  );
}