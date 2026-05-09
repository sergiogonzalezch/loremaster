/**
 * Tipos enumerados del dominio, espejo de los enums del backend.
 */

/** Estado de procesamiento de un documento. */
export type DocumentStatus = "processing" | "completed" | "failed";

/** Tipos de entidad soportados. */
export type EntityType =
  | "character"
  | "creature"
  | "location"
  | "faction"
  | "item";

/** Categorías de contenido generable para entidades. */
export type ContentCategory =
  | "backstory"
  | "extended_description"
  | "scene"
  | "chapter";

/** Estados posibles de un contenido generado. */
export type ContentStatus = "pending" | "confirmed" | "discarded";
