// frontend/src/api/images.ts

import { apiFetch } from "./apiClient";
import type {
  GenerateImageRequest,
  GenerateImagesResponse,
  ImageGenerationListResponse,
} from "../types";

export function buildPrompt(
  collectionId: string,
  entityId: string,
  contentId: string,
  signal?: AbortSignal,
) {
  return apiFetch<{
    auto_prompt: string;
    token_count: number;
  }>(
    `/collections/${collectionId}/entities/${entityId}/image-generation/build-prompt`,
    {
      method: "POST",
      body: JSON.stringify({ content_id: contentId }),
      signal,
    },
  );
}

export function generateImages(
  collectionId: string,
  entityId: string,
  data: GenerateImageRequest,
  signal?: AbortSignal,
): Promise<GenerateImagesResponse> {
  return apiFetch<GenerateImagesResponse>(
    `/collections/${collectionId}/entities/${entityId}/image-generation/generate`,
    {
      method: "POST",
      body: JSON.stringify(data),
      signal,
    },
  );
}

export function listImageGenerations(
  collectionId: string,
  entityId: string,
  signal?: AbortSignal,
): Promise<ImageGenerationListResponse> {
  return apiFetch<ImageGenerationListResponse>(
    `/collections/${collectionId}/entities/${entityId}/image-generation`,
    { method: "GET", signal },
  );
}

export function deleteImage(
  collectionId: string,
  entityId: string,
  generationId: string,
  imageId: string,
  signal?: AbortSignal,
) {
  return apiFetch(
    `/collections/${collectionId}/entities/${entityId}/image-generation/${generationId}/images/${imageId}`,
    { method: "DELETE", signal },
  );
}
