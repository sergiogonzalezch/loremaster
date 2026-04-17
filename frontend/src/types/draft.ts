export type DraftStatus = 'pending' | 'confirmed' | 'discarded'

export interface Draft {
  id: number
  entity_id: number
  collection_id: number
  query: string
  content: string
  sources_count: number
  status: DraftStatus
  created_at: string
  confirmed_at: string | null
}

export interface GenerateDraftRequest {
  query: string
}

export interface UpdateDraftContentRequest {
  content: string
}

export interface DraftListResponse {
  data: Draft[]
  count: number
}