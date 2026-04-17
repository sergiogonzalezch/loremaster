export interface Collection {
  id: number
  name: string
  description: string
  created_at: string
  updated_at: string | null
}

export interface CreateCollectionRequest {
  name: string
  description: string
}

export interface CollectionListResponse {
  data: Collection[]
  count: number
}