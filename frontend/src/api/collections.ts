/**
 * Endpoints de colecciones: CRUD y listado paginado con filtros.
 */

import { apiGet, apiPost, apiPatch, apiDelete, buildQuery } from "./factory";
import type {
  Collection,
  CreateCollectionRequest,
  UpdateCollectionRequest,
  CollectionListResponse,
} from "../types";

/** Parámetros de query para listar colecciones. */
export interface CollectionsQueryParams {
  page?: number;
  page_size?: number;
  name?: string;
  created_after?: string;
  created_before?: string;
  order?: "asc" | "desc";
}

/** Lista las colecciones del usuario con paginación y filtros. */
export function getCollections(
  params: CollectionsQueryParams = {},
  signal?: AbortSignal,
): Promise<CollectionListResponse> {
  return apiGet<CollectionListResponse>(
    `/collections/${buildQuery(params)}`,
    undefined,
    { signal },
  );
}

/** Obtiene una colección por ID. */
export function getCollection(
  id: string,
  signal?: AbortSignal,
): Promise<Collection> {
  return apiGet<Collection>(`/collections/${id}`, undefined, { signal });
}

/** Crea una nueva colección. */
export function createCollection(
  data: CreateCollectionRequest,
): Promise<Collection> {
  return apiPost<Collection>("/collections/", data);
}

/** Actualiza una colección existente. */
export function updateCollection(
  id: string,
  data: UpdateCollectionRequest,
): Promise<Collection> {
  return apiPatch<Collection>(`/collections/${id}`, data);
}

/** Elimina una colección (soft-delete en cascada). */
export function deleteCollection(id: string): Promise<void> {
  return apiDelete<void>(`/collections/${id}`);
}
