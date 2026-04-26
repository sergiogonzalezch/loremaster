import type { ContentCategory, ContentStatus } from "../utils/enums";

export interface EntityContent {
  id: string;
  entity_id: string;
  collection_id: string;
  query: string;
  sources_count: number;
  token_count: number;
  category: ContentCategory;
  content: string;
  status: ContentStatus;
  created_at: string;
  confirmed_at: string | null;
  updated_at: string | null;
}

export interface GenerateContentRequest {
  query: string;
}

export interface UpdateContentRequest {
  content: string;
}

export interface PaginatedMeta {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginatedMeta;
}
