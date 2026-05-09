import { apiGet, apiPost, apiPatch, apiDelete, buildQuery } from "./factory";
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
  return apiGet<EntityListResponse>(
    `/collections/${collectionId}/entities${buildQuery(params)}`,
    undefined,
    { signal },
  );
}

export function getEntity(
  collectionId: string,
  entityId: string,
  signal?: AbortSignal,
): Promise<Entity> {
  return apiGet<Entity>(
    `/collections/${collectionId}/entities/${entityId}`,
    undefined,
    { signal },
  );
}

export function createEntity(
  collectionId: string,
  data: CreateEntityRequest,
): Promise<Entity> {
  return apiPost<Entity>(`/collections/${collectionId}/entities`, data);
}

export function updateEntity(
  collectionId: string,
  entityId: string,
  data: UpdateEntityRequest,
): Promise<Entity> {
  return apiPatch<Entity>(
    `/collections/${collectionId}/entities/${entityId}`,
    data,
  );
}

export function deleteEntity(
  collectionId: string,
  entityId: string,
): Promise<void> {
  return apiDelete<void>(`/collections/${collectionId}/entities/${entityId}`);
}
