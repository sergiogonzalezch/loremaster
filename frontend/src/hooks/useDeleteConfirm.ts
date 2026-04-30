import { useState } from "react";

interface Options<T> {
  onDelete: (target: T) => Promise<void>;
  onError?: (e: unknown) => void;
}

export function useDeleteConfirm<T>({ onDelete, onError }: Options<T>) {
  const [target, setTarget] = useState<T | null>(null);
  const [deleting, setDeleting] = useState(false);

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
