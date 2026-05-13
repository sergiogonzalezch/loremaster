/**
 * Endpoints de documentos: subida, listado, reintentar y eliminar.
 */

import { apiFetch } from "./apiClient";
import { apiGet, apiPost, apiDelete, buildQuery } from "./factory";
import type { Document, DocumentListResponse } from "../types";
import type { DocumentStatus } from "../utils/enums";

/** Parámetros de query para listar documentos. */
export interface DocumentsQueryParams {
  page?: number;
  page_size?: number;
  filename?: string;
  file_type?: string;
  status?: DocumentStatus;
  created_after?: string;
  created_before?: string;
  order?: "asc" | "desc";
}

/** Sube un archivo a una colección para ingestión. */
export function uploadDocument(
  collectionId: string,
  file: File,
): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<Document>(`/collections/${collectionId}/documents`, {
    method: "POST",
    body: formData,
  });
}

/** Lista los documentos de una colección con paginación y filtros. */
export function getDocuments(
  collectionId: string,
  params: DocumentsQueryParams = {},
  signal?: AbortSignal,
): Promise<DocumentListResponse> {
  return apiGet<DocumentListResponse>(
    `/collections/${collectionId}/documents${buildQuery(params)}`,
    undefined,
    { signal },
  );
}

/** Obtiene un documento específico de una colección. */
export function getDocument(
  collectionId: string,
  docId: string,
  signal?: AbortSignal,
): Promise<Document> {
  return apiGet<Document>(
    `/collections/${collectionId}/documents/${docId}`,
    undefined,
    { signal },
  );
}

/** Reintenta la ingestión de un documento fallido. */
export function retryDocument(
  collectionId: string,
  docId: string,
): Promise<Document> {
  return apiPost<Document>(
    `/collections/${collectionId}/documents/${docId}/retry`,
  );
}

/** Elimina un documento de una colección. */
export function deleteDocument(
  collectionId: string,
  docId: string,
): Promise<void> {
  return apiDelete<void>(`/collections/${collectionId}/documents/${docId}`);
}

/** Elimina múltiples documentos en cascada (máx. 100 IDs). */
export function bulkDeleteDocuments(
  collectionId: string,
  ids: string[],
): Promise<void> {
  return apiPost<void>(`/collections/${collectionId}/documents/bulk-delete`, {
    ids,
  });
}
