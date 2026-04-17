import { apiFetch } from "./apiClient";
import type { GenerateTextRequest, GenerateTextResponse } from "../types";

export function generateText(
  collectionId: string,
  data: GenerateTextRequest
): Promise<GenerateTextResponse> {
  return apiFetch<GenerateTextResponse>(`/collections/${collectionId}/generate/text`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}