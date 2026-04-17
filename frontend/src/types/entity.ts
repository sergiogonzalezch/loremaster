export type EntityType = 'character' | 'scene' | 'faction' | 'item'

export interface Entity {
  id: number
  collection_id: number
  type: EntityType
  name: string
  description: string
  created_at: string
  updated_at: string | null
}

export interface CreateEntityRequest {
  type: EntityType
  name: string
  description: string
}

export type UpdateEntityRequest = CreateEntityRequest

export interface EntityListResponse {
  data: Entity[]
  count: number
}