/**
 * Hook para generar el array de items de paginación (números + elipsis).
 *
 * Produce una lista compacta: siempre muestra primera y última página,
 * con elipsis cuando hay muchas páginas.
 *
 * @param page - Página actual
 * @param totalPages - Total de páginas
 * @returns Array con números de página o strings "ellipsis-left"/"ellipsis-right"
 */

import { useMemo } from "react";

export type PaginationItem = number | "ellipsis-left" | "ellipsis-right";

export function usePagination(
  page: number,
  totalPages: number,
): PaginationItem[] {
  return useMemo(() => {
    const items: PaginationItem[] = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i += 1) items.push(i);
      return items;
    }
    items.push(1);
    if (page > 3) items.push("ellipsis-left");
    for (
      let i = Math.max(2, page - 1);
      i <= Math.min(totalPages - 1, page + 1);
      i += 1
    ) {
      items.push(i);
    }
    if (page < totalPages - 2) items.push("ellipsis-right");
    items.push(totalPages);
    return items;
  }, [page, totalPages]);
}
