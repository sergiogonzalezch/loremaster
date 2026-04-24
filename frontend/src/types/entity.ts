import type { EntityType } from "../utils/enums";

export interface Entity {
  id: string;
  collection_id: string;
  type: EntityType;
  name: string;
  description: string;
  created_at: string;
  updated_at: string | null;
}

export interface CreateEntityRequest {
  type: EntityType;
  name: string;
  description: string;
}

export interface UpdateEntityRequest {
  type?: EntityType;
  name?: string;
  description?: string;
}

import type { PaginatedMeta } from "./content";

export interface EntityListResponse {
  data: Entity[];
  meta: PaginatedMeta;
}