import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Alert, Badge, Breadcrumb, Button, Card, Form, Spinner } from "react-bootstrap";
import { getCollection, generateText } from "../api";
import type { GenerateTextResponse } from "../types";
import { parseApiError } from "../utils/errors";

export default function GeneratePage() {
  const { collectionId } = useParams<{ collectionId: string }>();

  const [collectionName, setCollectionName] = useState<string>("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateTextResponse | null>(null);
  const [error, setError] = useState<{ variant: "warning" | "danger"; text: string } | null>(null);

  useEffect(() => {
    if (!collectionId) return;
    getCollection(collectionId)
      .then((col) => setCollectionName(col.name))
      .catch(() => {});
  }, [collectionId]);

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!collectionId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await generateText(collectionId, { query });
      setResult(res);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Breadcrumb>
        <Breadcrumb.Item linkAs={Link} linkProps={{ to: "/" }}>
          Colecciones
        </Breadcrumb.Item>
        <Breadcrumb.Item linkAs={Link} linkProps={{ to: `/collections/${collectionId}` }}>
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

      {error && (
        <Alert variant={error.variant} onClose={() => setError(null)} dismissible>
          {error.text}
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
            disabled={loading}
          />
        </Form.Group>
        <Button
          variant="warning"
          type="submit"
          disabled={loading || query.trim().length < 5}
        >
          {loading ? (
            <>
              <Spinner animation="border" size="sm" className="me-2" />
              Generando...
            </>
          ) : (
            "Generar"
          )}
        </Button>
      </Form>

      {result && (
        <Card>
          <Card.Header className="d-flex justify-content-between align-items-center">
            <em className="text-muted">{result.query}</em>
            <Badge bg="secondary">{result.sources_count} fuentes</Badge>
          </Card.Header>
          <Card.Body>
            <p
              className="mb-0"
              style={{ whiteSpace: "pre-wrap", lineHeight: "1.7" }}
            >
              {result.answer}
            </p>
          </Card.Body>
        </Card>
      )}
    </>
  );
}
