import { ApiError } from "../api/apiClient";

export function getErrorMessage(error: unknown, fallback = "Error inesperado"): string {
  return error instanceof Error ? error.message : fallback;
}

export function parseApiError(error: unknown): { variant: "warning" | "danger"; text: string } {
  if (error instanceof ApiError) {
    if (error.status === 400 && error.message === "No context available") {
      return { variant: "warning", text: "No hay documentos en esta colección. Sube documentos primero." };
    }
    if (error.status === 422) {
      return { variant: "danger", text: "La consulta no cumple los requisitos mínimos." };
    }
    if (error.status === 503) {
      return { variant: "danger", text: "El servicio de generación no está disponible." };
    }
    return { variant: "danger", text: error.message };
  }
  return { variant: "danger", text: "Error de conexión con el servidor." };
}
