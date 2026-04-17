export type DocumentStatus = 'processing' | 'completed' | 'failed'

export interface Document {
  id: number
  collection_id: number
  filename: string
  file_type: string
  chunk_count: number
  status: DocumentStatus
  created_at: string
}

export interface DocumentListResponse {
  data: Document[]
  count: number
}