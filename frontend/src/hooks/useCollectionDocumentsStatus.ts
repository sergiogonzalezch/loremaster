import { useCallback, useEffect, useState } from "react";
import { getDocuments } from "../api";
import { ApiAbortError } from "../api/apiClient";

interface UseCollectionDocumentsStatusResult {
  hasCompletedDocs: boolean | null;
  hasProcessingDocs: boolean;
  refresh: (signal?: AbortSignal) => Promise<boolean>;
}

export function useCollectionDocumentsStatus(
  collectionId: string | undefined,
): UseCollectionDocumentsStatusResult {
  const [hasCompletedDocs, setHasCompletedDocs] = useState<boolean | null>(
    null,
  );
  const [hasProcessingDocs, setHasProcessingDocs] = useState(false);

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      if (!collectionId) return false;
      try {
        const res = await getDocuments(
          collectionId,
          { page: 1, page_size: 100 },
          signal,
        );
        const hasCompleted = res.data.some((d) => d.status === "completed");
        setHasCompletedDocs(hasCompleted);
        setHasProcessingDocs(res.data.some((d) => d.status === "processing"));
        return hasCompleted;
      } catch (e) {
        if (e instanceof ApiAbortError) return false;
        setHasCompletedDocs(false);
        setHasProcessingDocs(false);
        return false;
      }
    },
    [collectionId],
  );

  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  useEffect(() => {
    if (!hasProcessingDocs) return;
    const controller = new AbortController();
    const interval = setInterval(() => refresh(controller.signal), 3000);
    return () => {
      clearInterval(interval);
      controller.abort();
    };
  }, [hasProcessingDocs, refresh]);

  return { hasCompletedDocs, hasProcessingDocs, refresh };
}
