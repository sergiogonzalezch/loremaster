/**
 * Hook para debounce de un valor (útil para inputs de búsqueda).
 *
 * Retorna el valor solo después de que deje de cambiar durante `delay` ms.
 *
 * @param value - Valor a debouncear
 * @param delay - Tiempo de espera en milisegundos (default 350ms)
 * @returns Valor debounceado
 */

import { useEffect, useState } from "react";

export function useDebouncedValue<T>(value: T, delay = 350) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timeout);
  }, [value, delay]);

  return debounced;
}
