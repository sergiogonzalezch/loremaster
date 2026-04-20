import type { EntityType } from "./enums";

export const ENTITY_TYPE_BADGE: Record<EntityType, string> = {
  character: "primary",
  scene: "success",
  faction: "warning",
  item: "info",
};

export const MAX_PENDING_DRAFTS = 5;
export const MIN_QUERY_LENGTH = 5;
export const MAX_GENERATION_TOKENS = 2000;
