import { apiFetch } from "./apiClient";
import { apiGet, apiPost, apiDelete, buildQuery } from "./factory";
import type { Document, DocumentListResponse } from "../types";
import type { DocumentStatus } from "../utils/enums";

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

export function retryDocument(
  collectionId: string,
  docId: string,
): Promise<Document> {
  return apiPost<Document>(
    `/collections/${collectionId}/documents/${docId}/retry`,
  );
}

export function deleteDocument(
  collectionId: string,
  docId: string,
): Promise<void> {
  return apiDelete<void>(`/collections/${collectionId}/documents/${docId}`);
}
