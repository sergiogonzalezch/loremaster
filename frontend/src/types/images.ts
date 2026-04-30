// frontend/src/types/image.ts

export type ImageStatus = "pending" | "confirmed" | "discarded";
export type ImageBackend = "mock" | "local" | "runpod";
export type PromptSource =
  | "content_direct"
  | "content_sentences"
  | "description"
  | "name_only";
export type PromptStrategy = "direct" | "first_sentences" | "entity_only";

export interface GenerateImageResponse {
  id: string;
  entity_id: string;
  collection_id: string;
  content_id: string | null;
  category: string;

  // Prompt
  visual_prompt: string;
  prompt_token_count: number;
  prompt_source: PromptSource;
  prompt_strategy: PromptStrategy;
  truncated: boolean;

  // Imagen
  image_url: string;
  image_path: string | null;
  filename: string | null;
  extension: string;
  width: number;
  height: number;

  // Generación
  backend: ImageBackend;
  seed: number;
  generation_ms: number;

  // Estado
  status: ImageStatus;
  created_at: string;
  confirmed_at: string | null;
  updated_at: string | null;
}

export interface GenerateImageRequest {
  content_id: string;
}
