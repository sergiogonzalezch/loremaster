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
