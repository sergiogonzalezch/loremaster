import { apiGet, apiPost, apiPatch, apiDelete, buildQuery } from "./factory";
import type {
  EntityContent,
  GenerateContentRequest,
  PaginatedResponse,
  UpdateContentRequest,
} from "../types";
import type { ContentCategory } from "../utils/enums";
import type { Entity } from "../types";

export interface ContentsQueryParams {
  category?: ContentCategory;
  status?: "active" | "pending" | "confirmed" | "discarded" | "all";
  page?: number;
  page_size?: number;
  order?: "asc" | "desc";
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
  return apiPost<EntityContent>(
    `${base(collectionId, entityId)}/generate/${category}`,
    data,
    { signal },
  );
}

export function getContents(
  collectionId: string,
  entityId: string,
  params: ContentsQueryParams = {},
  signal?: AbortSignal,
): Promise<PaginatedResponse<EntityContent>> {
  return apiGet<PaginatedResponse<EntityContent>>(
    `${base(collectionId, entityId)}/contents${buildQuery({
      page: 1,
      page_size: 100,
      ...params,
    })}`,
    undefined,
    { signal },
  );
}

export function updateContent(
  collectionId: string,
  entityId: string,
  contentId: string,
  data: UpdateContentRequest,
): Promise<EntityContent> {
  return apiPatch<EntityContent>(
    `${base(collectionId, entityId)}/contents/${contentId}`,
    data,
  );
}

export function confirmContent(
  collectionId: string,
  entityId: string,
  contentId: string,
): Promise<Entity> {
  return apiPost<Entity>(
    `${base(collectionId, entityId)}/contents/${contentId}/confirm`,
  );
}

export function discardContent(
  collectionId: string,
  entityId: string,
  contentId: string,
): Promise<EntityContent> {
  return apiPatch<EntityContent>(
    `${base(collectionId, entityId)}/contents/${contentId}/discard`,
  );
}

export function deleteContent(
  collectionId: string,
  entityId: string,
  contentId: string,
): Promise<void> {
  return apiDelete<void>(
    `${base(collectionId, entityId)}/contents/${contentId}`,
  );
}

export function shareContent(
  collectionId: string,
  entityId: string,
  contentId: string,
  data: { shared: boolean },
): Promise<EntityContent> {
  return apiPatch<EntityContent>(
    `${base(collectionId, entityId)}/contents/${contentId}/share`,
    data,
  );
}
