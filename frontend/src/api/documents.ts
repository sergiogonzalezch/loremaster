import { apiFetch } from "./apiClient";
import { buildQuery } from "./query";
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
  return apiFetch<DocumentListResponse>(
    `/collections/${collectionId}/documents${buildQuery({ ...params })}`,
    { signal },
  );
}

export function getDocument(
  collectionId: string,
  docId: string,
  signal?: AbortSignal,
): Promise<Document> {
  return apiFetch<Document>(`/collections/${collectionId}/documents/${docId}`, {
    signal,
  });
}

export function retryDocument(
  collectionId: string,
  docId: string,
): Promise<Document> {
  return apiFetch<Document>(
    `/collections/${collectionId}/documents/${docId}/retry`,
    { method: "POST" },
  );
}

export function deleteDocument(
  collectionId: string,
  docId: string,
): Promise<void> {
  return apiFetch<void>(`/collections/${collectionId}/documents/${docId}`, {
    method: "DELETE",
  });
}
