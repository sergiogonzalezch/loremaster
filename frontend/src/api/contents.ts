/**
 * Endpoints de contenido de entidades: generar, listar, confirmar, descartar, editar y compartir.
 */

import { apiGet, apiPost, apiPatch, apiDelete, buildQuery } from "./factory";
import type {
  EntityContent,
  GenerateContentRequest,
  PaginatedResponse,
  UpdateContentRequest,
} from "../types";
import type { ContentCategory } from "../utils/enums";
import type { Entity } from "../types";

/** Parámetros de query para listar contenidos. */
export interface ContentsQueryParams {
  category?: ContentCategory;
  status?: "active" | "pending" | "confirmed" | "discarded" | "all";
  page?: number;
  page_size?: number;
  order?: "asc" | "desc";
}

const base = (collectionId: string, entityId: string) =>
  `/collections/${collectionId}/entities/${entityId}`;

/** Genera contenido para una entidad en una categoría dada. */
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

/** Lista los contenidos de una entidad con filtros y paginación. */
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

/** Actualiza el texto de un contenido. */
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

/** Confirma un contenido (descarta automáticamente los pendientes de la misma categoría). */
export function confirmContent(
  collectionId: string,
  entityId: string,
  contentId: string,
): Promise<Entity> {
  return apiPost<Entity>(
    `${base(collectionId, entityId)}/contents/${contentId}/confirm`,
  );
}

/** Descarta un contenido (cambia su estado a discarded). */
export function discardContent(
  collectionId: string,
  entityId: string,
  contentId: string,
): Promise<EntityContent> {
  return apiPatch<EntityContent>(
    `${base(collectionId, entityId)}/contents/${contentId}/discard`,
  );
}

/** Elimina un contenido (soft-delete). */
export function deleteContent(
  collectionId: string,
  entityId: string,
  contentId: string,
): Promise<void> {
  return apiDelete<void>(
    `${base(collectionId, entityId)}/contents/${contentId}`,
  );
}

/** Cambia el estado de visibilidad pública (share) de un contenido. */
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
