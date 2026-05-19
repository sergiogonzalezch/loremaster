/**
 * Tipos TypeScript para documentos (espejo del backend).
 */

import type { DocumentStatus } from "../utils/enums";
import type { PaginatedMeta } from "./content";

/** Documento ingestado en una colección. */
export interface Document {
  id: string;
  collection_id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
  status: DocumentStatus;
  processing_error?: string | null;
  created_at: string;
}

/** Respuesta paginada de documentos. */
export interface DocumentListResponse {
  data: Document[];
  meta: PaginatedMeta;
}

/** Contenido extraído de un documento completado. */
export interface DocumentContent {
  id: string;
  filename: string;
  raw_text: string | null;
}
