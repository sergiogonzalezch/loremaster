/**
 * Formateadores de datos para mostrar al usuario.
 */

/**
 * Formatea una fecha ISO a formato legible en español.
 *
 * @param dateStr - Fecha en formato ISO
 * @param includeTime - Si es true, incluye hora y minutos
 * @returns Cadena formateada (ej: "9 may 2026" o "9 may 2026, 14:30")
 */
export function formatDate(dateStr: string, includeTime = false): string {
  return new Date(dateStr).toLocaleDateString("es-ES", {
    year: "numeric",
    month: "short",
    day: "numeric",
    ...(includeTime && { hour: "2-digit", minute: "2-digit" }),
  });
}
