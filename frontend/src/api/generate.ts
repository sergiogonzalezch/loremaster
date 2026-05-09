/**
 * Endpoint de consultas RAG generales sobre una colección.
 */

import { apiPost } from "./factory";
import type { GenerateTextRequest, GenerateTextResponse } from "../types";

/** Ejecuta una consulta RAG sobre los documentos de una colección. */
export function generateText(
  collectionId: string,
  data: GenerateTextRequest,
  signal?: AbortSignal,
): Promise<GenerateTextResponse> {
  return apiPost<GenerateTextResponse>(
    `/collections/${collectionId}/query`,
    data,
    {
      signal,
    },
  );
}
