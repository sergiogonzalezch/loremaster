/**
 * Construye una query string a partir de un objeto de parámetros.
 *
 * Omite valores undefined, null o string vacío.
 * Soporta arrays como múltiples valores del mismo parámetro.
 *
 * @param params - Objeto con los parámetros de query
 * @returns Query string con prefijo `?` o cadena vacía si no hay parámetros
 */
export function buildQuery(params: object): string {
  const search = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }

    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== undefined && item !== null && item !== "") {
          search.append(key, String(item));
        }
      });
      return;
    }

    search.set(key, String(value));
  });

  const query = search.toString();
  return query ? `?${query}` : "";
}
