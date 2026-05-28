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
 * Hostnames adicionales permitidos para imágenes, leídos una vez al iniciar.
 *
 * Configúralo cuando el backend sirva imágenes desde un dominio externo
 * (S3, R2, Floci, CDN). Ejemplo en .env:
 *   VITE_MEDIA_HOST=pub-abc123.r2.dev,cdn.example.com
 */
const _EXTRA_MEDIA_HOSTNAMES: Set<string> = new Set(
  ((import.meta.env.VITE_MEDIA_HOST ?? "") as string)
    .split(",")
    .flatMap((h) => {
      const trimmed = h.trim().toLowerCase();
      return trimmed ? [trimmed] : [];
    }),
);

/**
 * Valida que una URL de imagen sea segura para renderizar.
 *
 * Implementa la protección L-9: validar origen de URLs de imágenes
 * para prevenir loading de recursos desde orígenes no confiables.
 *
 * Reglas de validación:
 * - Rutas relativas (./ o /): permitidas (mismo origin)
 * - Data URIs rasterizadas (jpeg/png/webp/gif base64): permitidas. SVG excluido (puede contener JS).
 * - Blob URLs (blob:...): permitidas (generadas localmente)
 * - localhost / 127.0.0.1: permitidas (desarrollo)
 * - Mismo hostname que la página: permitido
 * - Hostnames extra definidos en VITE_MEDIA_HOST: permitidos (CDN/S3)
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

  // Data URIs — solo tipos rasterizados seguros; SVG se excluye porque puede
  // contener JS ejecutable (e.g. <svg onload=alert(1)>).
  if (/^data:image\/(jpeg|jpg|png|webp|gif);base64,/.test(trimmed)) {
    return true;
  }

  // Blob URLs (generadas localmente)
  if (trimmed.startsWith("blob:")) {
    return true;
  }

  try {
    const parsed = new URL(trimmed);
    const hostname = parsed.hostname.toLowerCase();

    // Permitir localhost (desarrollo), mismo dominio y hostnames de CDN/S3 configurados
    if (
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname.endsWith(".localhost") ||
      hostname === window.location.hostname ||
      _EXTRA_MEDIA_HOSTNAMES.has(hostname)
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
