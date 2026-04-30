import { ApiError } from "../api/apiClient";

export function getErrorMessage(
  error: unknown,
  fallback = "Error inesperado",
): string {
  if (error instanceof ApiError) {
    // ApiError.message ya es descriptivo (ver apiClient.ts)
    return error.message;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  return fallback;
}

export function parseApiError(
  error: unknown,
  fallback = "Error de conexión con el servidor.",
): { variant: "warning" | "danger"; text: string } {
  if (error instanceof ApiError) {
    // 4xx del cliente: warning — el usuario puede corregirlo
    if (error.status >= 400 && error.status < 500) {
      return { variant: "warning", text: error.message };
    }
    // 5xx del servidor: danger
    return { variant: "danger", text: error.message };
  }
  return { variant: "danger", text: fallback };
}
