/**
 * Hook para ejecutar funciones de API con soporte de cancelación vía AbortSignal.
 *
 * Útil para operaciones largas como generación de contenido con LLM,
 * donde el usuario puede querer cancelar la petición en curso.
 *
 * La función envuelta debe aceptar AbortSignal como último argumento.
 */

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
 * @param fn - Función de API que acepta AbortSignal como último argumento
 * @returns Estado de la ejecución y controles run/cancel/reset
 */
export function useGenerate<TArgs extends unknown[], TResult>(
  fn: RunFn<TArgs, TResult>,
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

  /** Cancela la petición en curso. */
  const cancel = useCallback(() => {
    controllerRef.current?.abort();
  }, []);

  /** Resetea el estado a valores iniciales. */
  const reset = useCallback(() => {
    setState({ data: null, error: null, isLoading: false, isCancelled: false });
  }, []);

  /** Ejecuta la función con un nuevo AbortController. */
  const run = useCallback(
    async (...args: TArgs): Promise<TResult | null> => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      setState({
        data: null,
        error: null,
        isLoading: true,
        isCancelled: false,
      });
      try {
        const result = await fn(...args, controller.signal);
        if (!isMountedRef.current || controller.signal.aborted) return null;
        setState({
          data: result,
          error: null,
          isLoading: false,
          isCancelled: false,
        });
        return result;
      } catch (err) {
        if (!isMountedRef.current) return null;
        if (err instanceof ApiAbortError) {
          setState({
            data: null,
            error: null,
            isLoading: false,
            isCancelled: true,
          });
          return null;
        }
        setState({
          data: null,
          error: err,
          isLoading: false,
          isCancelled: false,
        });
        return null;
      }
    },
    [fn],
  );

  return { ...state, run, cancel, reset };
}
