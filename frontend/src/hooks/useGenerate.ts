import { useCallback, useEffect, useRef, useState } from "react";
import { ApiAbortError } from "../api/apiClient";

type RunFn<TArgs extends unknown[], TResult> = (
  ...args: [...TArgs, AbortSignal]
) => Promise<TResult>;

interface UseGenerateState<T> {
  data: T | null;
  error: unknown | null;
  isLoading: boolean;
  isCancelled: boolean;
}

export interface UseGenerateReturn<TArgs extends unknown[], TResult> {
  data: TResult | null;
  error: unknown | null;
  isLoading: boolean;
  isCancelled: boolean;
  run: (...args: TArgs) => Promise<TResult | null>;
  cancel: () => void;
  reset: () => void;
}

/**
 * Envuelve una función de API que acepta AbortSignal como último argumento.
 * Permite cancelar la petición en curso (útil para generaciones LLM largas).
 */
export function useGenerate<TArgs extends unknown[], TResult>(
  fn: RunFn<TArgs, TResult>
): UseGenerateReturn<TArgs, TResult> {
  const [state, setState] = useState<UseGenerateState<TResult>>({
    data: null,
    error: null,
    isLoading: false,
    isCancelled: false,
  });
  const controllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      controllerRef.current?.abort();
    };
  }, []);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    setState({ data: null, error: null, isLoading: false, isCancelled: false });
  }, []);

  const run = useCallback(
    async (...args: TArgs): Promise<TResult | null> => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      setState({ data: null, error: null, isLoading: true, isCancelled: false });
      try {
        const result = await fn(...args, controller.signal);
        if (!isMountedRef.current || controller.signal.aborted) return null;
        setState({ data: result, error: null, isLoading: false, isCancelled: false });
        return result;
      } catch (err) {
        if (!isMountedRef.current) return null;
        if (err instanceof ApiAbortError) {
          setState({ data: null, error: null, isLoading: false, isCancelled: true });
          return null;
        }
        setState({ data: null, error: err, isLoading: false, isCancelled: false });
        return null;
      }
    },
    [fn]
  );

  return { ...state, run, cancel, reset };
}
