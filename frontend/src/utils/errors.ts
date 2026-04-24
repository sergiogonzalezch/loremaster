import { ApiError } from "../api/apiClient";

export function getErrorMessage(
  error: unknown,
  fallback = "Error inesperado",
): string {
  return error instanceof Error ? error.message : fallback;
}

export function parseApiError(
  error: unknown,
  fallback = "Error de conexión con el servidor.",
): { variant: "warning" | "danger"; text: string } {
  if (error instanceof ApiError) {
    if ([400, 404, 409, 422].includes(error.status)) {
      return { variant: "warning", text: error.message };
    }
    if (error.status === 503) {
      return {
        variant: "danger",
        text: "El servicio de generación no está disponible. Inténtalo de nuevo más tarde.",
      };
    }
    return { variant: "danger", text: error.message };
  }
  return { variant: "danger", text: fallback };
}
