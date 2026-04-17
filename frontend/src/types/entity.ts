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

export type UpdateEntityRequest = CreateEntityRequest;

export interface EntityListResponse {
  data: Entity[];
  count: number;
}