import { useCallback, useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Form,
  Modal,
  Spinner,
  Table,
} from "react-bootstrap";
import {
  getDocuments,
  getDocument,
  getDocumentContent,
  uploadDocument,
  retryDocument,
  deleteDocument,
  bulkDeleteDocuments,
} from "../../api/documents";
import { ApiAbortError } from "../../api/apiClient";
import { OrderSelect, PageSizeSelect } from "../../components/FilterBar";
import LoadingSpinner from "../../components/LoadingSpinner";
import ConfirmModal from "../../components/ConfirmModal";
import PaginationControls from "../../components/PaginationControls";
import { useDeleteConfirm } from "../../hooks/useDeleteConfirm";
import type { Document } from "../../types";
import { formatDate } from "../../utils/formatters";
import { parseApiError } from "../../utils/errors";

interface Props {
  collectionId: string;
  onDocumentsMutated: () => void;
}

/**
 * Pestaña de documentos dentro del detalle de una colección.
 *
 * Lista los documentos de la colección con filtros por nombre y estado,
 * permite subir nuevos archivos (PDF o TXT), reintentar documentos
 * fallidos, eliminar documentos y ver su detalle. Gestiona el polling
 * automático de documentos en proceso.
 *
 * @param collectionId - Identificador de la colección.
 * @param onDocumentsMutated - Callback cuando la lista de documentos cambia.
 */
export default function DocumentsTab({
  collectionId,
  onDocumentsMutated,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{
    variant: "warning" | "danger";
    text: string;
  } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{
    type: "success" | "warning" | "danger" | "secondary";
    text: string;
  } | null>(null);
  const deleteConfirm = useDeleteConfirm<Document>({
    onDelete: async (doc) => {
      await deleteDocument(collectionId, doc.id);
      await fetchDocuments();
      onDocumentsMutated();
    },
    onError: (e) => setError(parseApiError(e, "Error al eliminar documento")),
  });
  const [filename, setFilename] = useState("");
  const [status, setStatus] = useState<"" | "completed" | "failed">("");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(0);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(
    null,
  );
  const [loadingDocumentDetail, setLoadingDocumentDetail] = useState(false);
  const [documentContent, setDocumentContent] = useState<string | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [selectedFileName, setSelectedFileName] = useState("");
  const [processingDocs, setProcessingDocs] = useState<Document[]>([]);
  const [retrying, setRetrying] = useState<Set<string>>(new Set());
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [showBulkConfirm, setShowBulkConfirm] = useState(false);

  /**
   * Carga la lista de documentos aplicando filtros y paginación.
   *
   * @param signal - Señal de aborto para cancelar la petición.
   */
  const fetchDocuments = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const res = await getDocuments(
          collectionId,
          {
            page,
            page_size: pageSize,
            filename: filename || undefined,
            status: status || undefined,
            order,
          },
          signal,
        );
        setDocuments(res.data);
        setTotalPages(res.meta.total_pages);
      } catch (e) {
        if (e instanceof ApiAbortError) return;
        setError(parseApiError(e, "Error al cargar documentos"));
      } finally {
        setLoading(false);
      }
    },
    [collectionId, filename, order, page, pageSize, status],
  );

  useEffect(() => {
    const controller = new AbortController();
    fetchDocuments(controller.signal);
    return () => controller.abort();
  }, [fetchDocuments]);

  const hasProcessing = documents.some((d) => d.status === "processing");
  useEffect(() => {
    if (!hasProcessing) return;
    const controller = new AbortController();
    const interval = setInterval(() => fetchDocuments(controller.signal), 3000);
    return () => {
      clearInterval(interval);
      controller.abort();
    };
  }, [hasProcessing, fetchDocuments]);

  useEffect(() => {
    if (processingDocs.length === 0) return;
    const controller = new AbortController();
    const interval = setInterval(async () => {
      const justCompleted: string[] = [];
      const justFailed: string[] = [];
      await Promise.allSettled(
        processingDocs.map(async (d) => {
          try {
            const updated = await getDocument(
              collectionId,
              d.id,
              controller.signal,
            );
            if (updated.status === "completed") justCompleted.push(d.id);
            else if (updated.status === "failed") justFailed.push(d.id);
          } catch {
            // keep polling on error
          }
        }),
      );
      const allDone = [...justCompleted, ...justFailed];
      if (allDone.length > 0) {
        const doneDocs = processingDocs.filter((d) => allDone.includes(d.id));
        const failedDocs = doneDocs.filter((d) => justFailed.includes(d.id));
        setProcessingDocs((prev) =>
          prev.filter((d) => !allDone.includes(d.id)),
        );
        fetchDocuments();
        onDocumentsMutated();
        if (failedDocs.length > 0) {
          setUploadMsg({
            type: "danger",
            text:
              failedDocs.length === 1
                ? `Error al procesar "${failedDocs[0].filename}".`
                : `Error al procesar ${failedDocs.length} documentos.`,
          });
        } else {
          const completedDocs = doneDocs.filter((d) =>
            justCompleted.includes(d.id),
          );
          setUploadMsg({
            type: "success",
            text:
              completedDocs.length === 1
                ? `"${completedDocs[0].filename}" procesado correctamente.`
                : `${completedDocs.length} documentos procesados correctamente.`,
          });
        }
      }
    }, 3000);
    return () => {
      clearInterval(interval);
      controller.abort();
    };
  }, [processingDocs, collectionId, fetchDocuments, onDocumentsMutated]);

  const selectableDocs = documents.filter((d) => d.status !== "processing");
  const allSelectableSelected =
    selectableDocs.length > 0 &&
    selectableDocs.every((d) => selectedIds.has(d.id));

  function toggleSelectAll() {
    if (allSelectableSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(selectableDocs.map((d) => d.id)));
    }
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleBulkDelete() {
    setBulkDeleting(true);
    try {
      await bulkDeleteDocuments(collectionId, [...selectedIds]);
      setSelectedIds(new Set());
      setShowBulkConfirm(false);
      await fetchDocuments();
      onDocumentsMutated();
    } catch (e) {
      setError(
        parseApiError(e, "Error al eliminar los documentos seleccionados"),
      );
      setShowBulkConfirm(false);
    } finally {
      setBulkDeleting(false);
    }
  }

  /**
   * Reintenta la ingestión de un documento fallido y lo mueve
   * a la lista de documentos en proceso.
   *
   * @param doc - Documento a reintentar.
   */
  async function handleRetry(doc: Document) {
    setRetrying((prev) => new Set(prev).add(doc.id));
    try {
      const retried = await retryDocument(collectionId, doc.id);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      setProcessingDocs((prev) => [retried, ...prev]);
    } catch (err) {
      setError(
        parseApiError(err, "Error al reintentar la ingestión del documento."),
      );
    } finally {
      setRetrying((prev) => {
        const next = new Set(prev);
        next.delete(doc.id);
        return next;
      });
    }
  }

  /**
   * Sube un nuevo archivo a la colección y lo añade a la lista
   * de documentos en proceso.
   *
   * @param e - Evento de cambio del input de tipo archivo.
   */
  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFileName(file.name);
    setUploading(true);
    setUploadMsg(null);
    try {
      const uploaded = await uploadDocument(collectionId, file);
      setUploadMsg({
        type: "secondary",
        text: `"${file.name}" subido. Procesando...`,
      });
      setProcessingDocs((prev) => [uploaded, ...prev]);
      onDocumentsMutated();
    } catch (err) {
      const { variant, text } = parseApiError(err, "Error al subir");
      setUploadMsg({ type: variant, text });
    } finally {
      setUploading(false);
      setSelectedFileName("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  /**
   * Abre el modal de detalle cargando la información completa
   * de un documento.
   *
   * @param docId - Identificador del documento.
   */
  async function handleOpenDocumentDetail(docId: string) {
    setLoadingDocumentDetail(true);
    setDocumentContent(null);
    try {
      const doc = await getDocument(collectionId, docId);
      setSelectedDocument(doc);
      if (doc.status === "completed") {
        setLoadingContent(true);
        try {
          const { raw_text } = await getDocumentContent(collectionId, docId);
          setDocumentContent(raw_text);
        } catch {
          setDocumentContent(null);
        } finally {
          setLoadingContent(false);
        }
      }
    } catch (e) {
      setError(parseApiError(e, "Error al cargar el detalle del documento"));
    } finally {
      setLoadingDocumentDetail(false);
    }
  }

  const allDocs = [...processingDocs, ...documents];

  return (
    <>
      <Card className="mb-3">
        <Card.Body>
          <div className="d-flex gap-3 flex-wrap align-items-end">
            <Form.Group style={{ minWidth: 220 }}>
              <Form.Label>Buscar archivo</Form.Label>
              <Form.Control
                value={filename}
                onChange={(e) => {
                  setFilename(e.target.value);
                  setPage(1);
                }}
                placeholder="Ej. worldbuilding.pdf"
              />
            </Form.Group>
            <Form.Group style={{ minWidth: 180 }}>
              <Form.Label>Estado</Form.Label>
              <Form.Select
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value as "" | "completed" | "failed");
                  setPage(1);
                }}
              >
                <option value="">Todos</option>
                <option value="completed">Completado</option>
                <option value="failed">Error</option>
              </Form.Select>
            </Form.Group>
            <OrderSelect
              value={order}
              onChange={(o) => {
                setOrder(o);
                setPage(1);
              }}
            />
            <PageSizeSelect
              value={pageSize}
              onChange={(size) => {
                setPageSize(size);
                setPage(1);
              }}
            />
          </div>
        </Card.Body>
      </Card>

      <div className="d-flex justify-content-between align-items-center mb-2">
        <div>
          {selectedIds.size > 0 && (
            <Button
              variant="danger"
              size="sm"
              onClick={() => setShowBulkConfirm(true)}
              disabled={bulkDeleting}
            >
              Eliminar seleccionados ({selectedIds.size})
            </Button>
          )}
        </div>
      </div>

      <div className="mb-3">
        <Form.Label className="fw-semibold">
          Subir documento (PDF o TXT)
        </Form.Label>
        <div className="d-flex align-items-center gap-2 flex-wrap">
          <Form.Control
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt"
            onChange={handleUpload}
            disabled={uploading}
            className="d-none"
          />
          <Button
            type="button"
            variant="outline-secondary"
            className="lm-upload-trigger"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Subiendo..." : "↑ Seleccionar archivo"}
          </Button>
          <small className="text-muted">
            {selectedFileName || "Ningún archivo seleccionado"}
          </small>
          {uploading && (
            <Spinner
              animation="border"
              size="sm"
              className="lm-spinner-inline"
            />
          )}
        </div>
        {uploadMsg && (
          <Alert
            variant={uploadMsg.type}
            className="mt-2 mb-0 py-2"
            onClose={() => setUploadMsg(null)}
            dismissible
          >
            {uploadMsg.text}
          </Alert>
        )}
      </div>

      {error && (
        <Alert
          variant={error.variant}
          onClose={() => setError(null)}
          dismissible
        >
          {error.text}
        </Alert>
      )}

      {loading && allDocs.length === 0 ? (
        <LoadingSpinner />
      ) : allDocs.length === 0 ? (
        <div className="lm-empty">
          <span className="lm-empty-glyph">✦</span>
          <p>No hay documentos en esta colección.</p>
          <p>Sube un PDF o TXT para comenzar.</p>
        </div>
      ) : (
        <Table striped hover responsive className="lm-table">
          <thead>
            <tr>
              <th style={{ width: 40 }}>
                <Form.Check
                  type="checkbox"
                  checked={allSelectableSelected}
                  onChange={toggleSelectAll}
                  disabled={selectableDocs.length === 0}
                />
              </th>
              <th>Archivo</th>
              <th>Tipo</th>
              <th>Chunks</th>
              <th>Estado</th>
              <th>Creado</th>
              <th aria-label="Acciones"></th>
            </tr>
          </thead>
          <tbody>
            {allDocs.map((doc) => (
              <tr key={doc.id}>
                <td>
                  <Form.Check
                    type="checkbox"
                    checked={selectedIds.has(doc.id)}
                    onChange={() => toggleSelect(doc.id)}
                    disabled={doc.status === "processing"}
                  />
                </td>
                <td>
                  {doc.filename}
                  {doc.status === "failed" && doc.processing_error && (
                    <small
                      className="d-block text-danger mt-1"
                      style={{ fontSize: "0.75rem" }}
                    >
                      {doc.processing_error.length > 90
                        ? `${doc.processing_error.slice(0, 90)}…`
                        : doc.processing_error}
                    </small>
                  )}
                </td>
                <td>{doc.file_type.toUpperCase()}</td>
                <td>{doc.chunk_count}</td>
                <td>
                  {doc.status === "completed" && (
                    <Badge bg="success">Completado</Badge>
                  )}
                  {doc.status === "failed" && <Badge bg="danger">Error</Badge>}
                  {doc.status === "processing" && (
                    <span className="d-inline-flex align-items-center gap-1">
                      <Spinner animation="border" size="sm" />
                      <Badge bg="secondary">Procesando</Badge>
                    </span>
                  )}
                </td>
                <td>{formatDate(doc.created_at)}</td>
                <td>
                  {doc.status === "failed" && (
                    <Button
                      variant="outline-warning"
                      size="sm"
                      className="me-2"
                      onClick={() => handleRetry(doc)}
                      disabled={retrying.has(doc.id) || deleteConfirm.deleting}
                    >
                      {retrying.has(doc.id) ? "Reintentando…" : "Reintentar"}
                    </Button>
                  )}
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    className="me-2"
                    onClick={() => handleOpenDocumentDetail(doc.id)}
                    disabled={
                      loadingDocumentDetail ||
                      deleteConfirm.deleting ||
                      doc.status === "processing"
                    }
                  >
                    Detalle
                  </Button>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => deleteConfirm.open(doc)}
                    disabled={
                      deleteConfirm.deleting || doc.status === "processing"
                    }
                  >
                    Eliminar
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <ConfirmModal
        show={deleteConfirm.target !== null}
        title="Eliminar documento"
        message={`¿Eliminar "${deleteConfirm.target?.filename}"? Se borrarán sus chunks del índice vectorial.`}
        onConfirm={deleteConfirm.handleConfirm}
        onCancel={deleteConfirm.cancel}
        loading={deleteConfirm.deleting}
      />

      <ConfirmModal
        show={showBulkConfirm}
        title="Eliminar documentos seleccionados"
        message={`¿Eliminar ${selectedIds.size} documento${selectedIds.size !== 1 ? "s" : ""}? Se borrarán sus chunks del índice vectorial.`}
        onConfirm={handleBulkDelete}
        onCancel={() => setShowBulkConfirm(false)}
        loading={bulkDeleting}
      />
      <Modal
        show={selectedDocument !== null}
        onHide={() => { setSelectedDocument(null); setDocumentContent(null); }}
        centered
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>Detalle del documento</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedDocument && (
            <div className="d-flex flex-column gap-3">
              <div>
                <small className="text-muted">Nombre</small>
                <div style={{ wordBreak: "break-word" }}>{selectedDocument.filename}</div>
              </div>
              <div className="row g-3">
                <div className="col-auto">
                  <small className="text-muted d-block">Tipo</small>
                  <div>{selectedDocument.file_type.toUpperCase()}</div>
                </div>
                <div className="col-auto">
                  <small className="text-muted d-block">Chunks</small>
                  <div>{selectedDocument.chunk_count}</div>
                </div>
                <div className="col-auto">
                  <small className="text-muted d-block">Estado</small>
                  <div>{selectedDocument.status}</div>
                </div>
                <div className="col-auto">
                  <small className="text-muted d-block">Creado</small>
                  <div>{formatDate(selectedDocument.created_at, true)}</div>
                </div>
              </div>
              {selectedDocument.processing_error && (
                <div>
                  <small className="text-muted">Error de procesamiento</small>
                  <div
                    className="text-danger mt-1"
                    style={{ fontSize: "0.875rem", wordBreak: "break-word" }}
                  >
                    {selectedDocument.processing_error}
                  </div>
                </div>
              )}
              {selectedDocument.status === "completed" && (
                <>
                  <hr style={{ borderColor: "var(--lm-border)", margin: 0 }} />
                  <div>
                    <small className="text-muted">Contenido extraído</small>
                    {loadingContent ? (
                      <div className="mt-2 d-flex align-items-center gap-2 text-muted">
                        <Spinner animation="border" size="sm" />
                        <span>Cargando contenido…</span>
                      </div>
                    ) : documentContent ? (
                      <pre
                        style={{
                          maxHeight: 320,
                          overflow: "auto",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          fontSize: "0.78rem",
                          fontFamily: "var(--lm-font-body)",
                          background: "var(--lm-raised)",
                          border: "1px solid var(--lm-border)",
                          color: "var(--lm-text)",
                          padding: "0.75rem",
                          borderRadius: "var(--lm-radius)",
                          marginTop: "0.5rem",
                          marginBottom: 0,
                        }}
                      >
                        {documentContent}
                      </pre>
                    ) : (
                      <div className="text-muted mt-1" style={{ fontSize: "0.875rem" }}>
                        Contenido no disponible.
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </Modal.Body>
      </Modal>
      <PaginationControls
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
      />
    </>
  );
}
