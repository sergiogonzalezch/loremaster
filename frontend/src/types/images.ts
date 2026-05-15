/**
 * Tipos TypeScript para imágenes generadas (espejo del backend).
 */

/** Registro individual de una imagen generada. */
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
  is_shared: boolean;
  created_at: string;
  is_deleted: boolean;
  deleted_at: string | null;
}

/** Generación de imágenes (batch) con sus registros. */
export interface ImageGenerationItem {
  id: string;
  entity_id: string;
  collection_id: string;
  content_id: string | null;
  category: string;
  auto_prompt: string;
  final_prompt: string;
  batch_size: number;
  backend: string;
  width: number;
  height: number;
  created_at: string;
  is_deleted: boolean;
  images: ImageRecord[];
}

/** Respuesta de listado de generaciones de imágenes. */
export interface ImageGenerationListResponse {
  generations: ImageGenerationItem[];
  total: number;
}

/** Payload para generar imágenes. */
export interface GenerateImageRequest {
  content_id: string;
  auto_prompt: string;
  final_prompt: string;
  batch_size: number;
  seed_base?: number;
}

/** Respuesta tras generar imágenes. */
export interface GenerateImagesResponse {
  generation_id: string;
  auto_prompt: string;
  final_prompt: string;
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
