import type { EntityType } from "./enums";

export const ENTITY_TYPE_BADGE: Record<EntityType, string> = {
  character: "primary",
  scene: "success",
  faction: "warning",
  item: "info",
};
