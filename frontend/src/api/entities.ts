import { apiFetch } from "./apiClient";
import type {
  Entity,
  EntityListResponse,
  CreateEntityRequest,
  UpdateEntityRequest,
} from "../types";

export function getEntities(collectionId: string): Promise<EntityListResponse> {
  return apiFetch<EntityListResponse>(`/collections/${collectionId}/entities`);
}

export function getEntity(collectionId: string, entityId: string): Promise<Entity> {
  return apiFetch<Entity>(`/collections/${collectionId}/entities/${entityId}`);
}

export function createEntity(collectionId: string, data: CreateEntityRequest): Promise<Entity> {
  return apiFetch<Entity>(`/collections/${collectionId}/entities`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateEntity(
  collectionId: string,
  entityId: string,
  data: UpdateEntityRequest
): Promise<Entity> {
  return apiFetch<Entity>(`/collections/${collectionId}/entities/${entityId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteEntity(collectionId: string, entityId: string): Promise<void> {
  return apiFetch<void>(`/collections/${collectionId}/entities/${entityId}`, { method: "DELETE" });
}