import { apiPost } from "./factory";
import type { GenerateTextRequest, GenerateTextResponse } from "../types";

export function generateText(
  collectionId: string,
  data: GenerateTextRequest,
  signal?: AbortSignal,
): Promise<GenerateTextResponse> {
  return apiPost<GenerateTextResponse>(`/collections/${collectionId}/query`, data, {
    signal,
  });
}
