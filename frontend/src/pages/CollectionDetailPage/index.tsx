import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Alert, Breadcrumb, Tab, Tabs } from "react-bootstrap";
import { getCollection } from "../../api/collections";
import LoadingSpinner from "../../components/LoadingSpinner";
import DocumentsTab from "./DocumentsTab";
import EntitiesTab from "./EntitiesTab";
import GenerateTab from "./GenerateTab";
import type { Collection } from "../../types";
import { getErrorMessage } from "../../utils/errors";

/**
 * Página de detalle de una colección.
 *
 * Organiza la vista en tres pestañas: documentos, entidades y generación
 * de texto. Mantiene sincronizado el estado de documentos entre las
 * pestañas de documentos y generación mediante una clave de refresco.
 */
export default function CollectionDetailPage() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const [collection, setCollection] = useState<Collection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [documentsRefreshKey, setDocumentsRefreshKey] = useState(0);

  /**
   * Carga los datos básicos de la colección desde la API.
   */
  const fetchCollection = useCallback(async () => {
    if (!collectionId) return;
    setError(null);
    setLoading(true);
    try {
      const col = await getCollection(collectionId);
      setCollection(col);
    } catch (e) {
      setError(getErrorMessage(e, "Error al cargar la colección"));
    } finally {
      setLoading(false);
    }
  }, [collectionId]);

  useEffect(() => {
    fetchCollection();
  }, [fetchCollection]);

  if (loading) return <LoadingSpinner />;
  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!collection || !collectionId) return null;

  return (
    <div className="lm-page">
      <Breadcrumb>
        <Breadcrumb.Item linkAs={Link} linkProps={{ to: "/collections" }}>
          Colecciones
        </Breadcrumb.Item>
        <Breadcrumb.Item active>{collection.name}</Breadcrumb.Item>
      </Breadcrumb>

      <h2 className="mb-4">{collection.name}</h2>

      <Tabs defaultActiveKey="documents" className="mb-4">
        <Tab eventKey="documents" title="Documentos">
          <DocumentsTab
            collectionId={collectionId}
            onDocumentsMutated={() =>
              setDocumentsRefreshKey((current) => current + 1)
            }
          />
        </Tab>
        <Tab eventKey="entities" title="Entidades">
          <EntitiesTab collectionId={collectionId} />
        </Tab>
        <Tab eventKey="generate" title="Generar texto">
          <GenerateTab
            collectionId={collectionId}
            refreshKey={documentsRefreshKey}
          />
        </Tab>
      </Tabs>
    </div>
  );
}
