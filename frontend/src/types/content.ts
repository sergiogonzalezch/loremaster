/**
 * Tipos TypeScript para contenidos de entidades y paginación.
 */

import type { ContentCategory, ContentStatus } from "../utils/enums";

/** Contenido generado para una entidad (backstory, scene, etc.). */
export interface EntityContent {
  id: string;
  entity_id: string;
  collection_id: string;
  generated_text_id: string;
  category: ContentCategory;
  content: string;
  raw_content: string | null;
  was_edited: boolean;
  query: string;
  sources_count: number;
  source_doc_ids: string[];
  token_count: number;
  model_used: string | null;
  status: ContentStatus;
  is_shared: boolean;
  created_at: string;
  confirmed_at: string | null;
  updated_at: string | null;
}

/** Payload para generar contenido. */
export interface GenerateContentRequest {
  query: string;
  model?: string;
}

/** Payload para actualizar contenido. */
export interface UpdateContentRequest {
  content: string;
}

/** Metadata de paginación para respuestas de listado. */
export interface PaginatedMeta {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** Respuesta paginada genérica. */
export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginatedMeta;
}
