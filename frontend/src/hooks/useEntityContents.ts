import { useState, useCallback } from "react";
import { getContents } from "../api/contents";
import { ApiAbortError } from "../api/apiClient";
import type { EntityContent } from "../types";
import { getErrorMessage } from "../utils/errors";
import type { ContentCategory } from "../utils/enums";

export function useEntityContents(
  collectionId: string | undefined,
  entityId: string | undefined,
) {
  const [contents, setContents] = useState<EntityContent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(
    async (options?: { signal?: AbortSignal; category?: ContentCategory }) => {
      if (!collectionId || !entityId) return;
      setLoading(true);
      setError(null);
      try {
        const res = await getContents(
          collectionId,
          entityId,
          {
            page: 1,
            page_size: 100,
            category: options?.category,
          },
          options?.signal,
        );
        setContents(res.data);
      } catch (e) {
        if (e instanceof ApiAbortError) return;
        setError(getErrorMessage(e, "Error al cargar contenidos"));
      } finally {
        setLoading(false);
      }
    },
    [collectionId, entityId],
  );

  return { contents, loading, error, refresh, setError };
}
