import { apiFetch } from "./apiClient";
import type { ContentCategory, EntityType } from "../utils/enums";

export function getEntityCategories(): Promise<
  Record<EntityType, ContentCategory[]>
> {
  return apiFetch<Record<EntityType, ContentCategory[]>>("/entity-categories");
}
