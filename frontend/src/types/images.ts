// frontend/src/types/image.ts

export type ImageStatus = "pending" | "confirmed" | "discarded";
export type ImageBackend = "mock" | "local" | "runpod";
export type PromptSource = "llm_extraction";
export type PromptStrategy = "llm_extraction";

export interface ImageRecord {
  id: string;
  generation_id: string;
  entity_id: string;
  collection_id: string;
  seed: number;
  storage_path: string | null;
  image_url: string | null;
  filename: string | null;
  extension: string;
  width: number;
  height: number;
  generation_ms: number;
  created_at: string;
  is_deleted: boolean;
  deleted_at: string | null;
}

export interface ImageGenerationItem {
  id: string;
  entity_id: string;
  collection_id: string;
  content_id: string | null;
  category: string;
  auto_prompt: string;
  final_prompt: string;
  prompt_source: string;
  batch_size: number;
  backend: string;
  width: number;
  height: number;
  created_at: string;
  is_deleted: boolean;
  images: ImageRecord[];
}

export interface ImageGenerationListResponse {
  generations: ImageGenerationItem[];
  total: number;
}

export interface GenerateImageRequest {
  content_id: string;
  final_prompt: string;
  batch_size: number;
}

export interface GenerateImagesResponse {
  generation_id: string;
  auto_prompt: string;
  final_prompt: string;
  prompt_source: string;
  prompt_source_label: string;
  batch_size: number;
  backend: string;
  images: {
    id: string;
    image_url: string | null;
    seed: number;
    width: number;
    height: number;
    generation_ms: number;
  }[];
}
