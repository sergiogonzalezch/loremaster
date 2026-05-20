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

/**
 * Valida que una URL de imagen sea segura para renderizar.
 *
 * Implementa la protección L-9: validar origen de URLs de imágenes
 * para prevenir loading de recursos desde orígenes no confiables.
 *
 * Reglas de validación:
 * - Rutas relativas (./ o /): permitidas (mismo origin)
 * - Data URIs (data:image/...): permitidas (inline seguro)
 * - Blob URLs (blob:...): permitidas (generadas localmente)
 * - localhost / 127.0.0.1: permitidas (desarrollo)
 * - Mismo hostname que la página: permitido
 * - Cualquier otro origen: rechazado
 *
 * @param url - URL de la imagen a validar
 * @returns true si la URL es segura para renderizar
 */
export function isImageUrlAllowed(url: string | null | undefined): boolean {
  if (!url) return false;

  const trimmed = url.trim();
  if (!trimmed) return false;

  // Rutas relativas (servidas por el mismo origin)
  if (trimmed.startsWith("/") || trimmed.startsWith("./")) {
    return true;
  }

  // Data URIs (base64 inline)
  if (trimmed.startsWith("data:image/")) {
    return true;
  }

  // Blob URLs (generadas localmente)
  if (trimmed.startsWith("blob:")) {
    return true;
  }

  try {
    const parsed = new URL(trimmed);
    const hostname = parsed.hostname.toLowerCase();

    // Permitir localhost (desarrollo) y mismos dominios
    if (
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname.endsWith(".localhost") ||
      hostname === window.location.hostname
    ) {
      return true;
    }

    // DEBUG: en desarrollo, loguear URLs rechazadas
    if (import.meta.env.DEV) {
      console.warn(
        "[SafeImage] URL rechazada:",
        trimmed,
        "hostname:",
        hostname,
      );
    }

    return false;
  } catch {
    // Si no es una URL válida, rechazar
    return false;
  }
}
