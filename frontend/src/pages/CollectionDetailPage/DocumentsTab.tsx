import { useCallback, useEffect, useReducer, useRef, useState } from "react";
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

// ── Reducers ─────────────────────────────────────────────────────────────────

type FiltersState = {
  filename: string;
  status: "" | "completed" | "failed";
  order: "asc" | "desc";
  page: number;
  pageSize: number;
  totalPages: number;
};

type FiltersAction =
  | { type: "SET_FILENAME"; value: string }
  | { type: "SET_STATUS"; value: "" | "completed" | "failed" }
  | { type: "SET_ORDER"; value: "asc" | "desc" }
  | { type: "SET_PAGE"; value: number }
  | { type: "SET_PAGE_SIZE"; value: number }
  | { type: "SET_TOTAL_PAGES"; value: number };

function filtersReducer(
  state: FiltersState,
  action: FiltersAction,
): FiltersState {
  switch (action.type) {
    case "SET_FILENAME":
      return { ...state, filename: action.value, page: 1 };
    case "SET_STATUS":
      return { ...state, status: action.value, page: 1 };
    case "SET_ORDER":
      return { ...state, order: action.value, page: 1 };
    case "SET_PAGE":
      return { ...state, page: action.value };
    case "SET_PAGE_SIZE":
      return { ...state, pageSize: action.value, page: 1 };
    case "SET_TOTAL_PAGES":
      return { ...state, totalPages: action.value };
  }
}

type UploadMsg = {
  type: "success" | "warning" | "danger" | "secondary";
  text: string;
} | null;

type UploadState = {
  uploading: boolean;
  selectedFileName: string;
  uploadMsg: UploadMsg;
  processingDocs: Document[];
  retrying: Set<string>;
};

type UploadAction =
  | { type: "UPLOAD_START"; filename: string }
  | { type: "UPLOAD_SUCCESS"; doc: Document; filename: string }
  | { type: "UPLOAD_ERROR"; msg: UploadMsg }
  | { type: "DISMISS_MSG" }
  | { type: "RETRY_START"; id: string; movedDoc: Document }
  | { type: "RETRY_END"; id: string }
  | {
      type: "PROCESSING_DONE";
      completedIds: string[];
      failedIds: string[];
      msg: UploadMsg;
    };

function uploadReducer(state: UploadState, action: UploadAction): UploadState {
  switch (action.type) {
    case "UPLOAD_START":
      return {
        ...state,
        uploading: true,
        selectedFileName: action.filename,
        uploadMsg: null,
      };
    case "UPLOAD_SUCCESS":
      return {
        ...state,
        uploading: false,
        selectedFileName: "",
        processingDocs: [action.doc, ...state.processingDocs],
        uploadMsg: {
          type: "secondary",
          text: `"${action.filename}" subido. Procesando...`,
        },
      };
    case "UPLOAD_ERROR":
      return {
        ...state,
        uploading: false,
        selectedFileName: "",
        uploadMsg: action.msg,
      };
    case "DISMISS_MSG":
      return { ...state, uploadMsg: null };
    case "RETRY_START":
      return {
        ...state,
        retrying: new Set(state.retrying).add(action.id),
        processingDocs: [action.movedDoc, ...state.processingDocs],
      };
    case "RETRY_END": {
      const next = new Set(state.retrying);
      next.delete(action.id);
      return { ...state, retrying: next };
    }
    case "PROCESSING_DONE": {
      const done = [...action.completedIds, ...action.failedIds];
      return {
        ...state,
        processingDocs: state.processingDocs.filter(
          (d) => !done.includes(d.id),
        ),
        uploadMsg: action.msg,
      };
    }
  }
}

type DetailState = {
  selectedDocument: Document | null;
  loadingDocumentDetail: boolean;
  documentContent: string | null;
  loadingContent: boolean;
};

type DetailAction =
  | { type: "OPEN_START" }
  | { type: "OPEN_SUCCESS"; doc: Document }
  | { type: "OPEN_ERROR" }
  | { type: "CONTENT_LOADING" }
  | { type: "CONTENT_LOADED"; content: string | null }
  | { type: "CLOSE" };

function detailReducer(state: DetailState, action: DetailAction): DetailState {
  switch (action.type) {
    case "OPEN_START":
      return { ...state, loadingDocumentDetail: true, documentContent: null };
    case "OPEN_SUCCESS":
      return {
        ...state,
        loadingDocumentDetail: false,
        selectedDocument: action.doc,
      };
    case "OPEN_ERROR":
      return { ...state, loadingDocumentDetail: false };
    case "CONTENT_LOADING":
      return { ...state, loadingContent: true };
    case "CONTENT_LOADED":
      return {
        ...state,
        loadingContent: false,
        documentContent: action.content,
      };
    case "CLOSE":
      return {
        selectedDocument: null,
        loadingDocumentDetail: false,
        documentContent: null,
        loadingContent: false,
      };
  }
}

type BulkState = {
  selectedIds: Set<string>;
  bulkDeleting: boolean;
  showBulkConfirm: boolean;
};

type BulkAction =
  | { type: "TOGGLE_ONE"; id: string }
  | { type: "REMOVE_ONE"; id: string }
  | { type: "SET_ALL"; ids: string[] }
  | { type: "CLEAR" }
  | { type: "OPEN_CONFIRM" }
  | { type: "CLOSE_CONFIRM" }
  | { type: "DELETE_START" }
  | { type: "DELETE_DONE" };

function bulkReducer(state: BulkState, action: BulkAction): BulkState {
  switch (action.type) {
    case "TOGGLE_ONE": {
      const next = new Set(state.selectedIds);
      if (next.has(action.id)) next.delete(action.id);
      else next.add(action.id);
      return { ...state, selectedIds: next };
    }
    case "REMOVE_ONE": {
      if (!state.selectedIds.has(action.id)) return state;
      const next = new Set(state.selectedIds);
      next.delete(action.id);
      return { ...state, selectedIds: next };
    }
    case "SET_ALL":
      return { ...state, selectedIds: new Set(action.ids) };
    case "CLEAR":
      return { ...state, selectedIds: new Set() };
    case "OPEN_CONFIRM":
      return { ...state, showBulkConfirm: true };
    case "CLOSE_CONFIRM":
      return { ...state, showBulkConfirm: false };
    case "DELETE_START":
      return { ...state, bulkDeleting: true };
    case "DELETE_DONE":
      return {
        ...state,
        bulkDeleting: false,
        selectedIds: new Set(),
        showBulkConfirm: false,
      };
  }
}

// ── Componente ────────────────────────────────────────────────────────────────

/**
 * Pestaña de documentos dentro del detalle de una colección.
 *
 * Lista los documentos de la colección con filtros por nombre y estado,
 * permite subir nuevos archivos (PDF o TXT), reintentar documentos
 * fallidos, eliminar documentos y ver su detalle. Gestiona el polling
 * automático de documentos en proceso.
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

  const [filters, dispatchFilters] = useReducer(filtersReducer, {
    filename: "",
    status: "",
    order: "desc",
    page: 1,
    pageSize: 10,
    totalPages: 0,
  });
  const { filename, status, order, page, pageSize, totalPages } = filters;

  const [upload, dispatchUpload] = useReducer(uploadReducer, {
    uploading: false,
    selectedFileName: "",
    uploadMsg: null,
    processingDocs: [],
    retrying: new Set<string>(),
  });

  const [detail, dispatchDetail] = useReducer(detailReducer, {
    selectedDocument: null,
    loadingDocumentDetail: false,
    documentContent: null,
    loadingContent: false,
  });

  const [bulk, dispatchBulk] = useReducer(bulkReducer, {
    selectedIds: new Set<string>(),
    bulkDeleting: false,
    showBulkConfirm: false,
  });

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
        dispatchFilters({
          type: "SET_TOTAL_PAGES",
          value: res.meta.total_pages,
        });
      } catch (e) {
        if (e instanceof ApiAbortError) return;
        setError(parseApiError(e, "Error al cargar documentos"));
      } finally {
        setLoading(false);
      }
    },
    [collectionId, filename, order, page, pageSize, status],
  );

  const deleteConfirm = useDeleteConfirm<Document>({
    onDelete: async (doc) => {
      await deleteDocument(collectionId, doc.id);
      dispatchBulk({ type: "REMOVE_ONE", id: doc.id });
      await fetchDocuments();
      onDocumentsMutated();
    },
    onError: (e) => setError(parseApiError(e, "Error al eliminar documento")),
  });

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
    if (upload.processingDocs.length === 0) return;
    const controller = new AbortController();
    const interval = setInterval(async () => {
      const justCompleted: string[] = [];
      const justFailed: string[] = [];
      await Promise.allSettled(
        upload.processingDocs.map(async (d) => {
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
      if (allDone.length === 0) return;

      const doneDocs = upload.processingDocs.filter((d) =>
        allDone.includes(d.id),
      );
      const failedDocs = doneDocs.filter((d) => justFailed.includes(d.id));
      const completedDocs = doneDocs.filter((d) =>
        justCompleted.includes(d.id),
      );

      const msg: UploadMsg =
        failedDocs.length > 0
          ? {
              type: "danger",
              text:
                failedDocs.length === 1
                  ? `Error al procesar "${failedDocs[0].filename}".`
                  : `Error al procesar ${failedDocs.length} documentos.`,
            }
          : {
              type: "success",
              text:
                completedDocs.length === 1
                  ? `"${completedDocs[0].filename}" procesado correctamente.`
                  : `${completedDocs.length} documentos procesados correctamente.`,
            };

      dispatchUpload({
        type: "PROCESSING_DONE",
        completedIds: justCompleted,
        failedIds: justFailed,
        msg,
      });
      fetchDocuments();
      onDocumentsMutated();
    }, 3000);
    return () => {
      clearInterval(interval);
      controller.abort();
    };
  }, [upload.processingDocs, collectionId, fetchDocuments, onDocumentsMutated]);

  const selectableDocs = documents.filter((d) => d.status !== "processing");
  const allSelectableSelected =
    selectableDocs.length > 0 &&
    selectableDocs.every((d) => bulk.selectedIds.has(d.id));

  function toggleSelectAll() {
    if (allSelectableSelected) {
      dispatchBulk({ type: "CLEAR" });
    } else {
      dispatchBulk({ type: "SET_ALL", ids: selectableDocs.map((d) => d.id) });
    }
  }

  async function handleBulkDelete() {
    dispatchBulk({ type: "DELETE_START" });
    try {
      await bulkDeleteDocuments(collectionId, [...bulk.selectedIds]);
      dispatchBulk({ type: "DELETE_DONE" });
      await fetchDocuments();
      onDocumentsMutated();
    } catch (e) {
      setError(
        parseApiError(e, "Error al eliminar los documentos seleccionados"),
      );
      dispatchBulk({ type: "DELETE_DONE" });
    }
  }

  async function handleRetry(doc: Document) {
    try {
      const retried = await retryDocument(collectionId, doc.id);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      dispatchUpload({ type: "RETRY_START", id: doc.id, movedDoc: retried });
    } catch (err) {
      setError(
        parseApiError(err, "Error al reintentar la ingestión del documento."),
      );
    } finally {
      dispatchUpload({ type: "RETRY_END", id: doc.id });
    }
  }

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    dispatchUpload({ type: "UPLOAD_START", filename: file.name });
    try {
      const uploaded = await uploadDocument(collectionId, file);
      dispatchUpload({
        type: "UPLOAD_SUCCESS",
        doc: uploaded,
        filename: file.name,
      });
      onDocumentsMutated();
    } catch (err) {
      const { variant, text } = parseApiError(err, "Error al subir");
      dispatchUpload({ type: "UPLOAD_ERROR", msg: { type: variant, text } });
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleOpenDocumentDetail(docId: string) {
    dispatchDetail({ type: "OPEN_START" });
    try {
      const doc = await getDocument(collectionId, docId);
      dispatchDetail({ type: "OPEN_SUCCESS", doc });
      if (doc.status === "completed") {
        dispatchDetail({ type: "CONTENT_LOADING" });
        try {
          const { raw_text } = await getDocumentContent(collectionId, docId);
          dispatchDetail({ type: "CONTENT_LOADED", content: raw_text });
        } catch {
          dispatchDetail({ type: "CONTENT_LOADED", content: null });
        }
      }
    } catch (e) {
      dispatchDetail({ type: "OPEN_ERROR" });
      setError(parseApiError(e, "Error al cargar el detalle del documento"));
    }
  }

  const allDocs = [...upload.processingDocs, ...documents];

  return (
    <>
      <Card className="mb-3">
        <Card.Body>
          <div className="d-flex gap-3 flex-wrap align-items-end">
            <Form.Group style={{ minWidth: 220 }}>
              <Form.Label>Buscar archivo</Form.Label>
              <Form.Control
                value={filename}
                onChange={(e) =>
                  dispatchFilters({
                    type: "SET_FILENAME",
                    value: e.target.value,
                  })
                }
                placeholder="Ej. worldbuilding.pdf"
              />
            </Form.Group>
            <Form.Group style={{ minWidth: 180 }}>
              <Form.Label>Estado</Form.Label>
              <Form.Select
                value={status}
                onChange={(e) =>
                  dispatchFilters({
                    type: "SET_STATUS",
                    value: e.target.value as "" | "completed" | "failed",
                  })
                }
              >
                <option value="">Todos</option>
                <option value="completed">Completado</option>
                <option value="failed">Error</option>
              </Form.Select>
            </Form.Group>
            <OrderSelect
              value={order}
              onChange={(o) => dispatchFilters({ type: "SET_ORDER", value: o })}
            />
            <PageSizeSelect
              value={pageSize}
              onChange={(size) =>
                dispatchFilters({ type: "SET_PAGE_SIZE", value: size })
              }
            />
          </div>
        </Card.Body>
      </Card>

      <div className="d-flex justify-content-between align-items-center mb-2">
        <div>
          {bulk.selectedIds.size > 0 && (
            <Button
              variant="danger"
              size="sm"
              onClick={() => dispatchBulk({ type: "OPEN_CONFIRM" })}
              disabled={bulk.bulkDeleting}
            >
              Eliminar seleccionados ({bulk.selectedIds.size})
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
            disabled={upload.uploading}
            className="d-none"
          />
          <Button
            type="button"
            variant="outline-secondary"
            className="lm-upload-trigger"
            onClick={() => fileInputRef.current?.click()}
            disabled={upload.uploading}
          >
            {upload.uploading ? "Subiendo..." : "↑ Seleccionar archivo"}
          </Button>
          <small className="text-muted">
            {upload.selectedFileName || "Ningún archivo seleccionado"}
          </small>
          {upload.uploading && (
            <Spinner
              animation="border"
              size="sm"
              className="lm-spinner-inline"
            />
          )}
        </div>
        {upload.uploadMsg && (
          <Alert
            variant={upload.uploadMsg.type}
            className="mt-2 mb-0 py-2"
            onClose={() => dispatchUpload({ type: "DISMISS_MSG" })}
            dismissible
          >
            {upload.uploadMsg.text}
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
                    checked={bulk.selectedIds.has(doc.id)}
                    onChange={() =>
                      dispatchBulk({ type: "TOGGLE_ONE", id: doc.id })
                    }
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
                      disabled={
                        upload.retrying.has(doc.id) || deleteConfirm.deleting
                      }
                    >
                      {upload.retrying.has(doc.id)
                        ? "Reintentando…"
                        : "Reintentar"}
                    </Button>
                  )}
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    className="me-2"
                    onClick={() => handleOpenDocumentDetail(doc.id)}
                    disabled={
                      detail.loadingDocumentDetail ||
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
        show={bulk.showBulkConfirm}
        title="Eliminar documentos seleccionados"
        message={`¿Eliminar ${bulk.selectedIds.size} documento${bulk.selectedIds.size !== 1 ? "s" : ""}? Se borrarán sus chunks del índice vectorial.`}
        onConfirm={handleBulkDelete}
        onCancel={() => dispatchBulk({ type: "CLOSE_CONFIRM" })}
        loading={bulk.bulkDeleting}
      />
      <Modal
        show={detail.selectedDocument !== null}
        onHide={() => dispatchDetail({ type: "CLOSE" })}
        centered
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>Detalle del documento</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {detail.selectedDocument && (
            <div className="d-flex flex-column gap-3">
              <div>
                <small className="text-muted">Nombre</small>
                <div style={{ wordBreak: "break-word" }}>
                  {detail.selectedDocument.filename}
                </div>
              </div>
              <div className="row g-3">
                <div className="col-auto">
                  <small className="text-muted d-block">Tipo</small>
                  <div>{detail.selectedDocument.file_type.toUpperCase()}</div>
                </div>
                <div className="col-auto">
                  <small className="text-muted d-block">Chunks</small>
                  <div>{detail.selectedDocument.chunk_count}</div>
                </div>
                <div className="col-auto">
                  <small className="text-muted d-block">Estado</small>
                  <div>{detail.selectedDocument.status}</div>
                </div>
                <div className="col-auto">
                  <small className="text-muted d-block">Creado</small>
                  <div>
                    {formatDate(detail.selectedDocument.created_at, true)}
                  </div>
                </div>
              </div>
              {detail.selectedDocument.processing_error && (
                <div>
                  <small className="text-muted">Error de procesamiento</small>
                  <div
                    className="text-danger mt-1"
                    style={{ fontSize: "0.875rem", wordBreak: "break-word" }}
                  >
                    {detail.selectedDocument.processing_error}
                  </div>
                </div>
              )}
              {detail.selectedDocument.status === "completed" && (
                <>
                  <hr style={{ borderColor: "var(--lm-border)", margin: 0 }} />
                  <div>
                    <small className="text-muted">Contenido extraído</small>
                    {detail.loadingContent ? (
                      <div className="mt-2 d-flex align-items-center gap-2 text-muted">
                        <Spinner animation="border" size="sm" />
                        <span>Cargando contenido…</span>
                      </div>
                    ) : detail.documentContent ? (
                      <pre className="lm-doc-content-pre">
                        {detail.documentContent}
                      </pre>
                    ) : (
                      <div
                        className="text-muted mt-1"
                        style={{ fontSize: "0.875rem" }}
                      >
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
        onPageChange={(p) => dispatchFilters({ type: "SET_PAGE", value: p })}
      />
    </>
  );
}
