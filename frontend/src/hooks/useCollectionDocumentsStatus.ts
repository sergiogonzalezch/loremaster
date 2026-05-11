/**
 * Hook para monitorear el estado de los documentos de una colección.
 *
 * Detecta si hay documentos completados y si hay documentos en procesamiento.
 * Usa SSE (Server-Sent Events) para notificaciones en tiempo real en lugar de polling.
 *
 * @param collectionId - ID de la colección a monitorear
 * @returns Estado de documentos y función refresh para forzar recarga
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { getDocuments } from "../api";
import { ApiAbortError } from "../api/apiClient";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
  const eventSourceRef = useRef<EventSource | null>(null);

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
    if (!hasProcessingDocs) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      return;
    }

    const baseUrl = API_BASE_URL.replace("/api/v1", "");
    const eventUrl = `${baseUrl}/collections/${collectionId}/documents/events`;
    const token = localStorage.getItem("token");

    const eventSource = new EventSource(
      token ? `${eventUrl}?auth=${encodeURIComponent(token)}` : eventUrl,
    );
    eventSourceRef.current = eventSource;

    eventSource.onmessage = async (event) => {
      const data = event.data;

      if (data === "processing" || data === "completed") {
        await refresh();

        if (data === "completed") {
          eventSource.close();
          eventSourceRef.current = null;
        }
      } else if (data === "done") {
        eventSource.close();
        eventSourceRef.current = null;
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      eventSourceRef.current = null;
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [hasProcessingDocs, collectionId, refresh]);

  return { hasCompletedDocs, hasProcessingDocs, refresh };
}
