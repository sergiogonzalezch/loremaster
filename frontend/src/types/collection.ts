/**
 * Tipos TypeScript para colecciones (espejo del backend).
 */

/** Colección de worldbuilding del usuario. */
export interface Collection {
  id: string;
  name: string;
  description: string;
  owner_id: string | null;
  created_at: string;
  updated_at: string | null;
  document_count: number;
  entity_count: number;
}

/** Payload para crear una colección. */
export interface CreateCollectionRequest {
  name: string;
  description: string;
}

/** Payload para actualizar una colección (todos los campos opcionales). */
export interface UpdateCollectionRequest {
  name?: string;
  description?: string;
}

import type { PaginatedMeta } from "./content";

/** Respuesta paginada de colecciones. */
export interface CollectionListResponse {
  data: Collection[];
  meta: PaginatedMeta;
}
