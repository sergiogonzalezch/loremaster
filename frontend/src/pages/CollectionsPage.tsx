import { useEffect, useState, useCallback } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Row, Col, Card, Button, Alert, Modal, Form } from "react-bootstrap";
import { getCollections, createCollection, deleteCollection } from "../api";
import LoadingSpinner from "../components/LoadingSpinner";
import ConfirmModal from "../components/ConfirmModal";
import type { Collection } from "../types";
import { formatDate } from "../utils/formatters";
import { getErrorMessage } from "../utils/errors";

export default function CollectionsPage() {
  const navigate = useNavigate();

  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<Collection | null>(null);
  const [deleting, setDeleting] = useState(false);

  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchCollections = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getCollections();
      setCollections(res.data);
    } catch (e) {
      setError(getErrorMessage(e, "Error al cargar las colecciones"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteCollection(deleteTarget.id);
      setDeleteTarget(null);
      await fetchCollections();
    } catch (e) {
      setError(getErrorMessage(e, "Error al eliminar la colección"));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await createCollection({ name: createName, description: createDescription });
      setShowCreate(false);
      setCreateName("");
      setCreateDescription("");
      await fetchCollections();
    } catch (e) {
      setError(getErrorMessage(e, "Error al crear la colección"));
    } finally {
      setCreating(false);
    }
  }

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="mb-0">Colecciones</h2>
        <Button variant="warning" onClick={() => setShowCreate(true)}>
          + Nueva colección
        </Button>
      </div>

      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          {error}
        </Alert>
      )}

      {loading ? (
        <LoadingSpinner />
      ) : collections.length === 0 ? (
        <div className="text-center py-5 text-muted">
          <p className="fs-5">No hay colecciones todavía.</p>
          <p>Crea tu primera colección para empezar a construir tu mundo.</p>
        </div>
      ) : (
        <Row className="g-4">
          {collections.map((col) => (
            <Col key={col.id} md={4}>
              <Card
                className="h-100"
                style={{ cursor: "pointer" }}
                onClick={() => navigate(`/collections/${col.id}`)}
              >
                <Card.Body>
                  <Card.Title>{col.name}</Card.Title>
                  <Card.Text
                    className="text-muted"
                    style={{
                      overflow: "hidden",
                      display: "-webkit-box",
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: "vertical",
                    }}
                  >
                    {col.description || "Sin descripción"}
                  </Card.Text>
                </Card.Body>
                <Card.Footer className="d-flex justify-content-between align-items-center">
                  <small className="text-muted">{formatDate(col.created_at)}</small>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTarget(col);
                    }}
                  >
                    Eliminar
                  </Button>
                </Card.Footer>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <ConfirmModal
        show={deleteTarget !== null}
        title="Eliminar colección"
        message={`¿Estás seguro de que quieres eliminar "${deleteTarget?.name}"? Esta acción eliminará todos sus documentos y entidades.`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        variant={deleting ? "secondary" : "danger"}
      />

      <Modal show={showCreate} onHide={() => setShowCreate(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Nueva colección</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleCreate}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Nombre *</Form.Label>
              <Form.Control
                type="text"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                placeholder="Nombre de la colección"
                required
                autoFocus
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Descripción</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={createDescription}
                onChange={(e) => setCreateDescription(e.target.value)}
                placeholder="Descripción opcional"
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowCreate(false)} disabled={creating}>
              Cancelar
            </Button>
            <Button variant="warning" type="submit" disabled={creating || !createName.trim()}>
              {creating ? "Creando..." : "Crear"}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </>
  );
}