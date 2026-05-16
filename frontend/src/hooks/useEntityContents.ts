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
      silent?: boolean;
      category?: ContentCategory;
      status?: "active" | "pending" | "confirmed" | "discarded" | "all";
      page?: number;
      page_size?: number;
      order?: "asc" | "desc";
    }) => {
      if (!collectionId || !entityId) return;
      if (!options?.silent) setLoading(true);
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
        if (!options?.silent) setLoading(false);
      }
    },
    [collectionId, entityId],
  );

  // Encapsula la lógica de actualización optimista: confirmar descarta los demás
  // pendientes de la misma categoría (duplica la regla del backend para UX inmediata).
  const applyOptimisticUpdate = useCallback(
    (id: string, patch: Partial<EntityContent> | null) => {
      setContents((prev) => {
        if (patch === null) return prev.filter((c) => c.id !== id);
        const target = prev.find((c) => c.id === id);
        if (!target) return prev;
        return prev.map((c) => {
          if (c.id === id) return { ...c, ...patch };
          if (
            patch.status === "confirmed" &&
            c.category === target.category &&
            c.status === "pending"
          ) {
            return { ...c, status: "discarded" as const };
          }
          return c;
        });
      });
    },
    [],
  );

  // Consulta mínima al servidor para obtener el total real de pendientes en una
  // categoría, sin depender de la página cargada en memoria.
  const fetchPendingCount = useCallback(
    async (category: ContentCategory): Promise<number> => {
      if (!collectionId || !entityId) return 0;
      try {
        const res = await getContents(collectionId, entityId, {
          category,
          status: "pending",
          page: 1,
          page_size: 1,
        });
        return res.meta.total;
      } catch {
        return 0;
      }
    },
    [collectionId, entityId],
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    contents,
    meta,
    loading,
    error,
    refresh,
    applyOptimisticUpdate,
    fetchPendingCount,
    clearError,
  };
}