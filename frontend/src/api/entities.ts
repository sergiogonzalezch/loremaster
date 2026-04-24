import { apiFetch } from "./apiClient";
import { buildQuery } from "./query";
import type {
  Entity,
  EntityListResponse,
  CreateEntityRequest,
  UpdateEntityRequest,
} from "../types";
import type { EntityType } from "../utils/enums";

export interface EntitiesQueryParams {
  page?: number;
  page_size?: number;
  name?: string;
  type?: EntityType;
  created_after?: string;
  created_before?: string;
  order?: "asc" | "desc";
}

export function getEntities(
  collectionId: string,
  params: EntitiesQueryParams = {},
  signal?: AbortSignal,
): Promise<EntityListResponse> {
  return apiFetch<EntityListResponse>(
    `/collections/${collectionId}/entities${buildQuery({ ...params })}`,
    { signal },
  );
}

export function getEntity(
  collectionId: string,
  entityId: string,
  signal?: AbortSignal,
): Promise<Entity> {
  return apiFetch<Entity>(`/collections/${collectionId}/entities/${entityId}`, {
    signal,
  });
}

export function createEntity(
  collectionId: string,
  data: CreateEntityRequest,
): Promise<Entity> {
  return apiFetch<Entity>(`/collections/${collectionId}/entities`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateEntity(
  collectionId: string,
  entityId: string,
  data: UpdateEntityRequest,
): Promise<Entity> {
  return apiFetch<Entity>(`/collections/${collectionId}/entities/${entityId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteEntity(
  collectionId: string,
  entityId: string,
): Promise<void> {
  return apiFetch<void>(`/collections/${collectionId}/entities/${entityId}`, {
    method: "DELETE",
  });
}
