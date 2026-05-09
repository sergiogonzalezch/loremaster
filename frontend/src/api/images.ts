import { apiGet, apiPost, apiPatch, apiDelete } from "./factory";
import type {
  GenerateImageRequest,
  GenerateImagesResponse,
  ImageGenerationListResponse,
  ImageRecord,
} from "../types";

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
