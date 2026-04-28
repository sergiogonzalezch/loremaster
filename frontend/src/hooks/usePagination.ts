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
