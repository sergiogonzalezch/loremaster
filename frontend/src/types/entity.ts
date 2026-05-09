/**
 * Tipos TypeScript para entidades (espejo del backend).
 */

import type { EntityType } from "../utils/enums";

/** Entidad dentro de una colección (personaje, criatura, lugar, etc.). */
export interface Entity {
  id: string;
  collection_id: string;
  type: EntityType;
  name: string;
  description: string;
  created_at: string;
  updated_at: string | null;
}

/** Payload para crear una entidad. */
export interface CreateEntityRequest {
  type: EntityType;
  name: string;
  description: string;
}

/** Payload para actualizar una entidad. */
export interface UpdateEntityRequest {
  type?: EntityType;
  name?: string;
  description?: string;
}

import type { PaginatedMeta } from "./content";

/** Respuesta paginada de entidades. */
export interface EntityListResponse {
  data: Entity[];
  meta: PaginatedMeta;
}
