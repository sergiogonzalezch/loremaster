import { apiGet } from "./factory";
import type { EntityType, ContentCategory } from "../utils/enums";

export function getEntityCategories(): Promise<
  Record<EntityType, ContentCategory[]>
> {
  return apiGet<Record<EntityType, ContentCategory[]>>("/entity-categories");
}

export interface AppLimits {
  max_pending_contents: number;
}

export function getLimits(): Promise<AppLimits> {
  return apiGet<AppLimits>("/limits");
}
