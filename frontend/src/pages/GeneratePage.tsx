import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Alert,
  Badge,
  Breadcrumb,
  Button,
  Card,
  Form,
  Spinner,
} from "react-bootstrap";
import { getCollection, generateText } from "../api";
import { parseApiError } from "../utils/errors";
import MarkdownContent from "../components/MarkdownContent";
import TokenCounter from "../components/TokenCounter";
import { useGenerate } from "../hooks/useGenerate";
import { useCollectionDocumentsStatus } from "../hooks/useCollectionDocumentsStatus";

export default function GeneratePage() {
  const { collectionId } = useParams<{ collectionId: string }>();

  const [collectionName, setCollectionName] = useState<string>("");
  const [query, setQuery] = useState("");
  const [errorDismissed, setErrorDismissed] = useState(false);
  const { hasCompletedDocs, refresh } = useCollectionDocumentsStatus(collectionId);
  const {
    data: result,
    error,
    isLoading,
    isCancelled,
    run,
    cancel,
    reset,
  } = useGenerate(generateText);

  useEffect(() => {
    if (error) setErrorDismissed(false);
  }, [error]);

  useEffect(() => {
    if (!collectionId) return;
    getCollection(collectionId)
      .then((col) => setCollectionName(col.name))
      .catch(() => {});
  }, [collectionId]);

  const parsedError = error ? parseApiError(error) : null;

  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    if (!collectionId) return;
    const canGenerate = await refresh();
    if (!canGenerate) return;
    await run(collectionId, { query });
  }

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
          {collectionName || collectionId}
        </Breadcrumb.Item>
        <Breadcrumb.Item active>Generar texto</Breadcrumb.Item>
      </Breadcrumb>

      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="mb-0">Generar texto</h2>
        <Link
          to={`/collections/${collectionId}`}
          className="btn btn-outline-secondary btn-sm"
        >
          ← Volver a la colección
        </Link>
      </div>

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
      {hasCompletedDocs === false && (
        <Alert variant="warning">
          Esta colección aún no tiene documentos procesados. Sube un PDF o TXT
          y espera a que finalice el procesamiento.
        </Alert>
      )}

      <Form onSubmit={handleGenerate} className="mb-4">
        <Form.Group className="mb-3">
          <Form.Label className="fw-semibold">Consulta</Form.Label>
          <Form.Control
            as="textarea"
            rows={4}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Escribe tu consulta al mundo narrativo..."
            minLength={5}
            required
            disabled={isLoading || hasCompletedDocs === false}
          />
          <TokenCounter text={query} />
        </Form.Group>
        <div className="d-flex gap-2">
          <Button
            variant="warning"
            type="submit"
            disabled={
              isLoading || query.trim().length < 5 || hasCompletedDocs === false
            }
          >
            {isLoading ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Generando...
              </>
            ) : (
              "Generar"
            )}
          </Button>
          {isLoading && (
            <Button variant="outline-secondary" type="button" onClick={cancel}>
              Cancelar
            </Button>
          )}
        </div>
      </Form>

      {result && (
        <Card>
          <Card.Header className="d-flex justify-content-between align-items-center">
            <em className="text-muted">{result.query}</em>
            <Badge bg="secondary">{result.sources_count} fuentes</Badge>
          </Card.Header>
          <Card.Body>
            <MarkdownContent>{result.answer}</MarkdownContent>
          </Card.Body>
        </Card>
      )}
    </div>
  );
}
