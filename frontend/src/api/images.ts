/**
 * Endpoints de generación de imágenes: build-prompt, generate, listar, eliminar y compartir.
 */

import { apiGet, apiPost, apiPatch, apiDelete } from "./factory";
import type {
  GenerateImageRequest,
  GenerateImagesResponse,
  ImageGenerationListResponse,
  ImageRecord,
} from "../types";

/** Construye el prompt visual automático para una imagen a partir de un contenido confirmado. */
export function buildPrompt(
  collectionId: string,
  entityId: string,
  contentId: string,
  signal?: AbortSignal,
) {
  return apiPost<{
    auto_prompt: string;
    token_count: number;
  }>(
    `/collections/${collectionId}/entities/${entityId}/image-generation/build-prompt`,
    { content_id: contentId },
    { signal },
  );
}

/** Genera un batch de imágenes para una entidad usando el prompt construido. */
export function generateImages(
  collectionId: string,
  entityId: string,
  data: GenerateImageRequest,
  signal?: AbortSignal,
): Promise<GenerateImagesResponse> {
  return apiPost<GenerateImagesResponse>(
    `/collections/${collectionId}/entities/${entityId}/image-generation/generate`,
    data,
    { signal },
  );
}

/** Lista las generaciones de imágenes de una entidad. */
export function listImageGenerations(
  collectionId: string,
  entityId: string,
  signal?: AbortSignal,
): Promise<ImageGenerationListResponse> {
  return apiGet<ImageGenerationListResponse>(
    `/collections/${collectionId}/entities/${entityId}/image-generation`,
    undefined,
    { signal },
  );
}

/** Elimina una imagen específica de una generación. */
export function deleteImage(
  collectionId: string,
  entityId: string,
  generationId: string,
  imageId: string,
  signal?: AbortSignal,
) {
  return apiDelete(
    `/collections/${collectionId}/entities/${entityId}/image-generation/${generationId}/images/${imageId}`,
    { signal },
  );
}

/** Cambia el estado de visibilidad pública de una imagen. */
export function shareImage(
  collectionId: string,
  entityId: string,
  generationId: string,
  imageId: string,
  data: { shared: boolean },
): Promise<ImageRecord> {
  return apiPatch<ImageRecord>(
    `/collections/${collectionId}/entities/${entityId}/image-generation/${generationId}/images/${imageId}/share`,
    data,
  );
}
