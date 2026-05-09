/**
 * Tipos TypeScript para consultas RAG generales.
 */

/** Payload para consulta RAG sobre una colección. */
export interface GenerateTextRequest {
  query: string;
}

/** Respuesta de una consulta RAG. */
export interface GenerateTextResponse {
  answer: string;
  query: string;
  sources_count: number;
}
