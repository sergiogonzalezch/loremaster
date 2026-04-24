export interface Collection {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string | null;
}

export interface CreateCollectionRequest {
  name: string;
  description: string;
}

import type { PaginatedMeta } from "./content";

export interface CollectionListResponse {
  data: Collection[];
  meta: PaginatedMeta;
}
