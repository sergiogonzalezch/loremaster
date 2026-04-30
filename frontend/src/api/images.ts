// frontend/src/api/images.ts

import { apiFetch } from "./apiClient";
import type { GenerateImageResponse, GenerateImageRequest } from "../types";

export function generateImage(
  collectionId: string,
  entityId: string,
  data: GenerateImageRequest,
  signal?: AbortSignal,
): Promise<GenerateImageResponse> {
  return apiFetch<GenerateImageResponse>(
    `/collections/${collectionId}/entities/${entityId}/generate/image`,
    {
      method: "POST",
      body: JSON.stringify(data),
      signal,
    },
  );
}
