export interface GenerateImageResponse {
  image_url: string;
  visual_prompt: string;
  token_count: number;
  truncated: boolean;
  prompt_source: "content" | "description" | "name_only";
  seed: number;
  backend: "mock" | "local" | "runpod";
  generation_ms: number;
  entity_id: string;
  collection_id: string;
  content_id: string | null;
}