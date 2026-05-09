/**
 * Hooks para envío de formularios y ejecución de acciones con estado de carga.
 *
 * `useFormSubmit` ejecuta una llamada API con manejo de éxito/error genérico.
 * `useAction` es similar pero sin manejo de data de respuesta en onSuccess.
 */

import { useState, useCallback } from "react";
import { parseApiError } from "../utils/errors";

interface FormSubmitOptions {
  onSuccess?: () => void;
  onError?: (message: string) => void;
}

/**
 * Hook para enviar formularios con estado de guardado.
 *
 * @param options - Callbacks opcionales onSuccess y onError
 * @returns Estado saving y función submit para ejecutar la llamada
 */
export function useFormSubmit({ onSuccess, onError }: FormSubmitOptions = {}) {
  const [saving, setSaving] = useState(false);

  const submit = useCallback(
    async <T>(
      apiCall: () => Promise<T>,
      options?: FormSubmitOptions & { onSuccess?: (data: T) => void },
    ): Promise<T | null> => {
      setSaving(true);
      try {
        const result = await apiCall();
        options?.onSuccess?.(result);
        onSuccess?.();
        return result;
      } catch (e) {
        const { text } = parseApiError(e, "Error inesperado");
        options?.onError?.(text);
        onError?.(text);
        return null;
      } finally {
        setSaving(false);
      }
    },
    [onSuccess, onError],
  );

  return { saving, submit };
}

/**
 * Hook para ejecutar acciones con estado de carga.
 *
 * Similar a useFormSubmit pero orientado a acciones sin data de retorno.
 *
 * @param options - Callback opcional onError
 * @returns Estado busy y función run para ejecutar la acción
 */
export function useAction({
  onError,
}: { onError?: (message: string) => void } = {}) {
  const [busy, setBusy] = useState(false);

  const run = useCallback(
    async <T>(
      apiCall: () => Promise<T>,
      options?: { onSuccess?: () => void; onError?: (message: string) => void },
    ): Promise<T | null> => {
      setBusy(true);
      try {
        const result = await apiCall();
        options?.onSuccess?.();
        return result;
      } catch (e) {
        const { text } = parseApiError(e, "Error inesperado");
        options?.onError?.(text);
        onError?.(text);
        return null;
      } finally {
        setBusy(false);
      }
    },
    [onError],
  );

  return { busy, run };
}
