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