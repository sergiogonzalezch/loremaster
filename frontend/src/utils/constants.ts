/**
 * Constantes de la aplicación: etiquetas, mapeos de categorías y límites.
 */

import type { ContentCategory, EntityType } from "./enums";

/** Variante Bootstrap Badge para cada tipo de entidad. */
export const ENTITY_TYPE_BADGE: Record<EntityType, string> = {
  character: "primary",
  creature: "info",
  location: "success",
  faction: "warning",
  item: "secondary",
};

/** Etiqueta legible para cada tipo de entidad. */
export const ENTITY_TYPE_LABELS: Record<EntityType, string> = {
  character: "Personaje",
  creature: "Criatura",
  location: "Lugar",
  faction: "Facción",
  item: "Objeto",
};

/** Mapeo de tipos de entidad a las categorías de contenido que soportan. */
export const ENTITY_CATEGORY_MAP: Record<EntityType, ContentCategory[]> = {
  character: ["backstory", "extended_description", "scene"],
  creature: ["backstory", "extended_description", "scene"],
  location: ["extended_description", "scene"],
  faction: ["backstory", "extended_description", "scene"],
  item: ["backstory", "extended_description"],
};

/** Etiqueta legible para cada categoría de contenido. */
export const CATEGORY_LABELS: Record<ContentCategory, string> = {
  backstory: "Trasfondo",
  extended_description: "Descripción extendida",
  scene: "Escena",
};
