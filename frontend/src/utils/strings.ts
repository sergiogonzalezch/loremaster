/**
 * Utilidades para manipulación de cadenas de texto.
 */

/**
 * Aplica trim a todos los valores string de un objeto plano.
 *
 * Útil para limpiar inputs de formularios antes de enviarlos al backend.
 *
 * @param obj - Objeto cuyos valores string serán recortados
 * @returns Nuevo objeto con los mismos valores, strings recortados
 */
export function trimStringValues<T extends object>(obj: T): T {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => [
      k,
      typeof v === "string" ? v.trim() : v,
    ]),
  ) as T;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const ALLOWED_IMAGE_ORIGINS = [
  API_BASE_URL,
  "http://localhost:8000",
  "http://localhost:5173",
  "https://localhost:5173",
];

/**
 * Valida que una URL de imagen venga de un origen permitido.
 * Previene loading de imágenes desde orígenes no confiables.
 *
 * @param url - URL de la imagen a validar
 * @returns true si la URL es segura (origen permitido o ruta relativa)
 */
export function isImageUrlAllowed(url: string | null | undefined): boolean {
  if (!url) return false;

  const trimmed = url.trim();
  if (!trimmed) return false;

  if (trimmed.startsWith("/") || trimmed.startsWith("./")) {
    return true;
  }

  try {
    const parsed = new URL(trimmed, API_BASE_URL);
    return ALLOWED_IMAGE_ORIGINS.some(
      (origin) => parsed.origin === origin || parsed.origin === "http://localhost",
    );
  } catch {
    return false;
  }
}
