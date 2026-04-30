import { apiFetch } from "./apiClient";
import type { GenerateImageResponse } from "../types";

export interface GenerateImageRequest {
  content_id?: string;
}

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
