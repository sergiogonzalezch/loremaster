import { apiFetch } from "./apiClient";
import type {
  Draft,
  DraftListResponse,
  GenerateDraftRequest,
  UpdateDraftContentRequest,
} from "../types";
import type { Entity } from "../types";

const base = (collectionId: string, entityId: string) =>
  `/collections/${collectionId}/entities/${entityId}`;

export function generateDraft(
  collectionId: string,
  entityId: string,
  data: GenerateDraftRequest,
  signal?: AbortSignal
): Promise<Draft> {
  return apiFetch<Draft>(`${base(collectionId, entityId)}/generate`, {
    method: "POST",
    body: JSON.stringify(data),
    signal,
  });
}

export function getDrafts(collectionId: string, entityId: string): Promise<DraftListResponse> {
  return apiFetch<DraftListResponse>(`${base(collectionId, entityId)}/drafts`);
}

export function updateDraftContent(
  collectionId: string,
  entityId: string,
  draftId: string,
  data: UpdateDraftContentRequest
): Promise<Draft> {
  return apiFetch<Draft>(`${base(collectionId, entityId)}/drafts/${draftId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function confirmDraft(
  collectionId: string,
  entityId: string,
  draftId: string
): Promise<Entity> {
  return apiFetch<Entity>(`${base(collectionId, entityId)}/drafts/${draftId}/confirm`, {
    method: "POST",
  });
}

export function discardDraft(
  collectionId: string,
  entityId: string,
  draftId: string
): Promise<Draft> {
  return apiFetch<Draft>(`${base(collectionId, entityId)}/drafts/${draftId}/discard`, {
    method: "PATCH",
  });
}

export function deleteDraft(
  collectionId: string,
  entityId: string,
  draftId: string
): Promise<void> {
  return apiFetch<void>(`${base(collectionId, entityId)}/drafts/${draftId}`, { method: "DELETE" });
}