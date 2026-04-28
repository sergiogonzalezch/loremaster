import { apiFetch } from "./apiClient";
import type { ContentCategory, EntityType } from "../utils/enums";

export function getEntityCategories(): Promise<
  Record<EntityType, ContentCategory[]>
> {
  return apiFetch<Record<EntityType, ContentCategory[]>>("/entity-categories");
}

export interface AppLimits {
  max_pending_contents: number;
}

export function getLimits(): Promise<AppLimits> {
  return apiFetch<AppLimits>("/limits");
}
