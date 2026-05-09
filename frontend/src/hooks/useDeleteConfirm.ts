/**
 * Hook para gestionar un flujo de confirmación antes de eliminar un elemento.
 *
 * Mantiene el elemento target seleccionado y ejecuta onDelete solo tras
 * la confirmación del usuario (vía modal).
 */

import { useState } from "react";

interface Options<T> {
  onDelete: (target: T) => Promise<void>;
  onError?: (e: unknown) => void;
}

export function useDeleteConfirm<T>({ onDelete, onError }: Options<T>) {
  const [target, setTarget] = useState<T | null>(null);
  const [deleting, setDeleting] = useState(false);

  /** Ejecuta la eliminación del elemento seleccionado. */
  async function handleConfirm() {
    if (target === null) return;
    setDeleting(true);
    try {
      await onDelete(target);
      setTarget(null);
    } catch (e) {
      onError?.(e);
      setTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  return {
    target,
    deleting,
    open: (item: T) => setTarget(item),
    cancel: () => setTarget(null),
    handleConfirm,
  };
}
