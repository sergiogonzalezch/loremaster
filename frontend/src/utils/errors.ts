/**
 * Utilidades para extraer mensajes de error de excepciones y formatearlos
 * para mostrar al usuario con el nivel de severidad adecuado.
 */

import { ApiError } from "../api/apiClient";

/**
 * Extrae un mensaje legible de cualquier error.
 *
 * Prioriza el mensaje de ApiError (ya procesado por apiClient.ts),
 * luego Error.message, y finalmente un mensaje por defecto.
 *
 * @param error - Error capturado (puede ser cualquier valor)
 * @param fallback - Mensaje por defecto si no se puede extraer ninguno
 * @returns Mensaje de error legible
 */
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

/**
 * Parsea un error en un objeto con variant Bootstrap y texto legible.
 *
 * Los errores 4xx se marcan como "warning" (el usuario puede corregirlos),
 * los errores 5xx y de red como "danger".
 *
 * @param error - Error capturado
 * @param fallback - Mensaje por defecto para errores no ApiError
 * @returns Objeto con la variante Bootstrap y el texto del mensaje
 */
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
