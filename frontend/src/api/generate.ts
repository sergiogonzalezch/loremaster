import { apiFetch } from "./apiClient";
import type { GenerateTextRequest, GenerateTextResponse } from "../types";

export function generateText(
  collectionId: string,
  data: GenerateTextRequest,
  signal?: AbortSignal
): Promise<GenerateTextResponse> {
  return apiFetch<GenerateTextResponse>(`/collections/${collectionId}/query`, {
    method: "POST",
    body: JSON.stringify(data),
    signal,
  });
}