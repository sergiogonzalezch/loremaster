import type { DocumentStatus } from "../utils/enums";
import type { PaginatedMeta } from "./content";

export interface Document {
  id: string;
  collection_id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
  status: DocumentStatus;
  created_at: string;
}

export interface DocumentListResponse {
  data: Document[];
  meta: PaginatedMeta;
}
