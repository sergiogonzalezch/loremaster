import { useState, useCallback } from "react";
import { parseApiError } from "../utils/errors";

interface FormSubmitOptions {
  onSuccess?: () => void;
  onError?: (message: string) => void;
}

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
