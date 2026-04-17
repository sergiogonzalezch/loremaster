import { EntityType } from "./enums";

export const ENTITY_TYPE_BADGE: Record<EntityType, string> = {
  [EntityType.Character]: "primary",
  [EntityType.Scene]: "success",
  [EntityType.Faction]: "warning",
  [EntityType.Item]: "info",
};