import { apiFetch, apiUpload } from "./apiClient";
import type { Document, DocumentListResponse } from "../types";

export function uploadDocument(collectionId: string, file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  return apiUpload<Document>(`/collections/${collectionId}/documents`, formData);
}

export function getDocuments(collectionId: string): Promise<DocumentListResponse> {
  return apiFetch<DocumentListResponse>(`/collections/${collectionId}/documents`);
}

export function deleteDocument(collectionId: string, docId: string): Promise<void> {
  return apiFetch<void>(`/collections/${collectionId}/documents/${docId}`, { method: "DELETE" });
}