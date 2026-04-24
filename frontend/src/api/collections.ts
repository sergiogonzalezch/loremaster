import { apiFetch } from "./apiClient";
import type {
  Collection,
  CreateCollectionRequest,
  CollectionListResponse,
} from "../types";

export function getCollections(): Promise<CollectionListResponse> {
  return apiFetch<CollectionListResponse>("/collections/");
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
