import { apiFetch } from "./apiClient";
import type { Document, DocumentListResponse } from "../types";

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
  signal?: AbortSignal,
): Promise<DocumentListResponse> {
  return apiFetch<DocumentListResponse>(
    `/collections/${collectionId}/documents`,
    { signal },
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
