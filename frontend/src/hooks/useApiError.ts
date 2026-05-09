/**
 * Hook para manejo centralizado de errores de API.
 *
 * Mantiene el estado del último error y proporciona helpers
 * para establecerlo (con parseo automático) y limpiarlo.
 */

import { useState, useCallback } from "react";
import { parseApiError } from "../utils/errors";

type Variant = "warning" | "danger";

/** Estado de error tipado para mostrar alertas Bootstrap. */
export interface ApiErrorState {
  variant: Variant;
  text: string;
}

/**
 * @param initial - Estado inicial opcional del error
 * @returns Estado del error, setter y helpers handleError/clearError
 */
export function useApiError(initial?: ApiErrorState) {
  const [error, setError] = useState<ApiErrorState | null>(initial ?? null);

  /** Parsea un error desconocido y lo guarda en el estado. */
  const handleError = useCallback(
    (e: unknown, fallback = "Error inesperado") => {
      setError(parseApiError(e, fallback));
    },
    [],
  );

  /** Limpia el estado de error. */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return { error, setError, handleError, clearError };
}
