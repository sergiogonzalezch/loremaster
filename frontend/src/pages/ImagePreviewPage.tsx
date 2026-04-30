// frontend/src/pages/ImagePreviewPage.tsx

import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Alert,
  Badge,
  Breadcrumb,
  Button,
  Card,
  Col,
  Row,
  Spinner,
} from "react-bootstrap";
import { generateImage } from "../api/images";
import { getContents } from "../api/contents";
import { getEntity, getCollection } from "../api";
import LoadingSpinner from "../components/LoadingSpinner";
import type { GenerateImageResponse } from "../types/";
import type { Entity, Collection, EntityContent } from "../types";
import { parseApiError } from "../utils/errors";
import { CATEGORY_LABELS } from "../utils/constants";

const PROMPT_SOURCE_LABEL: Record<string, string> = {
  content_direct: "Descripción extendida (texto completo)",
  content_sentences: "Escena/Capítulo (primeras oraciones)",
  description: "Descripción de entidad (fallback)",
  name_only: "Solo nombre (sin contexto)",
};

const STRATEGY_LABEL: Record<string, string> = {
  direct: "Directo — el texto RAG se usa como descriptor",
  first_sentences: "Primeras oraciones — extrae el setting visual",
  entity_only: "Solo entidad — la narrativa no es visual",
};

export default function ImagePreviewPage() {
  const { collectionId, entityId, contentId } = useParams<{
    collectionId: string;
    entityId: string;
    contentId: string;
  }>();

  const [collection, setCollection] = useState<Collection | null>(null);
  const [entity, setEntity] = useState<Entity | null>(null);
  const [content, setContent] = useState<EntityContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<GenerateImageResponse | null>(null);
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);

  useEffect(() => {
    if (!collectionId || !entityId || !contentId) return;
    Promise.all([
      getCollection(collectionId),
      getEntity(collectionId, entityId),
      getContents(collectionId, entityId, { status: "confirmed" }),
    ])
      .then(([col, ent, contents]) => {
        setCollection(col);
        setEntity(ent);
        const found = contents.data.find((c) => c.id === contentId);
        setContent(found ?? null);
      })
      .catch(() =>
        setError({ variant: "danger", text: "Error al cargar datos" }),
      )
      .finally(() => setLoading(false));
  }, [collectionId, entityId, contentId]);

  async function handleGenerate() {
    if (!collectionId || !entityId || !contentId) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await generateImage(collectionId, entityId, {
        content_id: contentId,
      });
      setResult(res);
    } catch (e) {
      setError(parseApiError(e, "Error al generar preview"));
    } finally {
      setGenerating(false);
    }
  }

  if (loading) return <LoadingSpinner />;

  return (
    <div className="lm-page">
      <Breadcrumb>
        <Breadcrumb.Item linkAs={Link} linkProps={{ to: "/" }}>
          Colecciones
        </Breadcrumb.Item>
        <Breadcrumb.Item
          linkAs={Link}
          linkProps={{ to: `/collections/${collectionId}` }}
        >
          {collection?.name ?? collectionId}
        </Breadcrumb.Item>
        <Breadcrumb.Item
          linkAs={Link}
          linkProps={{
            to: `/collections/${collectionId}/entities/${entityId}`,
          }}
        >
          {entity?.name ?? entityId}
        </Breadcrumb.Item>
        <Breadcrumb.Item active>Preview imagen</Breadcrumb.Item>
      </Breadcrumb>

      <h2 className="mb-4">Preview de imagen</h2>

      {error && (
        <Alert
          variant={error.variant}
          onClose={() => setError(null)}
          dismissible
        >
          {error.text}
        </Alert>
      )}

      <Row className="g-4">
        {/* ── Panel izquierdo: contexto del contenido base ── */}
        <Col md={6}>
          <p className="lm-section-title">Contenido base</p>

          {content ? (
            <Card>
              <Card.Header className="d-flex gap-2 align-items-center">
                <Badge bg="dark">
                  {
                    CATEGORY_LABELS[
                      content.category as keyof typeof CATEGORY_LABELS
                    ]
                  }
                </Badge>
                <Badge bg="success">Confirmado</Badge>
              </Card.Header>
              <Card.Body>
                <p
                  style={{
                    fontSize: "0.9rem",
                    color: "var(--lm-text-muted)",
                    fontStyle: "italic",
                    marginBottom: "0.75rem",
                  }}
                >
                  Query original: "{content.query}"
                </p>
                <div
                  style={{
                    maxHeight: 320,
                    overflowY: "auto",
                    fontSize: "0.9rem",
                    lineHeight: 1.7,
                    paddingRight: "0.5rem",
                  }}
                >
                  {content.content}
                </div>
              </Card.Body>
            </Card>
          ) : (
            <Alert variant="warning">
              No se encontró el contenido confirmado.
            </Alert>
          )}
        </Col>

        {/* ── Panel derecho: preview generado ── */}
        <Col md={6}>
          <p className="lm-section-title">Preview generado</p>

          {/* Imagen */}
          <div className="text-center mb-3">
            {result ? (
              <img
                src={result.image_url}
                alt={`Preview de ${entity?.name}`}
                style={{
                  width: "100%",
                  maxWidth: 340,
                  aspectRatio: "1/1",
                  borderRadius: "var(--lm-radius-lg)",
                  border: "1px solid var(--lm-border)",
                  objectFit: "cover",
                }}
              />
            ) : (
              <div
                style={{
                  width: "100%",
                  maxWidth: 340,
                  margin: "0 auto",
                  aspectRatio: "1/1",
                  border: "1px dashed var(--lm-border)",
                  borderRadius: "var(--lm-radius-lg)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <span className="text-muted" style={{ fontSize: "0.85rem" }}>
                  Sin preview todavía
                </span>
              </div>
            )}
          </div>

          {/* Botón generar */}
          <div className="d-flex justify-content-center mb-3">
            <Button
              variant="warning"
              onClick={handleGenerate}
              disabled={generating || !content}
            >
              {generating ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  Generando...
                </>
              ) : result ? (
                "↻ Regenerar preview"
              ) : (
                "✦ Generar preview"
              )}
            </Button>
          </div>

          {/* Metadatos del prompt */}
          {result && (
            <Card>
              <Card.Header>
                <div className="d-flex gap-2 flex-wrap">
                  <Badge bg="secondary">{result.backend.toUpperCase()}</Badge>
                  {result.truncated && (
                    <Badge bg="warning" text="dark">
                      prompt truncado
                    </Badge>
                  )}
                  <Badge
                    style={{
                      background: "var(--lm-accent-glow)",
                      color: "var(--lm-accent)",
                      border: "1px solid var(--lm-border-accent)",
                    }}
                  >
                    ~{result.prompt_token_count} tokens
                  </Badge>
                </div>
              </Card.Header>
              <Card.Body>
                {/* Estrategia aplicada */}
                <div className="mb-3">
                  <small className="text-muted d-block mb-1">
                    Estrategia de extracción
                  </small>
                  <small>
                    {STRATEGY_LABEL[result.prompt_strategy] ??
                      result.prompt_strategy}
                  </small>
                </div>

                {/* Fuente del contexto */}
                <div className="mb-3">
                  <small className="text-muted d-block mb-1">
                    Contexto utilizado
                  </small>
                  <small>
                    {PROMPT_SOURCE_LABEL[result.prompt_source] ??
                      result.prompt_source}
                  </small>
                </div>

                {/* Prompt visual generado */}
                <div>
                  <small className="text-muted d-block mb-1">
                    Prompt visual generado
                  </small>
                  <code
                    style={{
                      display: "block",
                      fontSize: "0.78rem",
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid var(--lm-border)",
                      borderRadius: "var(--lm-radius)",
                      padding: "0.65rem",
                      lineHeight: 1.6,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      color: "var(--lm-text-muted)",
                    }}
                  >
                    {result.visual_prompt}
                  </code>
                </div>
              </Card.Body>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
