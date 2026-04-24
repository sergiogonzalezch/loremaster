export type DocumentStatus = "processing" | "completed" | "failed";
export type EntityType =
  | "character"
  | "creature"
  | "location"
  | "faction"
  | "item";
export type ContentCategory =
  | "backstory"
  | "extended_description"
  | "scene"
  | "chapter";
export type ContentStatus = "pending" | "confirmed" | "discarded";
