import { useState, useCallback, useEffect } from "react";
import { getContents } from "../api/contents";
import { ApiAbortError } from "../api/apiClient";
import type { EntityContent } from "../types";
import { getErrorMessage } from "../utils/errors";

export function useEntityContents(
  collectionId: string | undefined,
  entityId: string | undefined,
) {
  const [contents, setContents] = useState<EntityContent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      if (!collectionId || !entityId) return;
      setLoading(true);
      setError(null);
      try {
        const res = await getContents(collectionId, entityId, signal);
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

  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  return { contents, loading, error, refresh, setError };
}
