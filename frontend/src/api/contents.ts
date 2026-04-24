import { apiFetch } from "./apiClient";
import type {
  EntityContent,
  GenerateContentRequest,
  PaginatedResponse,
  UpdateContentRequest,
} from "../types";
import type { ContentCategory } from "../utils/enums";
import type { Entity } from "../types";
import { buildQuery } from "./query";

export interface ContentsQueryParams {
  category?: ContentCategory;
  page?: number;
  page_size?: number;
}

const base = (collectionId: string, entityId: string) =>
  `/collections/${collectionId}/entities/${entityId}`;

export function generateContent(
  collectionId: string,
  entityId: string,
  category: ContentCategory,
  data: GenerateContentRequest,
  signal?: AbortSignal,
): Promise<EntityContent> {
  return apiFetch<EntityContent>(
    `${base(collectionId, entityId)}/generate/${category}`,
    {
      method: "POST",
      body: JSON.stringify(data),
      signal,
    },
  );
}

export function getContents(
  collectionId: string,
  entityId: string,
  params: ContentsQueryParams = {},
  signal?: AbortSignal,
): Promise<PaginatedResponse<EntityContent>> {
  return apiFetch<PaginatedResponse<EntityContent>>(
    `${base(collectionId, entityId)}/contents${buildQuery({
      page: 1,
      page_size: 100,
      ...params,
    })}`,
    { signal },
  );
}

export function updateContent(
  collectionId: string,
  entityId: string,
  contentId: string,
  data: UpdateContentRequest,
): Promise<EntityContent> {
  return apiFetch<EntityContent>(
    `${base(collectionId, entityId)}/contents/${contentId}`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    },
  );
}

export function confirmContent(
  collectionId: string,
  entityId: string,
  contentId: string,
): Promise<Entity> {
  return apiFetch<Entity>(
    `${base(collectionId, entityId)}/contents/${contentId}/confirm`,
    {
      method: "POST",
    },
  );
}

export function discardContent(
  collectionId: string,
  entityId: string,
  contentId: string,
): Promise<EntityContent> {
  return apiFetch<EntityContent>(
    `${base(collectionId, entityId)}/contents/${contentId}/discard`,
    {
      method: "PATCH",
    },
  );
}

export function deleteContent(
  collectionId: string,
  entityId: string,
  contentId: string,
): Promise<void> {
  return apiFetch<void>(
    `${base(collectionId, entityId)}/contents/${contentId}`,
    {
      method: "DELETE",
    },
  );
}
