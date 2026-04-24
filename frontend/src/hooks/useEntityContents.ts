import { useState, useCallback } from "react";
import { getContents } from "../api/contents";
import { ApiAbortError } from "../api/apiClient";
import type { EntityContent, PaginatedMeta } from "../types";
import { getErrorMessage } from "../utils/errors";
import type { ContentCategory } from "../utils/enums";

export function useEntityContents(
  collectionId: string | undefined,
  entityId: string | undefined,
) {
  const [contents, setContents] = useState<EntityContent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<PaginatedMeta>({
    total: 0,
    page: 1,
    page_size: 10,
    total_pages: 0,
  });

  const refresh = useCallback(
    async (options?: {
      signal?: AbortSignal;
      category?: ContentCategory;
      status?: "active" | "pending" | "confirmed" | "discarded" | "all";
      page?: number;
      page_size?: number;
      order?: "asc" | "desc";
    }) => {
      if (!collectionId || !entityId) return;
      setLoading(true);
      setError(null);
      try {
        const res = await getContents(
          collectionId,
          entityId,
          {
            page: options?.page ?? 1,
            page_size: options?.page_size ?? 10,
            category: options?.category,
            status: options?.status,
            order: options?.order,
          },
          options?.signal,
        );
        setContents(res.data);
        setMeta(res.meta);
      } catch (e) {
        if (e instanceof ApiAbortError) return;
        setError(getErrorMessage(e, "Error al cargar contenidos"));
      } finally {
        setLoading(false);
      }
    },
    [collectionId, entityId],
  );

  return { contents, meta, loading, error, refresh, setError };
}
