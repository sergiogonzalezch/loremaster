import { apiFetch } from "./apiClient";
import { buildQuery } from "./query";
import type {
  Collection,
  CreateCollectionRequest,
  CollectionListResponse,
} from "../types";

export interface CollectionsQueryParams {
  page?: number;
  page_size?: number;
  name?: string;
  created_after?: string;
  created_before?: string;
}

export function getCollections(
  params: CollectionsQueryParams = {},
  signal?: AbortSignal,
): Promise<CollectionListResponse> {
  return apiFetch<CollectionListResponse>(
    `/collections/${buildQuery({ ...params })}`,
    { signal },
  );
}

export function getCollection(
  id: string,
  signal?: AbortSignal,
): Promise<Collection> {
  return apiFetch<Collection>(`/collections/${id}`, { signal });
}

export function createCollection(
  data: CreateCollectionRequest,
): Promise<Collection> {
  return apiFetch<Collection>("/collections/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function deleteCollection(id: string): Promise<void> {
  return apiFetch<void>(`/collections/${id}`, { method: "DELETE" });
}
