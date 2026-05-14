/**
 * Endpoint para listar modelos LLM disponibles en Ollama.
 */

import { apiGet } from "./factory";

/** Modelo LLM instalado localmente en Ollama. */
export interface ModelInfo {
  name: string;
  size: number;
  is_default: boolean;
}

/** Lista los modelos LLM instalados en Ollama. */
export function getModels(): Promise<ModelInfo[]> {
  return apiGet<ModelInfo[]>("/models");
}
