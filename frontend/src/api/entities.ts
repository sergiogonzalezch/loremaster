/**
 * Endpoints de entidades: CRUD y listado paginado con filtros.
 */

import { apiGet, apiPost, apiPatch, apiDelete, buildQuery } from "./factory";
import type {
  Entity,
  EntityListResponse,
  CreateEntityRequest,
  UpdateEntityRequest,
} from "../types";
import type { EntityType } from "../utils/enums";

/** Parámetros de query para listar entidades. */
export interface EntitiesQueryParams {
  page?: number;
  page_size?: number;
  name?: string;
  type?: EntityType;
  created_after?: string;
  created_before?: string;
  order?: "asc" | "desc";
}

/** Lista las entidades de una colección con paginación y filtros. */
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

/** Obtiene una entidad por ID dentro de una colección. */
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

/** Crea una nueva entidad en una colección. */
export function createEntity(
  collectionId: string,
  data: CreateEntityRequest,
): Promise<Entity> {
  return apiPost<Entity>(`/collections/${collectionId}/entities`, data);
}

/** Actualiza una entidad existente. */
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

/** Elimina una entidad de una colección. */
export function deleteEntity(
  collectionId: string,
  entityId: string,
): Promise<void> {
  return apiDelete<void>(`/collections/${collectionId}/entities/${entityId}`);
}
