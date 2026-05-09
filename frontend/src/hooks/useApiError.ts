import { useState, useCallback } from "react";
import { parseApiError } from "../utils/errors";

type Variant = "warning" | "danger";

export interface ApiErrorState {
  variant: Variant;
  text: string;
}

export function useApiError(initial?: ApiErrorState) {
  const [error, setError] = useState<ApiErrorState | null>(initial ?? null);

  const handleError = useCallback(
    (e: unknown, fallback = "Error inesperado") => {
      setError(parseApiError(e, fallback));
    },
    [],
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return { error, setError, handleError, clearError };
}
