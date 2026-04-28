import type { ContentCategory, EntityType } from "./enums";

export const ENTITY_TYPE_BADGE: Record<EntityType, string> = {
  character: "primary",
  creature: "info",
  location: "success",
  faction: "warning",
  item: "secondary",
};

export const ENTITY_TYPE_LABELS: Record<EntityType, string> = {
  character: "Personaje",
  creature: "Criatura",
  location: "Lugar",
  faction: "Facción",
  item: "Objeto",
};

export const ENTITY_CATEGORY_MAP: Record<EntityType, ContentCategory[]> = {
  character: ["backstory", "extended_description", "scene", "chapter"],
  creature: ["backstory", "extended_description", "scene"],
  location: ["extended_description", "scene"],
  faction: ["backstory", "extended_description", "scene"],
  item: ["backstory", "extended_description"],
};

export const CATEGORY_LABELS: Record<ContentCategory, string> = {
  backstory: "Trasfondo",
  extended_description: "Descripción extendida",
  scene: "Escena",
  chapter: "Capítulo",
};

export const MIN_QUERY_LENGTH = 5;
export const MAX_GENERATION_TOKENS = 2000;
