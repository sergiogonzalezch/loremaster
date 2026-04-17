import type { DraftStatus } from "../utils/enums";

export interface Draft {
  id: string;
  entity_id: string;
  collection_id: string;
  query: string;
  content: string;
  sources_count: number;
  status: DraftStatus;
  created_at: string;
  confirmed_at: string | null;
}

export interface GenerateDraftRequest {
  query: string;
}

export interface UpdateDraftContentRequest {
  content: string;
}

export interface DraftListResponse {
  data: Draft[];
  count: number;
}