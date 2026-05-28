/**
 * Utilidades para resolución de URLs de medios (imágenes generadas, avatares).
 *
 * MEDIA_BASE apunta al servidor de medios del backend:
 * - Dev con proxy Vite (VITE_API_BASE_URL="/api/v1") → MEDIA_BASE = ""
 *   Las rutas relativas /media/... las sirve el backend a través del proxy de Vite.
 * - Demo/prod (VITE_API_BASE_URL="http://host:8000/api/v1") → MEDIA_BASE = "http://host:8000"
 *   Fallback para acceder al volumen local si el backend no devuelve image_url completa.
 *
 * En modo S3/Floci el backend siempre devuelve image_url con la URL absoluta del bucket,
 * por lo que el fallback MEDIA_BASE + /media/ solo aplica en desarrollo local.
 */
export const MEDIA_BASE = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"
).replace("/api/v1", "");

/**
 * Resuelve la URL de visualización de una imagen de storage.
 *
 * Prioridad:
 * 1. imageUrl — URL completa devuelta por el backend (S3/Floci en demo/prod).
 * 2. storagePath — construye ruta relativa al servidor de medios (fallback dev local).
 *
 * @param imageUrl   Valor de `image_url` del registro de imagen (puede ser null).
 * @param storagePath Valor de `storage_path` del registro de imagen (puede ser null).
 */
export function resolveImageUrl(
  imageUrl: string | null | undefined,
  storagePath: string | null | undefined,
): string {
  return imageUrl || (storagePath ? `${MEDIA_BASE}/media/${storagePath}` : "");
}

/**
 * Descarga una imagen a disco.
 *
 * Estrategia:
 * 1. `fetch(..., { cache: 'reload' })` — evita usar respuestas cacheadas sin
 *    cabecera CORS (problema común cuando <img> y fetch() comparten caché).
 *    Funciona cuando el servidor devuelve Access-Control-Allow-Origin.
 * 2. Fallback `window.open()` — si fetch() sigue bloqueado por CORS (e.g.,
 *    CORS no configurado en el servidor), abre la imagen en nueva pestaña y el
 *    usuario puede guardarla. Mantiene la demo funcional sin cambios de backend.
 *
 * @param url      URL resuelta de la imagen (resultado de resolveImageUrl).
 * @param filename Nombre sugerido del archivo descargado (con extensión).
 */
export async function downloadImage(
  url: string,
  filename: string,
): Promise<void> {
  if (!url) return;
  try {
    // cache: 'reload' fuerza petición fresca, bypassa respuestas cacheadas sin ACAO.
    const response = await fetch(url, { cache: "reload" });
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(blobUrl);
  } catch {
    // fetch() bloqueado (CORS no activo, red, etc.) → abrir en nueva pestaña.
    // Content-Type: application/octet-stream de S3/Floci hace que el navegador
    // descargue el archivo en lugar de mostrarlo.
    window.open(url, "_blank", "noopener,noreferrer");
  }
}
