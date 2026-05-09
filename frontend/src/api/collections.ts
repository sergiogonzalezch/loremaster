import { apiGet, apiPost, apiPatch, apiDelete, buildQuery } from "./factory";
import type {
  Collection,
  CreateCollectionRequest,
  UpdateCollectionRequest,
  CollectionListResponse,
} from "../types";

export interface CollectionsQueryParams {
  page?: number;
  page_size?: number;
  name?: string;
  created_after?: string;
  created_before?: string;
  order?: "asc" | "desc";
}

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

export function getCollection(
  id: string,
  signal?: AbortSignal,
): Promise<Collection> {
  return apiGet<Collection>(`/collections/${id}`, undefined, { signal });
}

export function createCollection(
  data: CreateCollectionRequest,
): Promise<Collection> {
  return apiPost<Collection>("/collections/", data);
}

export function updateCollection(
  id: string,
  data: UpdateCollectionRequest,
): Promise<Collection> {
  return apiPatch<Collection>(`/collections/${id}`, data);
}

export function deleteCollection(id: string): Promise<void> {
  return apiDelete<void>(`/collections/${id}`);
}
